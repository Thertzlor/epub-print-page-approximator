# Print Page Approximator for EPUB and EPUB3
One of the biggest advantages of Ebooks is the freedom that dynamically reflowing text grants the reader.  
However, having constantly shifting page numbers whenever you resize the text or change the font is often annyoing. Static print pages, even if they are technically no longer applicable, still have the advantage of being consistent.  
This is why both EPUB2 and EPUB3 standards support so called "print page" references, so that even when reading a book digitally you know which "actual" page you are on.  

However, with the exceptions of some very high end digital releases, most ebooks don't implement this feature (most ebook reader apps also do not support it, but that's their loss, [KOreader](https://github.com/koreader/koreader), is a great option that does). So you are stuck with dynamic pages unless you own the print version and painstakingly insert hundreds page breaks by hand in an EPUB editor.

This script offers a quick and easy, if not super accurate alternative and all you need is the ebook and the number of pages you know the book has.

## Usage

```powershell
py .\pageApproximator.py .\example_book.epub 150
```
This will produce a copy of `example_book.epub` paginated with 150 pages in the current directory under the name of `example_book_paginated.epub`.

## Command-line Arguments
### positional:
* **filepath**: Path to the EPUB file you wish to paginate.
* **pages**: The number of pages you want to add to the book.
### options:
* **-h, --help**: show help message and exit.
* **-s , --suffix**: Suffix for the newly generated EPUP file. Defaults to `_paginated`.
* **-n , --name**: A new name for the newly generated EPUB file. Overrides the `--suffix` argument.
* **-o , --outpath**: Save path for the output file. Does not include file name.
### flags
* **--noNcx**: Do not insert a pageList Element into the EPUB2 ToC NCX file.
* **--noNav**: Do not insert a page-list nav element into the EPUB3 navigation file.

## How?
The script will generate the pagination as follows:
1. Extract all text from the EPUB HTML.
2. Divide the text equally based on the number of pages provided.
3. Use pattern matching to map the page break locations to their corresponding locations in the HTML files.
4. Insert invisible page-break span elements at those locations.
5. Insert the reference list of pages into the navigation file of EPUB3 books or the table of contents NCX file of EPUB2 books (or both if a EPUB3 book contains)
6. Save the paginated ebook.

Suffice to say that since everything is indeed only an *approximation*, so expect the produced numbers to be a few pages off compared to the print edition.


## Caveats
As a general rule, if you are processing books predominantly written in non-Latin based alphabets, especially with writing systems featuring different reading directions, non-space word boundaries or generally very different characters such as, Japanese, Arabic, Chinese or Braille I can't guarantee any sane results.

There are also a few other cases that can throw off the page count, or produce other unintended effects.  
One such case are books in which the character density per page varies a lot.

For example, since the first part of Pale Fire is a poem with short lines, there are a lot less characters per page in this part compared to the more dense rest of the book. Since the page approximation works by dividing the number of characters in the book by the given number of pages you'll end up with a value that is biased towards the second part, so the general page divisions will be very much out of synch with the print version.  
But of course, if you have a whole book of *just* poems the average will work out again.

Heavily illustrated books are also going to produce less reliable results since images are not taken into account when calculating the pages.

## Roadmap
* More general testing of ebook compatibility.
* Perhaps an alternative line/paragraph based page enumeration mode.
* Maybe supporting playOrder for EPUB2