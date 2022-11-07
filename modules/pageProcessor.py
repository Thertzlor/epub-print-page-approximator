import math
import re

from ebooklib import ITEM_DOCUMENT, ITEM_NAVIGATION
from ebooklib.epub import (EpubHtml, EpubItem, EpubNav, Link, etree, read_epub,
                           zipfile)

xns = {'x':'*'}


def pageIdPattern(num:int,prefix = 'pg_break_'):
  return f'{prefix}{num}'

printToc = lambda b : [print(f'{x[0]+1}. {x[1].title}') for x in enumerate(b.toc)]

nodeText = lambda node : ''.join(node.itertext())

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
  

def mapReport(a,b):
  """simple printout function for mapping progress"""
  printProgressBar(a,b,f'Mapping page {a} of {b}','Done',2)
  pass


def approximatePageLocations(stripped:str, pages = 5, mode='split') -> list[int]:
  pgSize = math.ceil(len(stripped)/pages)
  print(f'Calculated approximate page size of {pgSize} characters')
  pgList = [i*pgSize for i in range(pages)]
  if mode == 'split': return pgList
  for [i,p] in enumerate(pgList):
    page = stripped[p:p+pgSize]
    if mode == 'prev': page = page[::-1]
    nextSpace = re.search(r'\s',page)
    if nextSpace is not None: 
      pgList[i] = (p + nextSpace.start() * (1 if mode == 'next' else -1)) 
  return pgList


def nodeRanges(node:etree.ElementBase,strippedText:str = None):
  """Receives a node and optionally the stripped text of that node.\n
  Returns a List of tuples, each consisting of a child element, offsets for where its text content starts and ends as well as the text itself
  """
  if strippedText is None: strippedText= nodeText(node)
  baseIndex = 0
  withText:list[tuple[etree.ElementBase,str]] = [[x,nodeText(x)] for x in node.iter() if nodeText(x) != '']
  rangeList:list[tuple[etree.ElementBase,int,int,str]] = []
  for [e,t] in withText:
    myIndex = strippedText.find(t,baseIndex)
    childText = next((nodeText(x) for x in iter(e) if nodeText(x) != ''),None)
    if childText == t: continue
    rangeList.append([e,myIndex,myIndex+len(t),t])
    if childText is None: baseIndex = myIndex + len(t)
  return rangeList


def getNodeFromLocation(strippedLoc:int,ranges:list[tuple[etree.ElementBase,int,int,str]])->tuple[etree.ElementBase,int,int,bool,str]:
  """Returns node containing the specified location of strippedtext based on a list of node ranges (output from nodeRanges).\n
  The returned tuple contains:\n
  -the node itself\n
  -the distance of the location from the start of the node text\n
  -the distance of the location from the end of the node text\n
  -a boolean expression indicating whether the location is closer to the start or end\n
  -and finally the text of the node
  """
  matches=[[x[0], strippedLoc-x[1], x[2] - strippedLoc ,abs(x[1]-strippedLoc) > abs(strippedLoc-x[2]),x[3]] for x in ranges if x[1] <= strippedLoc and x[2] > strippedLoc]
  return matches[-1]


def insertIntoText(newNode:etree.ElementBase,parentNode:etree.ElementBase,strippedLoc:int):
  newText = parentNode.text[0:strippedLoc]
  newTail = parentNode.text[strippedLoc:]
  parentNode.text = newText
  newNode.tail = newTail
  parentNode.insert(0,newNode)


def insertIntoTail(newNode:etree.ElementBase,parentNode:etree.ElementBase,strippedLoc:int):
  newParentTail = parentNode.tail[0:strippedLoc]
  newChildTail = parentNode.tail[strippedLoc:]
  #deleting zhe old tail, or else it will be added twice
  parentNode.tail=''
  newNode.tail = newChildTail
  parentNode.addnext(newNode)
  #setting the new tail
  parentNode.tail = newParentTail
  pass


def insertNodeAtTextPos(positionData:tuple[etree.ElementBase,int,int,bool,str],newNode:etree.ElementBase):
  """Takes a node position object (output from getNodeFromLocation)"""
  [el,fromStart,fromEnd,_,t] = positionData
  if el.text is not None and len(el.text) > fromStart: return insertIntoText(newNode,el,fromStart)
  if el.tail is not None and len(el.tail) > fromEnd: return insertIntoTail(newNode,el,len(el.tail)-fromEnd)
  offset = 0 if el.text is None else len(el.text)
  for c in el:
    offset = offset+len(nodeText(c) or '')+len(c.tail or '')
    if fromStart < offset: return insertIntoTail(newNode,c,len(c.tail or '') - (offset-fromStart))
  print('could not find insertion spot',fromStart,fromEnd)


def analyzeBook(docs:list[EpubHtml])-> tuple[str,list[int],list[etree.ElementBase]]:
  """Extract the full text content of an ebook, one string containing the full HTML, one containing only the text
  and one list of locations mapping each document to a location within the main string"""
  htmStrings:list[str] = [x.content for x in docs]
  htmDocs: list[etree.ElementBase] = [etree.fromstring(x,etree.HTMLParser()) for x in htmStrings]
  stripStrings:list[str] = [''.join(x.itertext()) for x in htmDocs]
  stripSplits:list[int]=[0]
  currentStripSplit = 0
  docStats:list[etree.ElementBase] = []
  for [i,t] in enumerate(stripStrings):
    doc = htmDocs[i]
    docStats.append(doc)
    currentStripSplit = currentStripSplit + len(t)
    stripSplits.append(currentStripSplit)
  return [''.join(stripStrings),stripSplits,docStats]


def getTocLocations(toc:list[Link],docs:list[EpubHtml],rawText:str,htmSplits:list[int],strippedSplits:list[int]):
  links:list[str] = [x.href for x in toc]
  locations:list[int] = []
  for [i,l] in enumerate(links):
    anchored = '#' in l
    [doc,id] = (l.split('#') if anchored else [l,None])
    [target,index] = next((x for x in enumerate(docs) if x[1].file_name == doc),[None,None])
    if target is None: raise LookupError('Table of Contents contains link to nonexistent documents.')
    if id is None: locations.append(strippedSplits[index])
    else:
      splitEnd = len(rawText) if i == len(htmSplits) else htmSplits[i+1]
      docText = rawText[htmSplits[i]:splitEnd]
  return locations


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


def processEPUB(path:str,pages:int,suffix=None,newPath=None,newName=None,noNav=False, noNcX = False):
  pub = read_epub(path)
  # getting all documents that are not the internal EPUB3 navigation
  docs:list[EpubHtml] = [x for x in pub.get_items_of_type(ITEM_DOCUMENT) if isinstance(x,EpubHtml)]
  [stripText,stripSplits,docStats] = analyzeBook(docs)
  stripPageIndex = approximatePageLocations(stripText,pages)
  pagesMapped:list[tuple[int,int]] = [[x,next(y[0]-1 for y in enumerate(stripSplits) if y[1] > x)] for x in stripPageIndex]
  changedDocs = []

  for [i,[pg,docIndex]] in reversed(list(enumerate(pagesMapped))):
    mapReport(pages-i,pages)
    docLocation = pg - stripSplits[docIndex]

    doc = docStats[docIndex]
    breakSpan:etree.ElementBase =  doc.makeelement('span')
    breakSpan.set('id',f'pg_break_{i}')
    breakSpan.set('epub:type','pagebreak')
    insertNodeAtTextPos(getNodeFromLocation(docLocation,nodeRanges(doc)),breakSpan)
    if docIndex not in changedDocs: changedDocs.append(docIndex)
  ncxNav:EpubItem = next((x for x in pub.get_items_of_type(ITEM_NAVIGATION)),None)
  epub3Nav:EpubHtml =  next((x for x in pub.get_items_of_type(ITEM_DOCUMENT) if isinstance(x,EpubNav)),None)
  if ncxNav is None and epub3Nav is None: raise LookupError('No navigation files found in EPUB, file probably is not valid.')
  repDict = {}
  for x in changedDocs: repDict[docs[x].file_name] = etree.tostring(docStats[x]).decode('utf-8')
  # print(repDict['bano_9781411433458_oeb_c14_r1.html'])
  # if epub3Nav and not noNav: 
  #   if addListToNav(epub3Nav,pagesMapped,docs,repDict) == False: return print('Pagination Cancelled')
  # if ncxNav and not noNcX: 
  #  if addListToNcx(ncxNav,pagesMapped,docs,repDict) == False :return print('Pagination Cancelled')
  
  # overrideZip(path,pathProcessor(path,newPath,newName,suffix),repDict)