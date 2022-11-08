from math import floor
from re import search

from ebooklib import ITEM_DOCUMENT, ITEM_NAVIGATION
from ebooklib.epub import EpubHtml, EpubNav, Link, etree, read_epub, zipfile


def pageIdPattern(num:int,prefix = 'pg_break_'):
  return f'{prefix}{num}'

printToc = lambda b : [print(f'{x[0]+1}. {x[1].title}') for x in enumerate(b.toc)]

def nodeText(node:etree.ElementBase):
  if isinstance(node,etree._Comment): return ''
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


def splitstr(s:str,n:int): return[s[i:i+n] for i in range(0, len(s), n)]


def approximatePageLocationsByLine(stripped:str, pages = 5, breakMode='split', pageMode:str|int='chars'):
  lines:list[str]=[]
  splits = stripped.splitlines(keepends=True)
  if pageMode == 'lines':
    lines= splits
  else:
    splitLines = [splitstr(x,pageMode) for x in splits]
    lines = [item for sublist in splitLines for item in sublist]
  if len(lines) < pages: raise BaseException(f'The number of detected lines in the book ({len(lines)}) is smaller than the number of pages to generate ({pages}). Consider using the "chars" paging mode for this book.')
  lineOffset=0
  lineLocations:list[int]=[]
  for [i,l] in enumerate(lines):
    lineLocations.append(lineOffset)
    lineOffset = lineOffset + len(l)
  
  step = len(lines)/pages
  pgList = [lineLocations[round(step*i)] for i in range(pages)]
  return pgList


def approximatePageLocations(stripped:str, pages = 5, breakMode='split', pageMode:str|int='chars') -> list[int]:
  if pageMode == 'lines' or isinstance(pageMode, int): 
    return approximatePageLocationsByLine(stripped,pages,breakMode,pageMode)

  pgSize = floor(len(stripped)/pages)
  print(f'Calculated approximate page size of {pgSize} characters')
  pgList = [i*pgSize for i in range(pages)]
  if breakMode == 'split': return pgList
  for [i,p] in enumerate(pgList):
    page = stripped[p:p+pgSize]
    if breakMode == 'prev': page = page[::-1]
    nextSpace = search(r'\s',page)
    if nextSpace is not None: 
      pgList[i] = (p + nextSpace.start() * (1 if breakMode == 'next' else -1)) 
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


def getNodeFromLocation(strippedLoc:int,ranges:list[tuple[etree.ElementBase,int,int,str]])->tuple[etree.ElementBase,int,int]:
  """Returns node containing the specified location of strippedtext based on a list of node ranges (output from nodeRanges).\n
  The returned tuple contains:\n
  -the node itself\n
  -the distance of the location from the start of the node text\n
  -the distance of the location from the end of the node text\n
  """
  matches=[[x[0], strippedLoc-x[1], x[2] - strippedLoc] for x in ranges if x[1] <= strippedLoc and x[2] > strippedLoc]
  return matches[-1]


def insertIntoText(newNode:etree.ElementBase,parentNode:etree.ElementBase,strippedLoc:int):
  newText = parentNode.text[0:strippedLoc]
  newTail = parentNode.text[strippedLoc:]
  parentNode.text = newText
  newNode.tail = newTail
  parentNode.insert(0,newNode)


def insertIntoTail(newNode:etree.ElementBase,parentNode:etree.ElementBase,strippedLoc:int):
  if parentNode.tag is not None:
    if parentNode.tag.lower() == 'body': return parentNode.insert(-1,newNode)
    if parentNode.tag.lower() == 'html': return parentNode.find('x:body',xns).insert(-1,newNode)

  newParentTail = parentNode.tail[0:strippedLoc]
  newChildTail = parentNode.tail[strippedLoc:]
  #deleting zhe old tail, or else it will be added twice
  parentNode.tail=''
  newNode.tail = newChildTail
  parentNode.addnext(newNode)
  #setting the new tail
  parentNode.tail = newParentTail


def insertNodeAtTextPos(positionData:tuple[etree.ElementBase,int,int],newNode:etree.ElementBase):
  """Takes a node position object (output from getNodeFromLocation)"""
  [el,fromStart,fromEnd] = positionData
  if el.text is not None and len(el.text) > fromStart: return insertIntoText(newNode,el,fromStart)
  if el.tail is not None and len(el.tail) > fromEnd: return insertIntoTail(newNode,el,len(el.tail)-fromEnd)
  offset = 0 if el.text is None else len(el.text)
  for c in el:
    offset = offset+len(nodeText(c) or '')+len(c.tail or '')
    if fromStart < offset: return insertIntoTail(newNode,c,len(c.tail or '') - (offset-fromStart))
  print('could not find insertion spot',fromStart,fromEnd)


def analyzeBook(docs:list[EpubHtml])-> tuple[str,list[int],list[etree.ElementBase]]:
  """Extract the full text content of an ebook, one string containing the full HTML, one containing only the text
  and one list of xml documents"""
  htmStrings:list[str] = [x.content for x in docs]
  htmDocs: list[etree.ElementBase] = [etree.fromstring(x,etree.HTMLParser()) for x in htmStrings]
  stripStrings:list[str] = [nodeText(x) for x in htmDocs]
  stripSplits:list[int]=[0]
  currentStripSplit = 0
  docStats:list[etree.ElementBase] = []
  for [i,t] in enumerate(stripStrings):
    docStats.append(htmDocs[i])
    currentStripSplit = currentStripSplit + len(t or '')
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
  """split a string at a certain position, highlight the split with a separator and output a range of characters to either side.\n
  Used for debugging purposes"""
  return f'{str[pos-around:pos]}{sep}{str[pos:pos+around]}'


def relPath(pathA:str,pathB:str):
  [splitA,splitB] = [x.split('/') for x in[pathA,pathB]]
  pathDiff=0
  for [i,s] in enumerate(splitA):
    if s == splitB[i]: pathDiff = pathDiff+1
    else: break
  return '/'.join(splitB[pathDiff:])


xns = {'x':'*'}


def addListToNcx(ncx:EpubHtml,linkList:list[str],repDict:dict={}):
  doc:etree.ElementBase = etree.fromstring(ncx.content)
  def tag(name:str,attributes:dict=None)->etree.ElementBase: return doc.makeelement(name,attributes)
  def makeLabel(text:str|int):
    label = tag('navLabel')
    txt = tag('text')
    txt.text = str(text)
    label.append(txt)
    return label
  def makeTarget(number:int,offset=0):
    target = tag('pageTarget',{'id':f'pageNav_{number}', 'type':'normal', 'value':str(number+offset)})
    target.append(makeLabel(number+offset))
    target.append(tag('content',{'src':relPath(ncx.file_name,linkList[number])}))
    return target
  pList:etree.ElementBase = doc.find('x:pageList',xns)
  if(pList is not None): 
    if input('EPUB NCX already has a pageList element.\nContinue and overwrite it? [y/N]').lower() != 'y': return False
    pList.getparent().remove(pList)
  genList = tag('pageList')
  genList.append(makeLabel('Pages'))
  for i in range(len(linkList)): genList.append(makeTarget(i,1))
  doc.append(genList)
  ncxString:str = etree.tostring(doc)
  repDict[ncx.file_name] = ncxString.decode('utf-8').replace('<pageTarget','\n<pageTarget')
  return True


def addListToNav(nav:EpubHtml,linkList:list[str],repDict:dict={}):
  doc:etree.ElementBase = etree.fromstring(nav.content,etree.HTMLParser())
  def tag(name:str,attributes:dict=None)->etree.ElementBase: return doc.makeelement(name,attributes)
  def makeTarget(number:int,offset=0):
    target = tag('li')
    link = tag('a',{'href':relPath(nav.file_name,linkList[number])})
    link.text=str(number+offset)
    target.append(link)
    return target
  body:etree.ElementBase = doc.find('x:body',xns)
  oldNav:etree.ElementBase = next((x for x in body.findall('x:nav',xns) if x.get('epub:type') == 'page-list'),None)
  if(oldNav is not None): 
    if input('EPUB3 navigation already has a page-list.\nContinue and overwrite it? [y/N]').lower() != 'y': return False
    oldNav.getparent().remove(oldNav)
  mainNav = tag('nav',{'epub:type':'page-list', 'hidden':''})
  header = tag('h1')
  header.text='List of Pages'
  mainNav.append(header)
  lst = tag('ol')
  for i in range(len(linkList)): lst.append(makeTarget(i,1))
  mainNav.append(lst)
  body.append(mainNav)
  navString:str = etree.tostring(doc)
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


def mapPages(pages:int,pagesMapped:list[tuple[int, int]],stripSplits:list[int],docStats:list[etree.ElementBase],docs:list[EpubHtml],epub3Nav:EpubHtml):
  changedDocs:list[str] = []
  pgLinks:list[str]=[]
  for [i,[pg,docIndex]] in reversed(list(enumerate(pagesMapped))):
    mapReport(pages-i,pages)
    docLocation = pg - stripSplits[docIndex]
    #if the location is right at teh start of a file we just lnk to the file directly
    pgLinks.append(docs[docIndex].file_name if docLocation == 0 else f'{docs[docIndex].file_name}#{pageIdPattern(i)}')
    # no need to insert a break in this case either
    if docLocation == 0: continue
    doc = docStats[docIndex]
    breakSpan:etree.ElementBase = doc.makeelement('span')
    breakSpan.set('id',f'pg_break_{i}')
    breakSpan.set('value',str(i+1))
    # EPUB2 does not support the epub: namespace.
    if epub3Nav is not None:breakSpan.set('epub:type','pagebreak')
    insertNodeAtTextPos(getNodeFromLocation(docLocation,nodeRanges(doc)),breakSpan)
    if docIndex not in changedDocs: changedDocs.append(docIndex)
  pgLinks.reverse()
  return [pgLinks,changedDocs]


def processEPUB(path:str,pages:int,suffix=None,newPath=None,newName=None,noNav=False, noNcX = False,breakMode='next',pageMode:str|int='chars'):
  pub = read_epub(path)
  ncxNav:EpubHtml = next((x for x in pub.get_items_of_type(ITEM_NAVIGATION)),None)
  epub3Nav:EpubHtml = next((x for x in pub.get_items_of_type(ITEM_DOCUMENT) if isinstance(x,EpubNav)),None)
  if ncxNav is None and epub3Nav is None: raise LookupError('No navigation files found in EPUB, file probably is not valid.')
  # getting all documents that are not the internal EPUB3 navigation
  docs:list[EpubHtml] = [x for x in pub.get_items_of_type(ITEM_DOCUMENT) if isinstance(x,EpubHtml)]
  [stripText,stripSplits,docStats] = analyzeBook(docs)
  stripPageIndex = approximatePageLocations(stripText,pages,breakMode,pageMode)
  pagesMapped:list[tuple[int,int]] = [[x,next(y[0]-1 for y in enumerate(stripSplits) if y[1] > x)] for x in stripPageIndex]
  [pgLinks,changedDocs] = mapPages(pages,pagesMapped,stripSplits,docStats,docs,epub3Nav)
  repDict = {}
  for x in changedDocs: repDict[docs[x].file_name] = etree.tostring(docStats[x]).decode('utf-8')
  if epub3Nav and not noNav: 
    if addListToNav(epub3Nav,pgLinks,repDict) == False: return print('Pagination Cancelled')
  if ncxNav and not noNcX: 
     if addListToNcx(ncxNav,pgLinks,repDict) == False :return print('Pagination Cancelled')
  overrideZip(path,pathProcessor(path,newPath,newName,suffix),repDict)
