import math
import re

from ebooklib import ITEM_DOCUMENT, ITEM_NAVIGATION
from ebooklib.epub import EpubHtml, EpubItem, etree, read_epub, zipfile

xns = {'x':'*'}

matcher = lambda word : r' ('+re.escape(word)+r')[.,! ?&*\n]'
"""match a word in a way that is  very unlikely to occur within a html tag"""


def spanner (num:str, offset=0,epub3=False) : 
  """generate a span element used to designate a page break"""
  typeString = epub3 and ' epub:type="pagebreak" ' or " "
  return f'<span{typeString}title="{num+offset}" id="{pageIdPattern(num)}"/>'


def pageIdPattern(num:int,prefix = 'pgBreak'):
  return f'{prefix}{num}'


def overzip(src:str,dest:str,repDict:dict={}):
  """Zip replacer from StackOverflow because for some reason the write method breaks XML"""
  with zipfile.ZipFile(src) as inZip, zipfile.ZipFile(dest, "w",compression=inZip.compression,compresslevel=inZip.compresslevel) as outZip:
    # Iterate the input files
    for inzipinfo in inZip.infolist():
      # Read input file
      with inZip.open(inzipinfo) as infile:
        inDict = next((x for x in repDict.keys() if inzipinfo.filename.endswith(x)),None)
        if inDict is not None:
          outZip.writestr(inzipinfo.filename, repDict[inDict].encode('utf-8'))
        else: outZip.writestr(inzipinfo.filename, infile.read()) # Other file, dont want to modify => just copy it
  

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
    ex=r' (\w{'+re.escape(str(preferredSize))+r',})[.,! ?&*\n]'
    res = re.search(ex,string[lastDex:])
    if res is not None and not safeWord(res[1],stripStr,fullStr):
      lastDex = lastDex + res.end()
      res = None
    else: preferredSize = preferredSize -1 
  return [res[1],lastDex+res.end()]


def mapReport(a,b):
  """simple printout function for mapping progress"""
  # print(f'mapping page {a} of {b}')
  pass


def mainPaginate(content:str, stripped:str, pages = 5) -> tuple[list[int],list[int],int,int]:
  pgSize = math.ceil(len(stripped)/pages)
  print(f'calculated page size of {pgSize} characters')
  realPageIndex = [0]
  rawPageIndex = [0]
  rawPageOffset = [0]
  mapReport(1,pages)
  for i in range(pages-1):
    mapReport(i+2,pages)
    pageEnd = (rawPageIndex[-1]+pgSize) - rawPageOffset[-1]
    htPart = content[realPageIndex[-1]:]
    rawPart = stripped[rawPageIndex[-1]:]
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
  return [
    realPageIndex,
    rawPageIndex,
    len(realPageIndex),
    len(rawPageIndex)
  ]


def unifyDoc(docs:list[EpubHtml])-> tuple[str,str,list[int]]:
  """Extract the full text content of an ebook, one string containing the full html, one containing only the text
  and one list of locations mapping each document to a location within the main string"""
  xmlStrings:list[str] = [x.content.decode('utf-8') for x in docs]
  innerStrings:list[str] = [''.join(etree.fromstring(x.content,etree.HTMLParser()).itertext()) for x in docs]
  splits:list[int]=[0]
  currentSplit = 0
  for x in xmlStrings:
    currentSplit = currentSplit + len(x)
    splits.append(currentSplit)
  return [''.join(xmlStrings),''.join(innerStrings),splits]

def isNav(html:EpubHtml):
  """detect the EPUB3 navigation html"""
  bod = etree.fromstring(html.content,etree.HTMLParser())
  return bod.find('x:body',xns).find('x:nav',xns) is not None


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


def reintegrate(pageLocations:list[int],pageMap:list[int],docOffsets:list[int],documents:list[EpubHtml],startNo = 0,repDict:dict={},epub3=False):
  perDoc = [[y[1] - docOffsets[x[0]] for y in enumerate(pageLocations) if x[0] == pageMap[y[0]]] for x in enumerate(documents)]
  for [i,locList] in enumerate(perDoc):
    if len(locList) == 0: continue
    doc = documents[i]
    docText:str = doc.content.decode('utf-8')
    offset = 0
    for loc in locList:
      if loc == 0: continue
      newSpan = spanner(startNo,2,epub3)
      docText = insertAt(newSpan,docText,loc+offset)
      startNo = startNo + 1
      offset = offset + len(newSpan)
    repDict[doc.file_name] = docText


def addToNcx(ncx:EpubItem,docMap:list[int],documents:list[EpubHtml],startNo=0,repDict:dict={}):
  doc:etree.ElementBase = etree.fromstring(ncx.content)
  def tag(name:str,attributes:dict=None)->etree.ElementBase: return doc.makeelement(name,attributes)
  def makeLabel(text:str|int):
    label = tag('navLabel')
    txt = tag('text')
    txt.text = str(text);
    label.append(txt)
    return label
  getLink = lambda pageNo : f'{relPath(ncx.file_name,documents[docMap[pageNo]].file_name)}#{pageIdPattern(startNo+pageNo-1)}'
  def makeTarget(number:int,customLink:str=None):
    target = tag('pageTarget',{'id':f'pageNav_{startNo+number}', 'type':'normal', 'value':str(number)})
    target.append(makeLabel(number))
    target.append(tag('content',{'src':customLink or getLink(number-1)}))
    return target
  pList:etree.ElementBase = doc.find('x:pageList',xns)
  if(pList is not None): 
    put = input('epub already has a pageList! Continue and overwrite it? [y/N]')
    if put.lower() != 'y': return False
    doc.remove(pList)
  genList = tag('pageList')
  genList.append(makeLabel('Pages'))
  for i in range(len(docMap)): genList.append(makeTarget(i+1, i==0 and relPath(ncx.file_name,documents[0].file_name) or None))
  doc.append(genList)
  ncxString:str =  etree.tostring(doc)
  repDict[ncx.file_name] = ncxString.decode('utf-8').replace('<pageTarget','\n<pageTarget')
  return True


def addToNav(nav:EpubHtml,docMap:list[int],documents:list[EpubHtml],startNo=0,repDict:dict={}):
  doc:etree.ElementBase = etree.fromstring(nav.content,etree.HTMLParser())
  getLink = lambda pageNo : f'{relPath(nav.file_name,documents[docMap[pageNo]].file_name)}#{pageIdPattern(startNo+pageNo-1)}'
  def tag(name:str,attributes:dict=None)->etree.ElementBase: return doc.makeelement(name,attributes)
  def makeTarget(number:int,customLink:str=None):
    target = tag('li')
    link = tag('a',{'href':customLink or getLink(number-1)})
    link.text=str(number)
    target.append(link)
    return target
  body:etree.ElementBase = doc.find('x:body',xns)
  mainNav  = tag('nav',{'epub:type':'page-list', 'hidden':''})
  header = tag('h1')
  header.text='List of Pages'
  mainNav.append(header)
  lst = tag('ol')
  for i in range(len(docMap)): lst.append(makeTarget(i+1, i==0 and relPath(nav.file_name,documents[0].file_name) or None))
  mainNav.append(lst)
  body.append(mainNav)
  ncxString:str =  etree.tostring(doc)
  repDict[nav.file_name] = ncxString.decode('utf-8').replace('<li','\n<li')
  return True


def numberOfNavPoints(ncx:EpubItem|None=None):
  if ncx is None: return 0
  doc:etree.ElementBase = etree.fromstring(ncx.content,etree.HTMLParser())
  navMap:etree.ElementBase = doc.find('x:navMap',xns)
  if navMap is None: return 0
  return len(navMap.findall('x:navPoint',xns))


def pubMain(path:str,pages:int):
  pub = read_epub(path)
  # getting all documents that are not the internal EPUB3 navigation
  docs:list[EpubHtml] = [x for x in pub.get_items_of_type(ITEM_DOCUMENT) if not isNav(x)]
  [fullText,strippedText,splits] = unifyDoc(docs)
  [realPages,_,realCount,rawCount] = mainPaginate(fullText,strippedText,pages)
  pageMap = [ next(y[0]-1 for y in enumerate(splits) if y[1] > x) for x in realPages]
  if(realCount != rawCount): print("WARNING! Page counts don't make sense")
  ncxNav:EpubItem = next((x for x in pub.get_items_of_type(ITEM_NAVIGATION)),None)
  epub3Nav:EpubHtml =  next((x for x in pub.get_items_of_type(ITEM_DOCUMENT) if isNav(x)),None)
  if ncxNav is None and epub3Nav is None: raise BaseException('No navigation files found in EPUB, file probably is not valid.')
  playOrderStart = numberOfNavPoints(ncxNav)
  repDict = {}
  reintegrate(realPages,pageMap,splits,docs,playOrderStart,repDict,epub3Nav is not None)
  if epub3Nav: addToNav(epub3Nav,pageMap,docs,playOrderStart,repDict)
  if ncxNav: addToNcx(ncxNav,pageMap,docs,playOrderStart,repDict)
  overzip(path,f'{path[:-5]}_paginated.epub',repDict)

pubMain('./The Issue at Hand - James Blish_e3.epub',413)