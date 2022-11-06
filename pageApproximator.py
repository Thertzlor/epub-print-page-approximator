from argparse import ArgumentParser

from modules.pageProcessor import processEPUB

parser = ArgumentParser(description='Print Page Approximator for EPUB and EPUB3',prog='Print Page Approximator')
parser.add_argument('filepath',type=str, help='Path to the EPUB file you wish to paginate')
parser.add_argument('pages',type=int, help='The number of pages you want to add to the book')
parser.add_argument('-s','--suffix', type=str, help="Suffix for the newly generated EPUP file. Defaults to '_paginated'",metavar='',default='_paginated')
parser.add_argument('-n','--name', type=str, help="A new name for the newly generated EPUB file. Overrides the --suffix argument",metavar='')
parser.add_argument('-o','--outpath', type=str, help="Save path for the output file. Does not include file name",metavar='')

args = parser.parse_args()

if args.pages == 0 or args.pages == 1: raise SystemExit("No point in paginating if you don't actually want more than one page.")

processEPUB(args.filepath,args.pages,args.suffix,args.outpath,args.name)