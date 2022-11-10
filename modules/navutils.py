from ebooklib import ITEM_DOCUMENT, ITEM_NAVIGATION
from ebooklib.epub import EpubHtml, EpubNav

from modules.nodeutils import addLinksToNcx


def prepareNavigations(pub):
  """Extract the Navigation files from the EPUB"""
  ncxNav:EpubHtml = next((x for x in pub.get_items_of_type(ITEM_NAVIGATION)),None)
  epub3Nav:EpubHtml = next((x for x in pub.get_items_of_type(ITEM_DOCUMENT) if isinstance(x,EpubNav)),None)
  # a valid EPUB will have at least one type of navigation.
  if ncxNav is None and epub3Nav is None: raise LookupError('No navigation files found in EPUB, file probably is not valid.')
  return (epub3Nav,ncxNav)


def processNavigations(epub3Nav:EpubNav,ncxNav:EpubHtml,pgLinks:list[str],repDict:dict,noNav:bool, noNcX:bool,pageOffset=1):
  """Adding the link list to any available navigation files."""
  if epub3Nav and not noNav: 
    if addLinksToNcx(epub3Nav,pgLinks,repDict,pageOffset) == False: return print('Pagination Cancelled') or False
  if ncxNav and not noNcX: 
     if addLinksToNcx(ncxNav,pgLinks,repDict,pageOffset) == False :return print('Pagination Cancelled') or False
  return True 