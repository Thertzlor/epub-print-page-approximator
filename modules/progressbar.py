def printProgressBar(iteration:int, total:int, prefix = '', suffix = '', decimals = 1, length = 60, fill = '█', printEnd = "\r"):
  """https://stackoverflow.com/questions/3173320/"""
  percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
  filledLength = int(length * iteration // total)
  bar = fill * filledLength + '-' * (length - filledLength)
  print(f'\r{prefix} |{bar}| {percent}% {suffix}', end = printEnd)
  # Print New Line on Complete
  if iteration == total: 
    print()

def mapReport(a,b, t='Mapping page break'):
  """simple printout function for mapping progress"""
  printProgressBar(a,b,f'{t} {a} of {b}','Done',2)
  return True