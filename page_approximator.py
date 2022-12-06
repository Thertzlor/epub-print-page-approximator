from argparse import ArgumentParser

from modules.helperfunctions import toInt
from modules.pageprocessor import processEPUB

parser = ArgumentParser(description='Print Page Approximator for EPUB and EPUB3',prog='Print Page Approximator')
parser.add_argument('filepath',type=str, help='Path to the EPUB file you wish to paginate')
parser.add_argument('pages', help='The number of pages you want to add to the book')
parser.add_argument('-p','--pagingmode',type=str, help='Define how to divide pages. "chars" uses a fixed number of characters per page, "lines" a fixed number of lines/paragraphs. Enter a number to use the "lines" mode with a maximum number of characters per line. Default is "chars"', metavar='',default='chars')
parser.add_argument('-t','--tocpages', nargs='+', help="A list of page numbers to be mapped to the ebook's chapter markers",metavar='', default=())
parser.add_argument('-r','--romanfrontmatter', nargs='?', help="The number of pages with Roman numerals in the front matter. Can be in the form of a Roman numeral.",metavar='')
parser.add_argument('-b','--breakmode', choices=['next','prev','split'], type=str, help="Behavior if a pagebreak is generated in the middle of a word; 'next' goes to the next whitespace, 'prev' to the previous, 'split' will keep the break inside the word",metavar='',default="next")
parser.add_argument('-l','--nonlinear', choices=['append','prepend','ignore'], type=str, help="How to handle documents that are desginated as 'nonlinear' in the book's spine.",metavar='',default="append")
parser.add_argument('-u','--unlisted', choices=['append','prepend','ignore'], type=str, help="How to handle documents not listed in the book's spine",metavar='',default="ignore")
parser.add_argument('-s','--suffix', type=str, help="Suffix for the newly generated EPUP file. Defaults to '_paginated'",metavar='',default='_paginated',nargs='?',const='')
parser.add_argument('-n','--name', type=str, help="A new name for the newly generated EPUB file. Overrides the --suffix argument",metavar='')
parser.add_argument('-o','--outpath', type=str, help="Save path for the output file. Does not include file name",metavar='')
parser.add_argument('--noncx',action='store_true', help="[flag] Do not insert a pageList Element into the EPUB2 ToC NCX file")
parser.add_argument('--nonav', action='store_true', help="[flag] Do not insert a page-list nav element into the EPUB3 navigation file")
parser.add_argument('--page-map', action='store_true', help="[flag] Add a page-map.xml for ADE based readers.")
parser.add_argument('--autopage', action='store_true', help="[flag] Use the value of the 'pages' argument as the definition of a single page according to the current pagingmode and generate an automatic page count")
parser.add_argument('--suggest', action='store_true', help="[flag] Only display automatically generated page count without applying it to the file")

args = parser.parse_args()
if args.pages == 0 or args.pages == 1: raise SystemExit("No point in paginating if you don't actually want more than one page.")
romans = toInt(args.romanfrontmatter)
if romans == 'auto' and len(args.tocpages) == 0: raise SystemExit('Automatic roman numerals only work if a ToC map is provided.')
pageMode = toInt(args.pagingmode)
if not isinstance(pageMode,int) and pageMode not in ['lines','chars','words']: raise SystemExit("-p/--pagingMode argument has to be 'chars', 'lines', 'words' or a number.")
processEPUB(args.filepath,args.pages,args.suffix,args.outpath,args.name,args.nonav,args.noncx,args.breakmode,pageMode,tuple(int(x) if x.isnumeric() else x for x in args.tocpages),args.page_map,args.suggest,args.autopage,romans,args.nonlinear,args.unlisted)