def relativePath(pathA:str,pathB:str):
  """A function to adjust link paths in case the navigation and content documents are in the same path."""
  [splitA,splitB] = tuple(x.split('/') for x in (pathA,pathB))
  pathDiff=0
  # comparing each path section of our files.
  for [i,s] in enumerate(splitA):
    # If the path is the same we will remove it from the link
    if s == splitB[i]: pathDiff = pathDiff+1
    # here we found the first section which is not the same
    else: break
  # returning the pruned path.
  return '/'.join(splitB[pathDiff:])


def pathProcessor(oldPath:str,newPath:str=None,newName:str=None,suffix:str='_paginated'):
  """Function to generate an output path for the new EPUB based on user preferences"""
  pathSplit = oldPath.split("/")
  if(len(pathSplit) == 1):pathSplit = oldPath.split("\\")
  oldFileName = pathSplit.pop()
  # if there's a new name, the suffix isn't necessary.
  if newName is not None:suffix = ''
  finalName = newName or oldFileName
  # the epub extension may be omitted, but in case it isn't we cut it off here.
  if finalName.lower().endswith('.epub'): finalName = finalName[:-5]
  # putting the path back together
  return f'{newPath or "/".join(pathSplit)}{finalName}{suffix}.epub'


def pageIdPattern(num:int,prefix = 'pg_break_'):
  """Just a quick utility function to generate link IDs"""
  return f'{prefix}{num}'