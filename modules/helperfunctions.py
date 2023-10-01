from re import search

num_map = ((1000, 'M'), (900, 'CM'), (500, 'D'), (400, 'CD'), (100, 'C'), (90, 'XC'),(50, 'L'), (40, 'XL'), (10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I'))

def intToRoman(num:int):
  """Convert an integer to a roman numeral"""
  roman = ''
  while num > 0:
    for i, r in num_map:
      while num >= i:
        roman += r
        num -= i
  return roman.lower()

roman = {'i':1,'v':5,'x':10,'l':50,'c':100,'d':500,'m':1000}
def romanToInt(s: str) -> int:
  s = s.lower()
  summ= 0
  for i in range(len(s)-1,-1,-1):
    num = roman[s[i]]
    if 3*num < summ: summ = summ-num
    else: summ = summ+num
  return summ


def splitStr(s:str,n:int): return[s[i:i+n] for i in range(0, len(s), n)]

def parseSelectors(selector:str)->tuple[str|None,str|None,str|None,str|None]:
  parseMatch = search(r"^([A-z]+)?(?:\.(.+?))?(?:\[([^\]]+)\])?(?:#(.+))?$",selector)
  if not parseMatch or len(parseMatch[0]) == 0: raise ValueError('invalid selector')
  return tuple(parseMatch[x] for x in [1,2,3,4])

def matchIdSelector(idSelector:str,id:str|None):
  if id is None:return False
  split = idSelector.split('*')
  if len(split) == 1: return idSelector == id
  if not ((id.startswith(split[0]) and id.endswith(split[-1]))): return False
  lastMatch = 0
  for s in split:
    try: lastMatch = id[lastMatch:].index(s)
    except ValueError: return False
  return True

def toInt(str:str|None):
  if not str: return str
  return str if search(r'^\d+$',str) is None else int(str)

def romanize(num:int,roman:int,offset:int):
  return intToRoman(num+offset) if (roman or 0) > num else (num-(roman or 0)+offset)