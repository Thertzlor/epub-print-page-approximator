from math import floor
from re import finditer, search

from ebooklib import ITEM_DOCUMENT
from ebooklib.epub import EpubHtml, etree, read_epub, zipfile

from modules.helperfunctions import romanize, romanToInt
from modules.navutils import makePgMap, prepareNavigations, processNavigations
from modules.nodeutils import addPageMapRefs, getBookContent, insertAtPosition,identifyPageNodes
from modules.pathutils import pageIdPattern, pathProcessor
from modules.progressbar import mapReport
from modules.statisticsutils import lineSplitter, outputStats, pagesFromStats
from modules.tocutils import checkToC, processToC

calculatedSizes:list[int|float]= []

def overrideZip(src:str,dest:str,repDict:dict={},pageMap:str|None=None):
  """Zip replacer from the internet because for some reason the write method of the ebook library breaks HTML"""
  with zipfile.ZipFile(src) as inZip, zipfile.ZipFile(dest, "w",compression=zipfile.ZIP_DEFLATED) as outZip:
    # Iterate the input files
    if pageMap:
      opfFile = next((x for x in inZip.infolist() if x.filename.endswith('.opf')),None)
      if not opfFile: raise LookupError('somehow your epub does not have an opf file.')
      opfContent = inZip.open(opfFile).read()
      mapReferences = addPageMapRefs(opfContent)
      if mapReferences is None: repDict['page-map.xml'] = pageMap
      else:
        repDict[opfFile.filename] = mapReferences.decode('utf-8')
        outZip.writestr('page-map.xml',pageMap)

    for inZipInfo in inZip.infolist():
      # Read input file
      with inZip.open(inZipInfo) as inFile:
        # Sometimes EbookLib does not include the root epub path in its filenames, so we're using endswith.
        inDict = next((x for x in repDict.keys() if inZipInfo.filename == x or ('/'.join(inZipInfo.filename.split('/')[1:]) == x)),None)
        if inDict is not None:
          outZip.writestr(inZipInfo.filename, repDict[inDict].encode('utf-8'))
          repDict.pop(inDict,None)
        # copying non-changed files, saving the mimetype without compression
        else: outZip.writestr(inZipInfo.filename, inFile.read(),compress_type=zipfile.ZIP_STORED if inZipInfo.filename.lower() == 'mimetype' else zipfile.ZIP_DEFLATED)
  print(f'Succesfully saved {dest}')


def approximatePageLocationsByLine(stripped:str, pages:int, pageMode:str|int,offset=0):
  """Splitting up the stripped text of the book by number of lines. Takes 'lines' or a maximum line length as its pageMode parameter. """
  lines = lineSplitter(stripped,pageMode)
  # This should only seldomly happen, but best to be prepared.
  if len(lines) < pages: raise BaseException(f'The number of detected lines in the book ({len(lines)}) is smaller than the number of pages to generate ({pages}). Consider using the "chars" paging mode for this book.')
  lineOffset = 0
  lineLocations:list[int]=[]
  # for most of the splitting we don't care about text content, just locations.
  for line in lines:
    lineLocations.append(lineOffset)
    lineOffset = lineOffset + len(line)
  # calculating the number of lines per page.
  step = len(lines)/pages
  if offset == 0: print(f'Calculated approximate page height of {"{:.2f}".format(step)} lines')
  calculatedSizes.append(step)
  # step is a float, so we round it to get a valid index.
  pgList = [lineLocations[round(step*i)] for i in range(pages)]
  return pgList if offset == 0 else [p+offset for p in pgList]


def getSingleLocation(lastPage:int,ranges:list[tuple[int,int,int]]):
  offset = 0
  lastLocation = 0
  for [_,end,numPages] in ranges:
    offset = offset+ numPages
    if offset >= lastPage:
      lastLocation = end
      break
  return lastLocation


def processRomans(roman:int|None,ranges:list[tuple[int,int,int]],frontRanges:list[tuple[int,int,int]],stripText:str,knownRomans:tuple[str],tocMap:tuple[int|str],pages:int,breakMode:str,pageMode:str|int):
  if roman is None: roman = 0
  pageOne = next((i for [i,x] in enumerate(tocMap) if x == 1),None)
  if pageOne is None: raise LookupError('ToC map needs to define the location of page 1 for compatibility with Roman numerals for front matter')
  frontEnd = ranges[0][0]
  frontText = stripText[0:frontEnd]
  [_,contentMapped] = approximatePageLocationsByRanges(ranges,[],stripText,pages,breakMode,pageMode)
  if roman == 0 or len(knownRomans) != 0:
    lastKnownRoman = romanToInt(knownRomans[-1]) if len(knownRomans) != 0 else 0
    lastRomanLocation = getSingleLocation(lastKnownRoman,frontRanges)
    frontDef = floor(sum(calculatedSizes)/len(calculatedSizes)) if lastRomanLocation == 0 else floor(lastRomanLocation/lastKnownRoman)
    roman = max(pagesFromStats(frontText,pageMode,frontDef) if roman == 0 else roman,lastKnownRoman)
    if len(frontRanges) == 0: frontRanges = [(0,frontEnd,roman)]
    elif frontEnd-frontRanges[-1][1] != 0:
      sectionPages = pagesFromStats(frontText[frontRanges[-1][1]:],pageMode,frontDef)
      roman = roman + sectionPages-1
      frontRanges.append((frontRanges[-1][1],frontEnd,sectionPages))
  [_,frontMapped] = approximatePageLocationsByRanges(frontRanges,[],frontText,roman,breakMode,pageMode)
  return (roman,frontMapped+contentMapped)


def approximatePageLocationsByRanges(ranges:list[tuple[int,int,int]],frontRanges:list[tuple[int,int,int]],stripText:str,pages = 5, breakMode='split', pageMode:str|int='chars',roman:int|None=None,tocMap:tuple[int|str]=tuple()):
  """This is the page location function used if we know not just how many pages are in a book, but also where specific pages are.\n
  The content of each tuple in the ranges argument is the range start, range end and the number of pages within that range."""
  knownRomans = tuple(x for x in tocMap if isinstance(x,str))
  if roman is not None or len(knownRomans) != 0: return processRomans(roman,ranges,frontRanges,stripText,knownRomans,tocMap,pages,breakMode,pageMode)

  pageLocations:list[int] = []
  processedPages = 0
  for [start,end,numPages] in ranges:
    pageLocations = pageLocations + approximatePageLocations(stripText[start:end],numPages,breakMode,pageMode,start)
    processedPages = processedPages + numPages
  lastRange = ranges[-1] if len(ranges) != 0 else (0,0,0)
  pagesRemaining = pages - processedPages
  if pagesRemaining != 0:
    pageLocations = pageLocations + approximatePageLocations(stripText[lastRange[1]:],pagesRemaining,breakMode,pageMode,lastRange[1])
  return (0,pageLocations)


def approximatePageLocationsByWords(stripped:str,pages:int,offset:int):
    wordMatches = tuple(x.start() for x in finditer(r'\S+',stripped))
    pgSize = len(wordMatches)/pages
    if offset == 0: print(f'Calculated approximate page size of {pgSize} words')
    calculatedSizes.append(pgSize)
    pgListW = [wordMatches[round(pgSize*i)] for i in range(pages)]
    return pgListW if offset == 0 else [p+offset for p in pgListW]


def shiftPageListing(pgList:list[int],stripped:str,pgSize:int, breakMode:str):
    for [i,p] in enumerate(pgList):
      # getting the text of the current page.
      page = stripped[p:p+pgSize]
      # the 'prev' mode uses the same operations as the 'next' mode, just on the reversed string.
      if breakMode == 'prev': page = page[::-1]
      # finding the next/previous whitespace character.
      nextSpace = search(r'\s',page)
      # If we don't find any whitespace we just leave the break where it is.
      if nextSpace is None: continue
      # in the 'prev' mode we need to subtract the index we found.
      pgList[i] = (p + nextSpace.start() * (1 if breakMode == 'next' else -1))
    return pgList


def approximatePageLocations(stripped:str, pages = 5, breakMode='split', pageMode:str|int='chars',offset=0,roman:int|None=None) -> list[int]:
  """Generate a list of page break locations based on the chosen page number and paging mode."""
    # taking care of the 'lines' paging mode
  if len(stripped) == 0: return [0]
  if pageMode == 'lines' or isinstance(pageMode, int): return approximatePageLocationsByLine(stripped,pages,pageMode,offset)
  if pageMode == 'words': return approximatePageLocationsByWords(stripped,pages,offset)
  if roman is not None: pages = pages + (roman or 0)
  pgSize = floor(len(stripped)/pages)
  if offset == 0: print(f'Calculated approximate page size of {pgSize} characters')
  calculatedSizes.append(pgSize)
  # The initial locations for our page splits are simply multiples of the page size
  pgList = [i*pgSize for i in range(pages)]
  # the 'split' break mode does not care about breaking pages in the middle of a word, so nothing needs to be done.
  if breakMode == 'split': return pgList
  pgList = shiftPageListing(pgList,stripped,pgSize,breakMode)
  return pgList if offset == 0 else [p+offset for p in pgList]


def mapPages(pagesMapped:list[tuple[int, int]],stripSplits:list[int],docStats:list[tuple[etree.ElementBase, list[tuple[etree.ElementBase, int, int]], dict[str, int]]],docs:list[EpubHtml],epub3Nav:EpubHtml,knownPages:dict[int,str]={},pageOffset=1,roman=0):
  """Function for mapping page locations to actual page break elements in the epub's documents."""
  changedDocs:list[int] = []
  pgLinks:list[str]=[]
  # We use currentIndex and currentIndex to keep track of which document ranges we need.
  for [i,[pg,docIndex]] in enumerate(pagesMapped):
    # showing the progress bar
    mapReport(i+1,len(pagesMapped))
    docLocation = pg - stripSplits[docIndex]
    # Generating links. If the location is right at the start of a file we just link to the file directly
    [doc,docRanges,_] = docStats[docIndex]
    realPage = romanize(i,roman,pageOffset)
    pgLinks.append(docs[docIndex].file_name if docLocation == 0 else f'{docs[docIndex].file_name}#{pageIdPattern(i)}' if realPage not in knownPages else knownPages[realPage])
    # no need to insert a break in that case either
    if docLocation == 0: continue
    # making our page breaker
    breakSpan:etree.ElementBase = doc.makeelement('span',None,None)
    breakSpan.set('id',f'pg_break_{i}')
    # page breaks don't have text, but they do have a value.
    breakSpan.set('value',str(realPage))
    # EPUB2 does not support the epub: namespace.
    if epub3Nav is not None:breakSpan.set('epub:type','pagebreak')
    # we don't recalculate the ranges because page breaks do not add any text.
    insertAtPosition(docLocation,docRanges,breakSpan)
    # noting the filename of every document that was modified.
    if docIndex not in changedDocs: changedDocs.append(docIndex)
  return [pgLinks,changedDocs]


def checkValidConstellations(suggest:bool,auto:bool,useToc:bool,tocMap:tuple[int|str],toc:list):
  if suggest and auto == False: raise ValueError('The --suggest flag can only be used if the --auto Flag is also set.')
  if useToc and checkToC(toc,tocMap) == False: return
  return True


def fillDict(changedDocs:list[int],docs:list[EpubHtml],docStats:list[tuple[etree.ElementBase, list[tuple[etree.ElementBase, int, int]]]]):
  repDict = {}
  # adding all changed documents to our dictionary of changed files
  for x in changedDocs: repDict[docs[x].file_name] = etree.tostring(docStats[x][0],method='html').decode('utf-8')
  return repDict


def mappingWrapper(stripSplits:list[str],docStats:list[tuple[etree.ElementBase, list[tuple[etree.ElementBase, int, int]]]],docs:tuple[EpubHtml],epub3Nav:EpubHtml,knownPages:dict[int|str,str],pageOffset:int,pageLocations:list[int],adobeMap:bool,roman:int|None,fromExisting:str=None,pageTag:str=None):
  if fromExisting is None:
    [pgLinks,changedDocs] = mapPages(
      tuple((pg,next(y[0]-1 for y in enumerate(stripSplits) if y[1] > pg))
      for pg in pageLocations),stripSplits,docStats,docs,epub3Nav,knownPages,pageOffset,roman
      )
    adoMap = None if adobeMap == False else makePgMap(pgLinks,pageOffset,roman)
    return (pgLinks,changedDocs,adoMap,[])
  else:
    print(['Huuka',fromExisting])
    [pgLinks,changedDocs,numList] = identifyPageNodes(docStats,docs,fromExisting,pageTag)
    adoMap = None if adobeMap == False else makePgMap(pgLinks,0)
    return (pgLinks,changedDocs,adoMap,numList)


def getPagesAndRomans(pages:int|str,roman:str|int|None):
  pages = int(pages) if search(r'^\d+$', pages) else pages
  if roman == 'auto': roman = 0
  elif roman is not None and type(roman) != int: roman = romanToInt(roman)
  return (pages,roman)


def sortDocuments(docs:tuple[EpubHtml],spine:list[tuple[str,bool]],nonlinear="append",unlisted="ignore"):
  nonLinearSort = -1 if nonlinear == 'append' else 1
  spineIds = tuple(x[0] for x in tuple(sorted(spine,key=lambda x: nonLinearSort * (1 if x[1]=='yes' else -1))) if (nonlinear != 'ignore' or x[1]=='yes'))
  # sorting the documents by the order they are referenced in the spine
  return docs if len(spineIds) == 0 else tuple(sorted([x for x in docs if (unlisted != "ignore" or x.id in spineIds)],key= lambda d: spineIds.index(d.id) if d.id in spineIds else float('inf' if unlisted == 'append' else '-inf')))


def processEPUB(path:str,pages:int|str,suffix:str=None,newPath:str=None,newName:str=None,noNav=False, noNcX = False,breakMode='next',pageMode:str|int='chars',tocMap:tuple[int|str]=tuple(),adobeMap=False,suggest=False,auto=False,roman:int|str|None=None,nonlinear="append",unlisted="ignore",pageTag:str=None):
  """The main function of the script. Receives all command line arguments and delegates everything to the other functions."""
  (pages,roman) = getPagesAndRomans(pages,roman)
  pub = read_epub(path)
  useToc = len(tocMap) != 0
  if not checkValidConstellations(suggest,auto,useToc,tocMap,pub.toc): return
  [epub3Nav,ncxNav] = prepareNavigations(pub)
  # getting all documents that are not the internal EPUB3 navigation.
  docs = sortDocuments(tuple(x for x in pub.get_items_of_type(ITEM_DOCUMENT) if isinstance(x,EpubHtml)),pub.spine,nonlinear,unlisted)
  # we might have a book that starts at page 0
  pageOffset = 1
  # processing the book contents.
  [stripText,stripSplits,docStats] = getBookContent(docs)
  if pages == 'bookstats': return outputStats(stripText,pageMode)
  elif auto:
    print('Generating automatic page count...')
    pages = pagesFromStats(stripText,pageMode,pages)
    if suggest:return print(f'Suggested page count: {pages}')
    print(f'Generated page count: {pages}')
  print('Starting pagination...')
  buildFromTags= type(pages) == str
  knownPages:dict[int|str,str] = {}
  # figuring out where the pages are located, and mapping those locations back onto the individual documents.
  pageLocations:list[int]=[]
  if useToc and  not buildFromTags:
    if tocMap[0] == 0 and roman is None and next((x for x in tocMap if isinstance(x,str)),None) is None:
      pageOffset = 0
      pages = pages+1
    [frontRanges,contentRanges] = processToC(pub.toc,tocMap,knownPages,docs,stripSplits,docStats,pageOffset)
    [roman,pageLocations] = approximatePageLocationsByRanges(contentRanges,frontRanges,stripText,pages,breakMode,pageMode,roman,tocMap)
  elif not buildFromTags: pageLocations = approximatePageLocations(stripText,pages,breakMode,pageMode,0,roman)
  [pgLinks,changedDocs,adoMap,numList] = mappingWrapper(stripSplits,docStats,docs,epub3Nav,knownPages,pageOffset,pageLocations,adobeMap,roman,pages if buildFromTags else None,pageTag)
  repDict = fillDict(changedDocs,docs,docStats)
  # finally, we save all our changed files into a new EPUB.
  if processNavigations(epub3Nav,ncxNav,pgLinks,repDict,noNav, noNcX,pageOffset,roman,numList):overrideZip(path,pathProcessor(path,newPath,newName,suffix),repDict,adoMap)