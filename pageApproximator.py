from argparse import ArgumentParser

from modules.pageProcessor import processEPUB

parser = ArgumentParser(description='Print Page Approximator for EPUB and EPUB3',prog='Print Page Approximator')
parser.add_argument('filepath',type=str, help='Path to the EPUB file you wish to paginate')
parser.add_argument('pages',type=int, help='The number of pages you want to add to the book')
parser.add_argument('-b','--breakMode', choices=['next','prev','split'], type=str, help="Behavior if a pagebreak is generated in the middle of a word; 'next' goes to the next whitespace, 'prev' to the previous, 'split' will keep the break inside the word.",metavar='',default="next")
parser.add_argument('-s','--suffix', type=str, help="Suffix for the newly generated EPUP file. Defaults to '_paginated'",metavar='',default='_paginated')
parser.add_argument('-n','--name', type=str, help="A new name for the newly generated EPUB file. Overrides the --suffix argument",metavar='')
parser.add_argument('-o','--outpath', type=str, help="Save path for the output file. Does not include file name",metavar='')
parser.add_argument('--noNcx',action='store_true', help="[flag] Do not insert a pageList Element into the EPUB2 ToC NCX file")
parser.add_argument('--noNav', action='store_true', help="[flag] Do not insert a page-list nav element into the EPUB3 navigation file")

args = parser.parse_args()

if args.pages == 0 or args.pages == 1: raise SystemExit("No point in paginating if you don't actually want more than one page.")

processEPUB(args.filepath,args.pages,args.suffix,args.outpath,args.name,args.noNav,args.noNcx,args.breakMode)