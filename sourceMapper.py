import math
import re
import zipfile

from ebooklib import epub

xns = {'x':'*'}

matcher = lambda word : r' ('+re.escape(word)+r')[.,! ?&*\n]'
"""match a word in a way that is  very unlikely to occur within a html tag"""

spanner = lambda num : f'<span class="pg_break" id="{pageIdPattern(num)}"/>'
"""generate a span element used to designate a page break"""

def pageIdPattern(num:int,prefix = 'pg_break_'):
  return f'{prefix}{num}'


def overzip(src:str,dest:str,repDict:dict={}):
  with zipfile.ZipFile(src) as inZip, zipfile.ZipFile(dest, "w",compression=inZip.compression,compresslevel=inZip.compresslevel) as outZip:
      # Iterate the input files
      for inzipinfo in inZip.infolist():
          # Read input file
          with inZip.open(inzipinfo) as infile:
              if inzipinfo.filename in repDict:
                  outZip.writestr(inzipinfo.filename, repDict[inzipinfo.filename].encode('utf-8'))
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
    if preferredSize == 0:
      raise LookupError("can't find any safe words for current page")
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

def unifyDoc(docs:list[epub.EpubHtml])-> tuple[str,str,list[int]]:
  """Extract the full text content of an ebook, one string containing the full html, one containing only the text
  and one list of locations mapping each document to a location within the main string"""
  xmlStrings:list[str] = [x.get_content().decode('utf-8') for x in docs]
  innerStrings:list[str] = [''.join(epub.etree.fromstring(x.get_content(),epub.etree.HTMLParser()).itertext()) for x in docs]
  splits:list[int]=[0]
  currentSplit = 0
  for x in xmlStrings:
    currentSplit = currentSplit + len(x)
    splits.append(currentSplit)
  return [''.join(xmlStrings),''.join(innerStrings),splits]

def isNav(html:epub.EpubHtml):
  """detect the EPUB3 navigation html"""
  bod = epub.etree.fromstring(html.get_content(),epub.etree.HTMLParser())
  return bod.find('x:body',xns).find('x:nav',xns) is not None


def between (str,pos,around,sep='|'): 
  """split a string at a certain position, highlight the split with a separator and output a range of characters to either side.

  Used for debugging purposes"""
  return f'{str[pos-around:pos]}{sep}{str[pos:pos+around]}'

def insertAt(value,targetString,index): return targetString[:index] + value + targetString[index:]

def reintegrate(pageLocations:list[int],pageMap:list[int],docOffsets:list[int],documents:list[epub.EpubHtml],startNo = 0,repDict:dict={}):
  perDoc = [[y[1] - docOffsets[x[0]] for y in enumerate(pageLocations) if x[0] == pageMap[y[0]]] for x in enumerate(documents)]
  for [i,locList] in enumerate(perDoc):
    if len(locList) == 0: continue
    doc = documents[i]
    docText:str = doc.get_content().decode('utf-8')
    for loc in reversed(locList):
      if loc == 0: continue
      docText = insertAt(spanner(startNo),docText,loc)
      startNo = startNo + 1
    doc.set_content(docText.encode('utf-8'))
    repDict[doc.file_name] = docText

def addToNcx(ncx:epub.EpubItem,docMap:list[int],documents:list[epub.EpubHtml],startNo=0,repDict:dict={}):
  doc:epub.etree.ElementBase = epub.etree.fromstring(ncx.get_content())
  def tag(name:str,attributes:dict=None)->epub.etree.ElementBase: return doc.makeelement(name,attributes)
  def makeLabel(text:str|int):
    label = tag('navLabel')
    txt = tag('text')
    txt.text = str(text);
    label.append(txt)
    return label
  getLink = lambda pageNo : f'{documents[docMap[pageNo]].file_name}#{pageIdPattern(startNo+pageNo)}'
  def makeTarget(number:int,customLink:str=None):
    target = tag('pageTarget',{'id':f'pageNav_{startNo+number}', 'type':'normal', 'value':str(number)})
    target.append(makeLabel(number))
    target.append(tag('content',{'src':customLink or getLink(number-1)}))
    return target
  pList:epub.etree.ElementBase = doc.find('x:pageList',xns)
  if(pList is not None): 
    put = input('epub already has a pageList! Continue and overwrite it? [y/N]')
    if put.lower() != 'y': return False
    doc.remove(pList)
  genList = tag('pageList')
  genList.append(makeLabel('Pages'))
  for i in range(len(docMap)): genList.append(makeTarget(i+1, i==0 and documents[0].file_name or None))
  doc.append(genList)
  ncx.set_content(epub.etree.tostring(doc))
  repDict[ncx.file_name] = epub.etree.tostring(doc).decode('utf-8')
  return True

def numberOfNavPoints(ncx:epub.EpubItem|None):
  if ncx is None: return 0
  doc:epub.etree.ElementBase = epub.etree.fromstring(ncx.get_content(),epub.etree.HTMLParser())
  navMap:epub.etree.ElementBase = doc.find('x:navMap',xns)
  if navMap is None: return 0
  return len(navMap.findall('x:navPoint',xns))

def pubMain(path:str):
  pub = epub.read_epub(path)
  # overzip(path,f'{path[:-5]}_oops.epub')
  # getting all documents that are not the internal EPUB3 navigation
  docs:list[epub.EpubHtml] = [x for x in pub.get_items_of_type(epub.ebooklib.ITEM_DOCUMENT) if not isNav(x)]
  [fullText,strippedText,splits] = unifyDoc(docs)
  [realPages,_,realCount,rawCount] = mainPaginate(fullText,strippedText,100)
  pageMap = [ next(y[0]-1 for y in enumerate(splits) if y[1] > x) for x in realPages]
  if(realCount != rawCount): print("WARNING! Page counts don't make sense")
  ncxNav:epub.EpubItem = next(x for x in pub.get_items_of_type(epub.ebooklib.ITEM_NAVIGATION))
  # epub3Nav:epub.EpubHtml =  next(x for x in pub.get_items_of_type(epub.ebooklib.ITEM_DOCUMENT) if isNav(x))
  if ncxNav is None: raise BaseException('No navigation files found in EPUB, file probably is not valid.')
  playOrderStart = numberOfNavPoints(ncxNav)
  repDict = {}
  reintegrate(realPages,pageMap,splits,docs,playOrderStart,repDict)
  addToNcx(ncxNav,pageMap,docs,playOrderStart,repDict)
  overzip(path,f'{path[:-5]}_paginated_zip.epub',repDict)
  caliTags = next(m for m in pub.metadata if 'calibre' in m)
  if caliTags:
    # custom metadata set by calibre causes errors when saving the file, so we simply remove them from the dictionary. 
    userTags = [k for k in pub.metadata[caliTags].keys() if 'user_metadata' in k]
    for u in userTags: del pub.metadata[caliTags][u]
  epub.write_epub(f'{path[:-5]}_paginated_lib.epub',pub)

pubMain('./The Issue at Hand - James Blish.epub')