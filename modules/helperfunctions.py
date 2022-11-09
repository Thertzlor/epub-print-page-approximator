from ebooklib.epub import zipfile


def between (str,pos,around,sep='|'): 
  """split a string at a certain position, highlight the split with a separator and output a range of characters to either side.\n
  Used for debugging purposes"""
  return f'{str[pos-around:pos]}{sep}{str[pos:pos+around]}'


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
  

def mapReport(a,b, t='Mapping page'):
  """simple printout function for mapping progress"""
  printProgressBar(a,b,f'{t} {a} of {b}','Done',2)
  return True


def splitStr(s:str,n:int): return[s[i:i+n] for i in range(0, len(s), n)]


def between (str,pos,around,sep='|'): 
  """split a string at a certain position, highlight the split with a separator and output a range of characters to either side.\n
  Used for debugging purposes"""
  return f'{str[pos-around:pos]}{sep}{str[pos:pos+around]}'