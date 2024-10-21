from ebooklib.epub import EpubHtml, etree

from modules.helperfunctions import romanize, parseSelectors, matchIdSelector
from modules.pathutils import relativePath
from modules.progressbar import mapReport
from re import search

xns = {'x':'*'}
"""Universal namespace for XML traversals"""

def nodeText(node:etree.ElementBase):
  if isinstance(node,etree._Comment): return ''
  # We include a list of all valid HTML tags that we want to include in our text.
  # If we don't filter, itertext includes the content of tags like head, meta and style, which makes no sense for our purposes.
  return ''.join([x for x in node.itertext('html','body','div','span','p','strong','em','a', 'b', 'i','h1','h2','h3','h4', 'h5','h6', 'title', 'figure', 'section','sub','ul','ol','li', 'abbr','blockquote', 'figcaption','aside','cite', 'code','pre', 'nav','tr', 'table','tbody','thead','header','th','td','math','mrow','mspace','msub','mi','mn','mo','var','mtable','mtr','mtd','mtext','msup','mfrac','msqrt','munderover','msubsup','mpadded','mphantom')])


def addPageMapRefs(opf)-> None|bytes:
  opfText = opf.decode('utf-8')
  if('page-map.xml' in opfText): None
  myOpf:etree.ElementBase = etree.fromstring(opf)
  spine:etree.ElementBase = myOpf.find('x:spine',xns)
  if spine is None:
    spine = myOpf.makeelement('spine',{'page-map':'map'})
    myOpf.append(spine)
  else: spine.set('page-map','map')
  manifest:etree.ElementBase = myOpf.find('x:manifest',xns)
  manifest.append(myOpf.makeelement('item',{'href':'page-map.xml','id':'map','media-type':"application/oebps-page-map+xml"}))
  return etree.tostring(myOpf)


def addLinksToNcx(ncx:EpubHtml,linkList:list[str],repDict:dict={}, pageOffset = 1,roman=0,numList:list[int|str]=[]):
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

  def makeTarget(number:int,offset=0,replace=None):
    "Generates a pageTargets element containing a content tag with a link to the specified page number"
    target = tag('pageTarget',{'id':f'pageNav_{number}', 'type':'normal', 'value':str(romanize(replace or number,roman,offset))})
    target.append(makeLabel(romanize(replace or number,roman,offset)))
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
  for i in range(len(linkList)): genList.append(makeTarget(i,pageOffset if i >= len(numList) else 0,None if i >= len(numList) else numList[i]))
  doc.append(genList)
  # inserting the final text of our ncx file into our dictionary of changes.
  # also inserting line breaks for prettier formatting.
  repDict[ncx.file_name] = etree.tostring(doc).decode('utf-8').replace('<pageTarget','\n<pageTarget')
  return True


def addLinksToNav(nav:EpubHtml,linkList:list[str],repDict:dict={},pageOffset=1,roman=0,numList:list[int|str]=[]):
  """Function to populate a EPUB3 Nav.xhtml file with our new list of pages."""
  doc:etree.ElementBase = etree.fromstring(nav.content,etree.HTMLParser(encoding='utf8'))
  # function for generating elements, mostly used to get proper autocomplete
  def tag(name:str,attributes:dict=None)->etree.ElementBase: return doc.makeelement(name,attributes)
  def makeTarget(number:int,offset=0,replace=None):
    """generating a list entry with a link to the page break element."""
    target = tag('li')
    link = tag('a',{'href':relativePath(nav.file_name,linkList[number])})
    link.text=str(romanize(replace or number,roman,offset))
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
  for i in range(len(linkList)): lst.append(makeTarget(i,pageOffset if i >= len(numList) else 0,None if i >= len(numList) else numList[i]))
  mainNav.append(lst)
  body.append(mainNav)
  # inserting the final text of our nav.xhtml file into our dictionary of changes.
  # also inserting line breaks for prettier formatting.
  repDict[nav.file_name] = etree.tostring(doc).decode('utf-8').replace('<li','\n<li')
  return True


def nodeRanges(node:etree.ElementBase,strippedText:str = None):
  """Receives a node and optionally the stripped text of that node.\n
  Returns a List of tuples, each consisting of a child element and offsets for where its text content starts and ends.
  """
  if strippedText is None: strippedText= nodeText(node)
  baseIndex = 0
  # getting all child nodes containing text.
  rangeList:list[tuple[etree.ElementBase,int,int]] = []
  idLocations:dict[str,int]={}
  def addId(element:etree.ElementBase,idx:int):
    elId = element.get('id')
    if elId: idLocations[elId] = idx
  for (e,t) in tuple((x,nodeText(x)) for x in node.iter()):
    # finding where in our text the node is located
    if t == '':
      addId(e,baseIndex)
      continue
    myIndex = strippedText.find(t,baseIndex)
    addId(e,myIndex)
    childText = next((nodeText(x) for x in iter(e) if nodeText(x) != ''),None)
    # we skip elements that don't have text outside of their child elements.
    if childText == t: continue
    # saving the list entry.
    rangeList.append((e,myIndex,myIndex+len(t)))
    # advancing in our base string, this is how we guarantee identical node text matching the correct child.
    if childText is None: baseIndex = myIndex + len(t)
  return (rangeList,idLocations)


def getNodeForIndex(strippedLoc:int,ranges:list[tuple[etree.ElementBase,int,int]]):
  """Returns node containing the specified location of stripped text based on a list of node ranges (output from nodeRanges).\n
  The returned tuple contains:\n
  -the node itself\n
  -the distance of the location from the start of the node text\n
  -the distance of the location from the end of the node text
  """
  return tuple((x[0], strippedLoc-x[1], x[2] - strippedLoc) for x in ranges if x[1] <= strippedLoc and x[2] > strippedLoc)[-1]


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


def insertAtPosition(docLocation:int,docRanges:list[tuple[etree.ElementBase, int, int]],newNode:etree.ElementBase):
  """Takes a node position object (output from getNodeFromLocation()) and inserts a new node at that spot."""
  [el,fromStart,fromEnd] = getNodeForIndex(docLocation,docRanges)
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
  print('Could not find insertion spot',fromStart,fromEnd)

def identifyPageNodes(docs:list[tuple[etree.ElementBase, list[tuple[etree.ElementBase, int, int]]]],eDocs:list[EpubHtml],nodeSelector:str,attributeSelector:str,isEpub3=False):
  print('Identifying page markers.')
  currentPage = 0
  numList:list[int|str]=[]
  linkList:list[str]=[]
  changedList:list[int]=[]
  [tagFilter,classFilter,attributeFilter,idFilter] = parseSelectors(nodeSelector)
  attrSplit = None if attributeFilter is None else tuple(x.strip() for x in attributeFilter.split('='))
  for [i,[d,_,_]] in enumerate(docs):
    for e in (d.iter()):
      if ((tagFilter is not None) and e.tag.lower() != tagFilter.lower() ):continue
      if ((classFilter is not None) and classFilter.lower() not in (e.get('class') or '').lower().split(' ')):continue
      if ((attrSplit is not None) and ((e.get(attrSplit[0]) is None) if len(attrSplit) == 1 else (e.get(attrSplit[0]) != attrSplit[1]))):continue
      if ((idFilter is not None) and not matchIdSelector(idFilter,e.get('id'))):continue

      if type(currentPage) == int: currentPage = currentPage+1
      elPage:str
      if attributeSelector is not None:
        elPage = (attributeSelector != '' and e.get(attributeSelector)) or currentPage
        tNum = None if type(elPage) == int else search(r"(\d+)\D*$",elPage or '')
        if tNum: elPage = int(tNum[1])
      else:
        elPage = e.text
        tNum = search(r"(\d+)\D*$",elPage or '')
        if tNum: elPage = int(tNum[1])
        if not elPage:
          numatch = search(r"(\d+)\D*$",e.get('id') or '')
          matchNo = currentPage if numatch is None else int(numatch[1])
          if matchNo != currentPage: currentPage = matchNo
          elPage = matchNo
        else:
          try: currentPage = int(elPage)
          except ValueError: pass

      if not e.get('id'):
        e.set('id',f'pg_{currentPage}')
        if not i in changedList:changedList.append(i)
      linkList.append(f'{eDocs[i].file_name}#{e.get("id")}')

      if isEpub3 and not e.get('epub:type'):
        e.set('epub:type','pagebreak')
        if not i in changedList:changedList.append(i)

      numList.append(currentPage)
  pageNo = len(numList)
  if pageNo == 0: raise LookupError(f'Could not find any valid page markers matching the selector {nodeSelector}')
  print(f'Rebuilding page list from {pageNo} page markers.')
  return (linkList,changedList,numList)

def getBookContent(docs:list[EpubHtml]):
  """Extract the full text content of an ebook, outputs the text stripped of HTML, a list of document locations within that string and one list of xml documents"""
  numDocs=len(docs)
  htmStrings:list[str] = tuple(x.content for x in docs)
  # getting all documents.
  htmDocs: list[etree.ElementBase] = tuple(etree.fromstring(x,etree.HTMLParser(encoding='utf8')) for x in htmStrings)
  # extracting all text.
  stripStrings:list[str] = [nodeText(x) for x in htmDocs]
  htmRanges = tuple(nodeRanges(x,stripStrings[i]) for (i,x) in enumerate(htmDocs) if mapReport(i+1,numDocs,'Parsing HTML'))
  stripSplits=[0]
  currentStripSplit = 0
  for string in stripStrings:
    currentStripSplit = currentStripSplit + len(string or '')
    # saving where each separate document starts within the text.
    stripSplits.append(currentStripSplit)
  return (''.join(stripStrings),stripSplits,tuple((x,htmRanges[i][0],htmRanges[i][1]) for [i,x] in enumerate(htmDocs)))