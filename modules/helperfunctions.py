from ebooklib.epub import etree, zipfile

from modules.nodeutils import addPageMapReferences


def between (str,pos,around,sep='|'): 
  """split a string at a certain position, highlight the split with a separator and output a range of characters to either side.\n
  Used for debugging purposes"""
  return f'{str[pos-around:pos]}{sep}{str[pos:pos+around]}'


def overrideZip(src:str,dest:str,repDict:dict={},pageMap:str=None):
  """Zip replacer from the internet because for some reason the write method of the ebook library breaks HTML"""
  with zipfile.ZipFile(src) as inZip, zipfile.ZipFile(dest, "w",compression=zipfile.ZIP_DEFLATED) as outZip:
    # Iterate the input files
    if pageMap:
      opfFile = next((x for x in inZip.infolist() if x.filename.endswith('.opf')),None)
      if not opfFile: raise LookupError('somehow your epub does not have an opf file.')
      opfContent = inZip.open(opfFile).read()
      mapReferences = addPageMapReferences(opfContent)
      if mapReferences is None: repDict['page-map.xml'] = pageMap
      else:
        repDict[opfFile.filename] = mapReferences.decode('utf-8')
        outZip.writestr('page-map.xml',pageMap)
      

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


def splitStr(s:str,n:int): return[s[i:i+n] for i in range(0, len(s), n)]


def between (str,pos,around,sep='|'): 
  """split a string at a certain position, highlight the split with a separator and output a range of characters to either side.\n
  Used for debugging purposes"""
  return f'{str[pos-around:pos]}{sep}{str[pos:pos+around]}'