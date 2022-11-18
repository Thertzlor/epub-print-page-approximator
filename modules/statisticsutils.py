from modules.helperfunctions import splitStr


def lineSplitter(txt:str,lineLength:str|int):
  lines = txt.splitlines(keepends=True)
  if isinstance(lineLength,int):
    # splitting up all lines above the maximum length
    splitLines = [splitStr(x,lineLength) for x in lines]
    # flattening our list of split up strings back into a regular list of strings
    return [item for sublist in splitLines for item in sublist]
  else: return lines


def textStats(txt:str,lineLength:str|int):
  lineCount = lineSplitter(txt,lineLength)
  return (len(txt),len(lineCount),len(txt.split()))
