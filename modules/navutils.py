from ebooklib import ITEM_DOCUMENT, ITEM_NAVIGATION
from ebooklib.epub import EpubBook, EpubHtml, EpubNav, etree

from modules.helperfunctions import romanize
from modules.nodeutils import addLinksToNav, addLinksToNcx


def prepareNavigations(pub:EpubBook):
  """Extract the Navigation files from the EPUB"""
  ncxNav:EpubHtml = next((x for x in pub.get_items_of_type(ITEM_NAVIGATION)),None)
  epub3Nav:EpubHtml = next((x for x in pub.get_items_of_type(ITEM_DOCUMENT) if isinstance(x,EpubNav)),None)
  # a valid EPUB will have at least one type of navigation.
  if ncxNav is None and epub3Nav is None: raise LookupError('No navigation files found in EPUB, file probably is not valid.')
  return (epub3Nav,ncxNav)


def processNavigations(epub3Nav:EpubNav,ncxNav:EpubHtml,pgLinks:list[str],repDict:dict,noNav:bool, noNcX:bool,pageOffset=1,roman=0,numList:list[int|str] = []):
  """Adding the link list to any available navigation files."""
  if epub3Nav and not noNav:
    if addLinksToNav(epub3Nav,pgLinks,repDict,pageOffset,roman,numList) == False: return print('Pagination Cancelled') or False
  if ncxNav and not noNcX:
     if addLinksToNcx(ncxNav,pgLinks,repDict,pageOffset,roman,numList) == False :return print('Pagination Cancelled') or False
  return True


def makePgMap(linkList:list[str],pageOffset = 1,roman:int=0,numList:list[int|str]=[]):
  pgMap:etree.ElementBase = etree.fromstring('<?xml version="1.0" ?><page-map xmlns="http://www.idpf.org/2007/opf"></page-map>')
  def tag(name:str,attributes:dict=None)->etree.ElementBase: return pgMap.makeelement(name,attributes)
  def makeTarget(number:int,offset=0,replace=None):
    "Generates a pageTargets element containing a content tag with a link to the specified page number"
    target = tag('page',{'id':f'pageNav_{number}', 'href':linkList[number], 'name':str(romanize(replace or number,roman,offset))})
    return target
  for i in range(len(linkList)): pgMap.append(makeTarget(i,pageOffset if i >= len(numList) else 0,None if i >= len(numList) else numList[i]))
  return etree.tostring(pgMap).decode('utf-8')