from ebooklib.epub import EpubHtml, etree


def printToc(b:list,indent='', offset = 1):
  """Output all entries of a table of contents to the console."""
  for t in b:
    if isinstance (t,list) or isinstance(t,tuple): offset = printToc(t,f'{indent}  ',offset)
    else: 
      print(f'{offset}. {indent}{t.title} - {t.href}')
      offset = offset +1
  return offset


def flattenToc(b:list,links:list[str]=[]):
  """Output all entries of a table of contents to the console."""
  for t in b:
    if isinstance (t,list) or isinstance(t,tuple): flattenToc(t,links)
    else: links.append(t.href)

  return links

def checkToC(toc:list,mapping:list[int]):
  if len(flattenToc(toc)) == len(mapping): return True
  print('The manual chapter map must have the same number of entries as the Table of Contents of the ebook.\n The current ToC Data has the following entries:')
  printToc(toc)
  print('\n Please adjust your list.')
  return False

def getTocLocations(toc:list,docs:list[EpubHtml],stripSplits:list[int],docStats:list[tuple[etree.ElementBase, list[tuple[etree.ElementBase, int, int]], dict[str, int]]]):
  links:list[str] = flattenToc(toc)
  locations:list[tuple[str,int]] = []
  for link in links:
    anchored = '#' in link
    [doc,id] = (link.split('#') if anchored else [link,None])
    index = next((idx for (idx,pubDoc) in enumerate(docs) if pubDoc.file_name == doc),None)
    if index is None: raise LookupError(f'Table of Contents contains link to nonexistent document "{doc}".')
    if id is None: locations.append((link,stripSplits[index]))
    else:
      [_,_,idLocations] = docStats[index]
      try:
        locations.append((link,stripSplits[index]+idLocations[id]))
      except:
        print(f'could not locate id {id} in document {doc}.')
  return locations
