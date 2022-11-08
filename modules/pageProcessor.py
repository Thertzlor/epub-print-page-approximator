from math import floor
from re import search

from ebooklib import ITEM_DOCUMENT, ITEM_NAVIGATION
from ebooklib.epub import EpubHtml, EpubNav, Link, etree, read_epub, zipfile


def pageIdPattern(num:int,prefix = 'pg_break_'):
  """Just a quick utility function to generate link IDs"""
  return f'{prefix}{num}'

printToc = lambda b : [print(f'{x[0]+1}. {x[1].title}') for x in enumerate(b.toc)]
"""Output all entries of a table of contents to the console. Not used yet."""

def nodeText(node:etree.ElementBase):
  if isinstance(node,etree._Comment): return ''
  # We include a list of all valid HTML tags that we want to include in our text.
  # If we don't filter, itertext includes the content of tags like head, meta and style, which makes no sense for our purposes.
  return ''.join([x for x in node.itertext('html','body','div','span','p','strong','em','a', 'b', 'i','h1','h2','h3','h4', 'h5','h6', 'title', 'figure', 'section','sub','ul','ol','li', 'abbr','blockquote', 'figcaption','aside','cite', 'code','pre', 'nav','tr', 'table','tbody','thead','header','th','td','math','mrow','mspace','msub','mi','mn','mo','var','mtable','mtr','mtd','mtext','msup','mfrac','msqrt','munderover','msubsup','mpadded','mphantom')])

def printProgressBar(iteration:int, total:int, prefix = '', suffix = '', decimals = 1, length = 100, fill = '█', printEnd = "\r"):
    """https://stackoverflow.com/questions/3173320/"""
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end = printEnd)
    # Print New Line on Complete
    if iteration == total: 
        print()

def overrideZip(src:str,dest:str,repDict:dict={}):
  """Zip replacer from the internet because for some reason the write method of the ebook library breaks HTML"""
  with zipfile.ZipFile(src) as inZip, zipfile.ZipFile(dest, "w",compression=zipfile.ZIP_DEFLATED) as outZip:
    # Iterate the input files
    for inZipInfo in inZip.infolist():
      # Read input file
      with inZip.open(inZipInfo) as inFile:
        # Sometimes EbookLib does not include the root epub path in its filenames, so we're using endswith.
        inDict = next((x for x in repDict.keys() if inZipInfo.filename.endswith(x)),None)
        if inDict is not None:
          outZip.writestr(inZipInfo.filename, repDict[inDict].encode('utf-8'))
        # copying non-changed files, saving the mimetype without compression
        else: outZip.writestr(inZipInfo.filename, inFile.read(),compress_type=zipfile.ZIP_STORED if inZipInfo.filename.lower() == 'mimetype' else zipfile.ZIP_DEFLATED)
  print(f'succesfully saved {dest}')
  

def mapReport(a,b):
  """simple printout function for mapping progress"""
  printProgressBar(a,b,f'Mapping page {a} of {b}','Done',2)


def splitStr(s:str,n:int): return[s[i:i+n] for i in range(0, len(s), n)]


def approximatePageLocationsByLine(stripped:str, pages:int, pageMode:str|int):
  """Splitting up the stripped text of the book by number of lines. Takes 'lines' or a maximum line length as its pageMode parameter. """
  lines:list[str]=[]
  # initial split
  splits = stripped.splitlines(keepends=True)
  if pageMode == 'lines':
    # in the simple 'lines' mode we don't care about the length of the lines
    lines= splits
  else:
    # splitting up all lines above the maximum length
    splitLines = [splitStr(x,pageMode) for x in splits]
    # flattening our list of split up strings back into a regular list of strings
    lines = [item for sublist in splitLines for item in sublist]
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
  # step is a float, so we round it to get a valid index.
  pgList = [lineLocations[round(step*i)] for i in range(pages)]
  return pgList


def approximatePageLocations(stripped:str, pages = 5, breakMode='split', pageMode:str|int='chars') -> list[int]:
  """Generate a list of page break locations based on the chosen page number and paging mode."""
  if pageMode == 'lines' or isinstance(pageMode, int):
    # taking care of the 'lines' paging mode
    return approximatePageLocationsByLine(stripped,pages,pageMode)

  pgSize = floor(len(stripped)/pages)
  print(f'Calculated approximate page size of {pgSize} characters')
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
  return pgList


def nodeRanges(node:etree.ElementBase,strippedText:str = None):
  """Receives a node and optionally the stripped text of that node.\n
  Returns a List of tuples, each consisting of a child element and offsets for where its text content starts and ends.
  """
  if strippedText is None: strippedText= nodeText(node)
  baseIndex = 0
  # getting all child nodes containing text.
  rangeList:list[tuple[etree.ElementBase,int,int]] = []
  for [e,t] in [[x,nodeText(x)] for x in node.iter() if nodeText(x) != '']:
    # finding where in our text the node is located
    myIndex = strippedText.find(t,baseIndex)
    childText = next((nodeText(x) for x in iter(e) if nodeText(x) != ''),None)
    # we skip elements that don't have text outside of their child elements.
    if childText == t: continue
    # saving the list entry.
    rangeList.append([e,myIndex,myIndex+len(t)])
    # advancing in our base string, this is how we guarantee identical node text matching the correct child.
    if childText is None: baseIndex = myIndex + len(t)
  return rangeList


def getNodeFromLocation(strippedLoc:int,ranges:list[tuple[etree.ElementBase,int,int]])->tuple[etree.ElementBase,int,int]:
  """Returns node containing the specified location of stripped text based on a list of node ranges (output from nodeRanges).\n
  The returned tuple contains:\n
  -the node itself\n
  -the distance of the location from the start of the node text\n
  -the distance of the location from the end of the node text
  """
  return [[x[0], strippedLoc-x[1], x[2] - strippedLoc] for x in ranges if x[1] <= strippedLoc and x[2] > strippedLoc][-1]


def insertIntoText(newNode:etree.ElementBase,parentNode:etree.ElementBase,strippedLoc:int):
  """Inserting a node into a specific index of another node's text content.
  necessary because insert(0) will always put it after the text."""
  newText = parentNode.text[0:strippedLoc]
  # only the first part of the text will still belong to the parent, the other part becomes the new node's tail
  newTail = parentNode.text[strippedLoc:]
  parentNode.text = newText
  # We are only inserting page breaks, so we don't need to worry about overriding existing tail data.
  newNode.tail = newTail
  # insert at first position
  parentNode.insert(0,newNode)


def insertIntoTail(newNode:etree.ElementBase,parentNode:etree.ElementBase,strippedLoc:int):
  """Inserting a node into a specific index of another node's text content.
  necessary because insert(-1) will always put it before the tail"""
  if parentNode.tag is not None:
    # we do not want to put anything outside the body tag, in that case we insert it at the end.
    if parentNode.tag.lower() == 'body': return parentNode.insert(-1,newNode)
    if parentNode.tag.lower() == 'html': return parentNode.find('x:body',xns).insert(-1,newNode)

  newParentTail = parentNode.tail[0:strippedLoc]
  newChildTail = parentNode.tail[strippedLoc:]
  #deleting the old tail, or else it will be added twice
  parentNode.tail=''
  newNode.tail = newChildTail
  parentNode.addnext(newNode)
  #setting the new tail, needs to happen after insertion.
  parentNode.tail = newParentTail


def insertNodeAtTextPos(positionData:tuple[etree.ElementBase,int,int],newNode:etree.ElementBase):
  """Takes a node position object (output from getNodeFromLocation()) and inserts a new node at that spot."""
  [el,fromStart,fromEnd] = positionData
  # in some cases we can simply use the tail or text insertion functions directly.
  if el.text is not None and len(el.text) > fromStart: return insertIntoText(newNode,el,fromStart)
  if el.tail is not None and len(el.tail) > fromEnd: return insertIntoTail(newNode,el,len(el.tail)-fromEnd)
  offset = 0 if el.text is None else len(el.text)
  # basically we only get to this part if there's multiple child elements and our node needs to go in the middle.
  for c in el:
    # skipping the content of the child node, we already know our location can't be inside.
    offset = offset+len(nodeText(c) or '')+len(c.tail or '')
    # The location can only be the tail of one of the child nodes, once we find it, we insert the node.
    if fromStart < offset: return insertIntoTail(newNode,c,len(c.tail or '') - (offset-fromStart))
  # Something has gone very wrong if we don't find any viable location, so we print a warning.
  print('could not find insertion spot',fromStart,fromEnd)


def analyzeBook(docs:list[EpubHtml])-> tuple[str,list[int],list[etree.ElementBase]]:
  """Extract the full text content of an ebook, outputs the text stripped of HTML, a list of document locations within that string and one list of xml documents"""
  htmStrings:list[str] = [x.content for x in docs]
  # getting all documents.
  htmDocs: list[etree.ElementBase] = [etree.fromstring(x,etree.HTMLParser()) for x in htmStrings]
  # extracting all text.
  stripStrings:list[str] = [nodeText(x) for x in htmDocs]
  stripSplits:list[int]=[0]
  currentStripSplit = 0
  for string in stripStrings:
    currentStripSplit = currentStripSplit + len(string or '')
    # saving where each separate document starts within the text.
    stripSplits.append(currentStripSplit)
  return [''.join(stripStrings),stripSplits,htmDocs]


def getTocLocations(toc:list[Link],docs:list[EpubHtml],rawText:str,htmSplits:list[int],strippedSplits:list[int]):
  """**NOT YET IMPLEMENTED**"""
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
  """split a string at a certain position, highlight the split with a separator and output a range of characters to either side.\n
  Used for debugging purposes"""
  return f'{str[pos-around:pos]}{sep}{str[pos:pos+around]}'


def relativePath(pathA:str,pathB:str):
  """A function to adjust link paths in case the navigation and content documents are in the same path."""
  [splitA,splitB] = [x.split('/') for x in[pathA,pathB]]
  pathDiff=0
  # comparing each path section of our files.
  for [i,s] in enumerate(splitA):
    # If the path is the same we will remove it from the link
    if s == splitB[i]: pathDiff = pathDiff+1
    # here we found the first section which is not the same
    else: break
  # returning the pruned path.
  return '/'.join(splitB[pathDiff:])


xns = {'x':'*'}
"""Universal namespace for XML traversals"""

def addLinksToNcx(ncx:EpubHtml,linkList:list[str],repDict:dict={}):
  """Function to populate a EPUB2 NCX file with our new list of pages."""
  # getting the XML document
  doc:etree.ElementBase = etree.fromstring(ncx.content)
  # function for generating elements, mostly used to get proper autocomplete
  def tag(name:str,attributes:dict=None)->etree.ElementBase: return doc.makeelement(name,attributes)

  def makeLabel(text:str|int):
    """Generates a navLabel with a child text element, containing the specified text."""
    label = tag('navLabel')
    txt = tag('text')
    txt.text = str(text)
    label.append(txt)
    return label

  def makeTarget(number:int,offset=0):
    "Generates a pageTargets element containing a content tag with a link to the specified page number"
    target = tag('pageTarget',{'id':f'pageNav_{number}', 'type':'normal', 'value':str(number+offset)})
    target.append(makeLabel(number+offset))
    target.append(tag('content',{'src':relativePath(ncx.file_name,linkList[number])}))
    return target

  pList:etree.ElementBase = doc.find('x:pageList',xns)
  # the ncx file might already have a pageList element.
  if(pList is not None): 
    if input('EPUB NCX already has a pageList element.\nContinue and overwrite it? [y/N]:').lower() != 'y': return False
    # getting rid of the old element
    pList.getparent().remove(pList)
  # the new tag we are inserting
  genList = tag('pageList')
  genList.append(makeLabel('Pages'))
  # generating our links. Since the Ids are zero indexed, we provide an offset of 1 for the text.
  for i in range(len(linkList)): genList.append(makeTarget(i,1))
  doc.append(genList)
  # inserting the final text of our ncx file into our dictionary of changes.
  # also inserting line breaks for prettier formatting.
  repDict[ncx.file_name] = etree.tostring(doc).decode('utf-8').replace('<pageTarget','\n<pageTarget')
  return True


def addLinksToNav(nav:EpubHtml,linkList:list[str],repDict:dict={}):
  """Function to populate a EPUB3 Nav.xhtml file with our new list of pages."""
  doc:etree.ElementBase = etree.fromstring(nav.content,etree.HTMLParser())
  # function for generating elements, mostly used to get proper autocomplete
  def tag(name:str,attributes:dict=None)->etree.ElementBase: return doc.makeelement(name,attributes)
  def makeTarget(number:int,offset=0):
    """generating a list entry with a link to the page break element."""
    target = tag('li')
    link = tag('a',{'href':relativePath(nav.file_name,linkList[number])})
    link.text=str(number+offset)
    target.append(link)
    return target
  
  body:etree.ElementBase = doc.find('x:body',xns)
  # perhaps the file already has a page-list navigation element
  oldNav:etree.ElementBase = next((x for x in body.findall('x:nav',xns) if x.get('epub:type') == 'page-list'),None)
  if(oldNav is not None): 
    if input('EPUB3 navigation already has a page-list.\nContinue and overwrite it? [y/N]:').lower() != 'y': return False
    # getting rid of the old element
    oldNav.getparent().remove(oldNav)
  # generating a new navigation tag for our list and hiding it.
  mainNav = tag('nav',{'epub:type':'page-list', 'hidden':''})
  # we don't technically need a header, but it's polite to have one I guess.
  header = tag('h1')
  header.text='List of Pages'
  mainNav.append(header)
  lst = tag('ol')
  # generating our links. Since the Ids are zero indexed, we provide an offset of 1 for the text.
  for i in range(len(linkList)): lst.append(makeTarget(i,1))
  mainNav.append(lst)
  body.append(mainNav)
  # inserting the final text of our nav.xhtml file into our dictionary of changes.
  # also inserting line breaks for prettier formatting.
  repDict[nav.file_name] = etree.tostring(doc).decode('utf-8').replace('<li','\n<li')
  return True


def pathProcessor(oldPath:str,newPath:str=None,newName:str=None,suffix:str='_paginated'):
  """Function to generate an output path for the new EPUB based on user preferences"""
  pathSplit = oldPath.split("/")
  oldFileName = pathSplit.pop()
  # if there's a new name, the suffix isn't necessary.
  if newName is not None:suffix = ''
  finalName = newName or oldFileName
  # the epub extension may be omitted, but in case it isn't we cut it off here.
  if finalName.lower().endswith('.epub'): finalName = finalName[:-5]
  # putting the path back together
  return f'{newPath or "/".join(pathSplit)}{finalName}{suffix}.epub'


def mapPages(pages:int,pagesMapped:list[tuple[int, int]],stripSplits:list[int],docStats:list[etree.ElementBase],docs:list[EpubHtml],epub3Nav:EpubHtml):
  """Function for mapping page locations to actual page break elements in the epub's documents."""
  changedDocs:list[str] = []
  pgLinks:list[str]=[]
  # We use currentIndex and currentIndex to keep track of which document ranges we need.
  currentIndex:int = None
  currentRanges:list[tuple[etree.ElementBase, int, int]] = None
  for [i,[pg,docIndex]] in enumerate(pagesMapped):
    # showing the progress bar
    mapReport(i+1,pages)
    docLocation = pg - stripSplits[docIndex]
    # Generating links. If the location is right at the start of a file we just link to the file directly
    pgLinks.append(docs[docIndex].file_name if docLocation == 0 else f'{docs[docIndex].file_name}#{pageIdPattern(i)}')
    # no need to insert a break in that case either
    if docLocation == 0: continue
    doc = docStats[docIndex]
    if currentIndex != docIndex: 
      currentIndex = docIndex
      currentRanges = nodeRanges(doc)
    # making our page breaker
    breakSpan:etree.ElementBase = doc.makeelement('span')
    breakSpan.set('id',f'pg_break_{i}')
    # page breaks don't have text, but they do have a value.
    breakSpan.set('value',str(i+1))
    # EPUB2 does not support the epub: namespace.
    if epub3Nav is not None:breakSpan.set('epub:type','pagebreak')
    # we don't recalculate the ranges because page breaks do not add any text.
    insertNodeAtTextPos(getNodeFromLocation(docLocation,currentRanges),breakSpan)
    # noting the filename of every document that was modified.
    if docIndex not in changedDocs: changedDocs.append(docIndex)
  return [pgLinks,changedDocs]

def prepareNavigations(pub)->tuple[EpubNav,EpubHtml]:
  """Extract the Navigation files from the EPUB"""
  ncxNav:EpubHtml = next((x for x in pub.get_items_of_type(ITEM_NAVIGATION)),None)
  epub3Nav:EpubHtml = next((x for x in pub.get_items_of_type(ITEM_DOCUMENT) if isinstance(x,EpubNav)),None)
  # a valid EPUB will have at least one type of navigation.
  if ncxNav is None and epub3Nav is None: raise LookupError('No navigation files found in EPUB, file probably is not valid.')
  return [epub3Nav,ncxNav]


def processNavigations(epub3Nav:EpubNav,ncxNav:EpubHtml,pgLinks:list[str],repDict:dict,noNav:bool, noNcX:bool):
  """Adding the link list to any available navigation files."""
  if epub3Nav and not noNav: 
    if addLinksToNav(epub3Nav,pgLinks,repDict) == False: return print('Pagination Cancelled') or False
  if ncxNav and not noNcX: 
     if addLinksToNcx(ncxNav,pgLinks,repDict) == False :return print('Pagination Cancelled') or False
  return True 
  

def processEPUB(path:str,pages:int,suffix=None,newPath=None,newName=None,noNav=False, noNcX = False,breakMode='next',pageMode:str|int='chars'):
  """The main function of the script. Receives all command line arguments and delegates everything to the other functions."""
  pub = read_epub(path)
  [epub3Nav,ncxNav] = prepareNavigations(pub)
  # getting all documents that are not the internal EPUB3 navigation.
  docs:list[EpubHtml] = [x for x in pub.get_items_of_type(ITEM_DOCUMENT) if isinstance(x,EpubHtml)]
  # processing the book contents.
  [stripText,stripSplits,docStats] = analyzeBook(docs)
  # figuring out where the pages are located, and mapping those locations back onto the individual documents.
  pagesMapped:list[tuple[int,int]] = [
    [x,next(y[0]-1 for y in enumerate(stripSplits) if y[1] > x)] 
    for x in approximatePageLocations(stripText,pages,breakMode,pageMode)
  ]
  [pgLinks,changedDocs] = mapPages(pages,pagesMapped,stripSplits,docStats,docs,epub3Nav)
  repDict = {}
  # adding all changed documents to our dictionary of changed files
  for x in changedDocs: repDict[docs[x].file_name] = etree.tostring(docStats[x]).decode('utf-8')
  # finally, we save all our changed files into a new EPUB.
  if processNavigations(epub3Nav,ncxNav,pgLinks,repDict,noNav, noNcX):overrideZip(path,pathProcessor(path,newPath,newName,suffix),repDict)