from math import ceil, floor
from re import finditer, search

from ebooklib import ITEM_DOCUMENT
from ebooklib.epub import EpubHtml, etree, read_epub

from modules.helperfunctions import overrideZip
from modules.navutils import makePgMap, prepareNavigations, processNavigations
from modules.nodeutils import getBookContent, getNodeForIndex, insertAtPosition
from modules.pathutils import pageIdPattern, pathProcessor
from modules.progressbar import mapReport
from modules.statisticsutils import lineSplitter, textStats
from modules.tocutils import checkToC, processToC


def approximatePageLocationsByLine(stripped:str, pages:int, pageMode:str|int,offset=0):
  """Splitting up the stripped text of the book by number of lines. Takes 'lines' or a maximum line length as its pageMode parameter. """
  lines = lineSplitter(stripped,pageMode)
  # This should only seldomly happen, but best to be prepared.
  if len(lines) < pages: raise BaseException(f'The number of detected lines in the book ({len(lines)}) is smaller than the number of pages to generate ({pages}). Consider using the "chars" paging mode for this book.')
  lineOffset=0
  lineLocations:list[int]=[]
  # for most of the splitting we don't care about text content, just locations.
  for line in lines:
    lineLocations.append(lineOffset)
    lineOffset = lineOffset + len(line)
  # calculating the number of lines per page.
  step = len(lines)/pages
  print(f'Calculated approximate page height of ${"{:.2f}".format(step)} lines')
  # step is a float, so we round it to get a valid index.
  pgList = [lineLocations[round(step*i)] for i in range(pages)]
  return pgList if offset == 0 else [p+offset for p in pgList]

def approximatePageLocationsByRanges(ranges:list[tuple[int,int,int]],stripText:str,pages = 5, breakMode='split', pageMode:str|int='chars'):
  """This is the page location function used if we know not just how many pages are in a book, but also where specific pages are.\n
  The content of each tuple in the ranges argument is the range start, range end and the number of pages within that range."""
  pageLocations:list[int] = []
  processedPages = 0
  for [start,end,numPages] in ranges: 
    pageLocations = pageLocations + approximatePageLocations(stripText[start:end],numPages,breakMode,pageMode,start)
    processedPages = processedPages + numPages
  lastRange = ranges[-1]
  pagesRemaining = pages - processedPages
  if pagesRemaining != 0: pageLocations = pageLocations + approximatePageLocations(stripText[lastRange[1]:],pagesRemaining,breakMode,pageMode,lastRange[1])
  return pageLocations

def approximatePageLocations(stripped:str, pages = 5, breakMode='split', pageMode:str|int='chars',offset=0) -> list[int]:
  """Generate a list of page break locations based on the chosen page number and paging mode."""
  if pageMode == 'lines' or isinstance(pageMode, int):
    # taking care of the 'lines' paging mode
    return approximatePageLocationsByLine(stripped,pages,pageMode,offset)
  pgSize = 0
  
  if pageMode == 'words':
    wordMatches = tuple(x.start() for x in finditer(r'\S+',stripped))
    pgSize = len(wordMatches)/pages
    if offset == 0: print(f'Calculated approximate page size of {pgSize} words')
    pgListW = [wordMatches[round(pgSize*i)] for i in range(pages)]
    return pgListW if offset == 0 else [p+offset for p in pgListW]

  pgSize = floor(len(stripped)/pages)
  if offset == 0: print(f'Calculated approximate page size of {pgSize} characters')
  # The initial locations for our page splits are simply multiples of the page size
  pgList = [i*pgSize for i in range(pages)]
  # the 'split' break mode does not care about breaking pages in the middle of a word, so nothing needs to be done.
  if breakMode == 'split': return pgList
  for [i,p] in enumerate(pgList):
    # getting the text of the current page.
    page = stripped[p:p+pgSize]
    # the 'prev' mode uses the same operations as the 'next' mode, just on the reversed string.
    if breakMode == 'prev': page = page[::-1]
    # finding the next/previous whitespace character.
    nextSpace = search(r'\s',page)
    # If we don't find any whitespace we just leave the break where it is.
    if nextSpace is not None: 
      # in the 'prev' mode we need to subtract the index we found.
      pgList[i] = (p + nextSpace.start() * (1 if breakMode == 'next' else -1))
  return pgList if offset == 0 else [p+offset for p in pgList]


def mapPages(pages:int,pagesMapped:list[tuple[int, int]],stripSplits:list[int],docStats:list[tuple[etree.ElementBase, list[tuple[etree.ElementBase, int, int]], dict[str, int]]],docs:list[EpubHtml],epub3Nav:EpubHtml,knownPages:dict[int,str]={},pageOffset=1):
  """Function for mapping page locations to actual page break elements in the epub's documents."""
  changedDocs:list[str] = []
  pgLinks:list[str]=[]
  # We use currentIndex and currentIndex to keep track of which document ranges we need.
  for [i,[pg,docIndex]] in enumerate(pagesMapped):
    # showing the progress bar
    mapReport(i+1,pages)
    docLocation = pg - stripSplits[docIndex]
    # Generating links. If the location is right at the start of a file we just link to the file directly
    [doc,docRanges,_] = docStats[docIndex]
    pgLinks.append(docs[docIndex].file_name if docLocation == 0 else f'{docs[docIndex].file_name}#{pageIdPattern(i)}' if i not in knownPages else knownPages[i])
    # no need to insert a break in that case either
    if docLocation == 0: continue
    # making our page breaker
    breakSpan:etree.ElementBase = doc.makeelement('span')
    breakSpan.set('id',f'pg_break_{i}')
    # page breaks don't have text, but they do have a value.
    breakSpan.set('value',str(i+pageOffset))
    # EPUB2 does not support the epub: namespace.
    if epub3Nav is not None:breakSpan.set('epub:type','pagebreak')
    # we don't recalculate the ranges because page breaks do not add any text.
    insertAtPosition(getNodeForIndex(docLocation,docRanges),breakSpan)
    # noting the filename of every document that was modified.
    if docIndex not in changedDocs: changedDocs.append(docIndex)
  return [pgLinks,changedDocs]
  

def outputStats(text,pageMode):
  print('Displaying book stats...')
  [chars,lines,words] = textStats(text,pageMode)
  print(f'characters:{chars}, lines:{lines}, words:{words}')

def pagesFromStats(text:str,pageMode:str|int,pageDef:int):
  [chars,lines,words] = textStats(text,pageMode)
  if pageMode == 'chars': return ceil(chars/pageDef)
  if pageMode == 'words': return ceil(words/pageDef)
  return ceil(lines/pageDef)

def processEPUB(path:str,pages:int|str,suffix=None,newPath=None,newName=None,noNav=False, noNcX = False,breakMode='next',pageMode:str|int='chars',tocMap:tuple[int]=(),adobeMap=False,suggest=False,auto=False):
  """The main function of the script. Receives all command line arguments and delegates everything to the other functions."""
  if suggest and auto ==  False: raise ValueError('The --suggest flag can only be used if the --auto Flag is also set.')
  pages = int(pages) if search(r'^\d+$', pages) else pages
  pub = read_epub(path)
  useToc = len(tocMap) != 0
  if useToc and checkToC(pub.toc,tocMap) == False: return
  [epub3Nav,ncxNav] = prepareNavigations(pub)
  # getting all documents that are not the internal EPUB3 navigation.
  docs = tuple(x for x in pub.get_items_of_type(ITEM_DOCUMENT) if isinstance(x,EpubHtml))
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
  knownPages:dict[int,str] = {}
  # figuring out where the pages are located, and mapping those locations back onto the individual documents.
  pageLocations:list[int]
  if useToc:
    mappedToc = processToC(pub.toc,tocMap,knownPages,docs,stripSplits,docStats)
    if next((t for t in tocMap if t != 0),0) == 1 and mappedToc[0][1] != 0:
      pageOffset = 0
      pages = pages + 1
    pageLocations = approximatePageLocationsByRanges(mappedToc,stripText,pages,breakMode,pageMode)
  else: pageLocations = approximatePageLocations(stripText,pages,breakMode,pageMode)
  # return print(len(pageLocations),pageLocations)
  [pgLinks,changedDocs] = mapPages(
    pages,tuple((pg,next(y[0]-1 for y in enumerate(stripSplits) if y[1] > pg)) 
    for pg in pageLocations),stripSplits,docStats,docs,epub3Nav,knownPages,pageOffset
    )
  adoMap = None if adobeMap == False else makePgMap(pgLinks,pageOffset)
  repDict = {}
  # adding all changed documents to our dictionary of changed files
  for x in changedDocs: repDict[docs[x].file_name] = etree.tostring(docStats[x][0]).decode('utf-8')
  # finally, we save all our changed files into a new EPUB.
  if processNavigations(epub3Nav,ncxNav,pgLinks,repDict,noNav, noNcX,pageOffset):overrideZip(path,pathProcessor(path,newPath,newName,suffix),repDict,adoMap)