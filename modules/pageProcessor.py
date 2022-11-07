import math
import re

from ebooklib import ITEM_DOCUMENT, ITEM_NAVIGATION
from ebooklib.epub import (EpubHtml, EpubItem, EpubNav, Link, etree, read_epub,
                           zipfile)

xns = {'x':'*'}

wordTerminators = '.,! ?&*\n'
nonWordChars = '\s><="'

matcher = lambda word : f' ({re.escape(word)})[{wordTerminators}]'
"""match a word in a way that is  very unlikely to occur within a html tag"""


def spanner (num:str, offset=0,epub3=False) : 
  """generate a span element used to designate a page break"""
  typeString = epub3 and ' epub:type="pagebreak" ' or " "
  return f'<span{typeString}title="{num+offset}" id="{pageIdPattern(num)}"/>'


def pageIdPattern(num:int,prefix = 'pg_break_'):
  return f'{prefix}{num}'

printToc = lambda b : [print(f'{x[0]+1}. {x[1].title}') for x in enumerate(b.toc)]

def printProgressBar (iteration:int, total:int, prefix = '', suffix = '', decimals = 1, length = 100, fill = '█', printEnd = "\r"):
    """https://stackoverflow.com/questions/3173320/"""
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end = printEnd)
    # Print New Line on Complete
    if iteration == total: 
        print()

def overrideZip(src:str,dest:str,repDict:dict={}):
  """Zip replacer from the internet because for some reason the write method of the ebook libraray breaks HTML"""
  with zipfile.ZipFile(src) as inZip, zipfile.ZipFile(dest, "w",compression=zipfile.ZIP_DEFLATED) as outZip:
    # Iterate the input files
    for inZipInfo in inZip.infolist():
      # Read input file
      with inZip.open(inZipInfo) as inFile:
        # Sometimes EbookLib does not include the root epub path in its filenames, so we're using endswith.
        inDict = next((x for x in repDict.keys() if inZipInfo.filename.endswith(x)),None)
        if inDict is not None:
          outZip.writestr(inZipInfo.filename, repDict[inDict].encode('utf-8'))
        else: outZip.writestr(inZipInfo.filename, inFile.read(),compress_type=zipfile.ZIP_STORED if inZipInfo.filename.lower() == 'mimetype' else zipfile.ZIP_DEFLATED) # Other file, dont want to modify => just copy it
  print(f'succesfully saved {dest}')
  

def safeWord(match:str,stripStr:str,fullStr:str):
  """function for finding 'safe' word matches for inserting page breaks"""
  ex = matcher(match)
  [l1,l2] = [ len(re.findall(ex,x)) for x in [stripStr,fullStr]]
  # a word is 'safe' if we can match it in the stripped and unstripped text the same number of times. 
  return l1 == l2


def findWord(string:str,preferredSize:int,stripStr:str,fullStr:str):
  """function for finding the first 'safe' word match on a page, returns the word and its resulting offset"""
  res = None
  lastDex = 0
  while res is None:
    if preferredSize == 0: raise LookupError(f"can't find any safe words for current page: {fullStr}")
    ex=f' ([^{nonWordChars}{wordTerminators}]{{{re.escape(str(preferredSize))},}})[{wordTerminators}]'
    res = re.search(ex,string[lastDex:])
    if res is not None and not safeWord(res[1],stripStr,fullStr):
      lastDex = lastDex + res.end()
      res = None
    else: preferredSize = preferredSize -1 
  return [res[1],lastDex+res.end()]


def mapReport(a,b):
  """simple printout function for mapping progress"""
  printProgressBar(a,b,f'Mapping page {a} of {b}','Done',2)
  pass


def approximatePageLocations(content:str, stripped:str, pages = 5) -> tuple[list[int],list[int],int,int]:
  pgSize = math.ceil(len(stripped)/pages)
  print(f'Calculated approximate page size of {pgSize} characters')
  # we assume that each HTML page is not 100 times bigger than the "raw" page text page to speed up performance
  pgLookaround = pgSize*100
  realPageIndex = [0]
  rawPageIndex = [0]
  rawPageOffset = [0]
  mapReport(1,pages)
  for i in range(pages-1):
    mapReport(i+2,pages)
    pageEnd = (rawPageIndex[-1]+pgSize) - rawPageOffset[-1]
    htPart = content[realPageIndex[-1]:realPageIndex[-1]+pgLookaround]
    rawPart = stripped[rawPageIndex[-1]:rawPageIndex[-1]+pgLookaround]
    currentPage = stripped[rawPageIndex[-1]:pageEnd]
    nextPage = stripped[pageEnd:pageEnd+pgSize]
    [lastWord,currentOffset] = findWord(nextPage,3,rawPart,htPart)
    rawPageIndex.append(pageEnd+currentOffset)
    rawPageOffset.append(currentOffset)
    wordEx = matcher(lastWord)
    occurrences = len(re.findall(wordEx,currentPage))
    rawMatches = [x for x in enumerate(re.finditer(wordEx,htPart))]
    for [i,match] in rawMatches:
      realOffset = match.end()
      if i == occurrences:
        realPageIndex.append(realOffset+realPageIndex[-1])
        break
  return [realPageIndex,rawPageIndex,len(realPageIndex),len(rawPageIndex)]


def mergeBook(docs:list[EpubHtml])-> tuple[str,str,list[int],list[int]]:
  """Extract the full text content of an ebook, one string containing the full HTML, one containing only the text
  and one list of locations mapping each document to a location within the main string"""
  xmlStrings:list[str] = [x.content.decode('utf-8') for x in docs]
  innerStrings:list[str] = [''.join(etree.fromstring(x.content,etree.HTMLParser()).itertext()) for x in docs]
  splits:list[int]=[0]
  textSplits:list[int]=[0]
  currentSplit = 0
  currentTextSplit = 0
  for [i,x] in enumerate(xmlStrings):
    currentSplit = currentSplit + len(x)
    currentTextSplit = currentTextSplit + len(innerStrings[i])
    splits.append(currentSplit)
    textSplits.append(currentTextSplit)
  return [''.join(xmlStrings),''.join(innerStrings),splits,textSplits]


def getTocLocations(toc:list[Link],docs:list[EpubHtml],rawText:str,splits:list[int]):
  links:list[str] = [x.href for x in toc]
  locations:list[int] = []
  for [i,l] in enumerate(links):
    anchored = '#' in l
    [doc,id] = (l.split('#') if anchored else [l,None])
    [target,index] = next((x for x in enumerate(docs) if x[1].file_name == doc),[None,None])
    if target is None: raise LookupError('Table of Contents contains link to nonexistent documents.')
    if id is None: locations.append(splits[index])
    else:
      splitEnd = len(rawText) if i == len(splits) else splits[i+1]
      docText = rawText[splits[i]:splitEnd]


def between (str,pos,around,sep='|'): 
  """split a string at a certain position, highlight the split with a separator and output a range of characters to either side.

  Used for debugging purposes"""
  return f'{str[pos-around:pos]}{sep}{str[pos:pos+around]}'


def relPath(pathA:str,pathB:str):
  [splitA,splitB] = [x.split('/') for x in[pathA,pathB]]
  pathDiff=0
  for [i,s] in enumerate(splitA):
    if s == splitB[i]: pathDiff = pathDiff+1
    else: break
  return '/'.join(splitB[pathDiff:])


def insertAt(value,targetString,index): return targetString[:index] + value + targetString[index:]

def insertPageBreaks(pageLocations:list[int],pageMap:list[int],docOffsets:list[int],documents:list[EpubHtml],repDict:dict={},epub3=False):
  perDoc = [[y[1] - docOffsets[x[0]] for y in enumerate(pageLocations) if x[0] == pageMap[y[0]]] for x in enumerate(documents)]
  currentNo = 0
  for [i,locList] in enumerate(perDoc):
    if len(locList) == 0: continue
    doc = documents[i]
    docText:str = doc.content.decode('utf-8')
    offset = 0
    for loc in locList:
      if loc == 0: continue
      newSpan = spanner(currentNo,2,epub3)
      docText = insertAt(newSpan,docText,loc+offset)
      currentNo = currentNo + 1
      offset = offset + len(newSpan)
    repDict[doc.file_name] = docText


def addListToNcx(ncx:EpubItem,docMap:list[int],documents:list[EpubHtml],repDict:dict={}):
  doc:etree.ElementBase = etree.fromstring(ncx.content)
  def tag(name:str,attributes:dict=None)->etree.ElementBase: return doc.makeelement(name,attributes)
  def makeLabel(text:str|int):
    label = tag('navLabel')
    txt = tag('text')
    txt.text = str(text);
    label.append(txt)
    return label
  getLink = lambda pageNo : f'{relPath(ncx.file_name,documents[docMap[pageNo]].file_name)}#{pageIdPattern(pageNo-1)}'
  def makeTarget(number:int,customLink:str=None):
    target = tag('pageTarget',{'id':f'pageNav_{number}', 'type':'normal', 'value':str(number)})
    target.append(makeLabel(number))
    target.append(tag('content',{'src':customLink or getLink(number-1)}))
    return target
  pList:etree.ElementBase = doc.find('x:pageList',xns)
  if(pList is not None): 
    put = input('EPUB NCX already has a pageList element.\nContinue and overwrite it? [y/N]')
    if put.lower() != 'y': return False
    doc.remove(pList)
  genList = tag('pageList')
  genList.append(makeLabel('Pages'))
  for i in range(len(docMap)): genList.append(makeTarget(i+1, i==0 and relPath(ncx.file_name,documents[0].file_name) or None))
  doc.append(genList)
  ncxString:str =  etree.tostring(doc)
  repDict[ncx.file_name] = ncxString.decode('utf-8').replace('<pageTarget','\n<pageTarget')
  return True


def addListToNav(nav:EpubHtml,docMap:list[int],documents:list[EpubHtml],repDict:dict={}):
  doc:etree.ElementBase = etree.fromstring(nav.content,etree.HTMLParser())
  getLink = lambda pageNo : f'{relPath(nav.file_name,documents[docMap[pageNo]].file_name)}#{pageIdPattern(pageNo-1)}'
  def tag(name:str,attributes:dict=None)->etree.ElementBase: return doc.makeelement(name,attributes)
  def makeTarget(number:int,customLink:str=None):
    target = tag('li')
    link = tag('a',{'href':customLink or getLink(number-1)})
    link.text=str(number)
    target.append(link)
    return target
  body:etree.ElementBase = doc.find('x:body',xns)
  oldNav = next((x for x in body.findall('x:nav',xns) if x.get('epub:type') == 'page-list'),None)
  if(oldNav is not None): 
    put = input('EPUB3 navigation already has a page-list.\nContinue and overwrite it? [y/N]')
    if put.lower() != 'y': return False
    doc.remove(oldNav)
  mainNav  = tag('nav',{'epub:type':'page-list', 'hidden':''})
  header = tag('h1')
  header.text='List of Pages'
  mainNav.append(header)
  lst = tag('ol')
  for i in range(len(docMap)): lst.append(makeTarget(i+1, i==0 and relPath(nav.file_name,documents[0].file_name) or None))
  mainNav.append(lst)
  body.append(mainNav)
  navString:str =  etree.tostring(doc)
  repDict[nav.file_name] = navString.decode('utf-8').replace('<li','\n<li')
  return True


def pathProcessor(oldPath:str,newPath:str=None,newName:str=None,suffix:str='_paginated'):
  pathSplit = oldPath.split("/")
  oldFileName = pathSplit.pop()
  if newName is not None:suffix = ''
  finalName = newName or oldFileName
  if finalName.lower().endswith('.epub'):
    finalName = finalName[:-5]
  return f'{newPath or "/".join(pathSplit)}{finalName}{suffix}.epub'

nodeText = lambda node : ''.join(node.itertext())

def nodeRanges(node:etree.ElementBase,baseText:str = None):
  if baseText is None: baseText= nodeText(node)
  baseIndex = 0
  withText:list[tuple[etree.ElementBase,str]] = [[x,nodeText(x)] for x in node.iter() if nodeText(x) != '']
  rangeList:list[tuple[etree.ElementBase,int,int,str]] = []
  for [e,t] in withText:
    myIndex = baseText.find(t,baseIndex)
    childText = next((nodeText(x) for x in iter(e) if nodeText(x) != ''),None)
    if childText == t: continue
    rangeList.append([e,myIndex,myIndex+len(t),t])
    if childText is None: baseIndex = myIndex + len(t)
  return rangeList

def getNodeFromLocation(loc:int,ranges:list[tuple[etree.ElementBase,int,int,str]])->tuple[etree.ElementBase,bool,str]:
  matches=[[x[0], abs(x[1]-loc) > abs(loc-x[2]),x[3]] for x in ranges if x[1] <= loc and x[2] > loc]
  return matches[-1]

def processEPUB(path:str,pages:int,suffix=None,newPath=None,newName=None,noNav=False, noNcX = False):
  pub = read_epub(path)
  # getting all documents that are not the internal EPUB3 navigation
  docs:list[EpubHtml] = [x for x in pub.get_items_of_type(ITEM_DOCUMENT) if isinstance(x,EpubHtml)]
  [fullText,strippedText,splits,rawSplits] = mergeBook(docs)
  [realPages,rawPages,realCount,rawCount] = approximatePageLocations(fullText,strippedText,pages)
  pageMap = [ next(y[0]-1 for y in enumerate(splits) if y[1] > x) for x in realPages]
  if(realCount != rawCount): print("WARNING! Page counts don't make sense")
  ncxNav:EpubItem = next((x for x in pub.get_items_of_type(ITEM_NAVIGATION)),None)
  epub3Nav:EpubHtml =  next((x for x in pub.get_items_of_type(ITEM_DOCUMENT) if isinstance(x,EpubNav)),None)
  if ncxNav is None and epub3Nav is None: raise LookupError('No navigation files found in EPUB, file probably is not valid.')
  repDict = {}
  insertPageBreaks(realPages,pageMap,splits,docs,repDict,epub3Nav is not None)
  if epub3Nav and not noNav: 
    if addListToNav(epub3Nav,pageMap,docs,repDict) == False: return print('Pagination Cancelled')
  if ncxNav and not noNcX: 
   if addListToNcx(ncxNav,pageMap,docs,repDict) == False :return print('Pagination Cancelled')
  
  overrideZip(path,pathProcessor(path,newPath,newName,suffix),repDict)