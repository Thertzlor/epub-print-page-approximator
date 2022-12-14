![version](https://img.shields.io/badge/version-1.1.7-blue)
[![CodeFactor](https://www.codefactor.io/repository/github/thertzlor/epub-print-page-approximator/badge/main)](https://www.codefactor.io/repository/github/thertzlor/epub-print-page-approximator/overview/main)
![license](https://img.shields.io/github/license/Thertzlor/epub-print-page-approximator) 
# Print Page Approximator for EPUB and EPUB3
One of the biggest advantages of Ebooks is the freedom that dynamically reflowing text grants the reader.  
However, having constantly shifting page numbers whenever you resize the text or change the font is often annoying. Static print pages, even if they are technically no longer applicable, still have the advantage of being consistent.  
This is why both EPUB2 and EPUB3 standards support so called "print page" references, so that even when reading a book digitally you know which "actual" page you are on.  

However, with the exceptions of some very high end digital releases, most ebooks don't implement this feature (most ebook reader apps also do not support it, but that's their loss, [KOreader](https://github.com/koreader/koreader), is a great option that does). So you are stuck with dynamic pages unless you own the print version and painstakingly insert hundreds page breaks by hand in an EPUB editor.

This script offers a quick and easy, if not super accurate alternative and all you need is the ebook and the number of pages you know the book has.  
You can also generate a cust9om page count based on a specific number of characters, lines or words per page.

## Usage
```powershell
py .\page_approximator.py .\example_book.epub 150
```
This will produce a copy of `example_book.epub` paginated with 150 pages in the current directory under the name of `example_book_paginated.epub`.

You can also download the pre-built executable for 64bit Windows from the [Releases Section](https://github.com/Thertzlor/epub-print-page-approximator/releases).

### Dependencies
This script requires the `ebooklib` python library.

## Command-line Arguments
### positional:
* **filepath**: Path to the EPUB file you wish to paginate.
* **pages**: The number of print pages you want to insert into to the book. (You can also pass the word `"bookstats"` to print out the number of characters, lines and words in the book).
### options:
* **-p , --pagingmode**: Define how to divide pages. "chars" uses a fixed number of characters per page, "lines" a fixed number of lines/paragraphs, and "words" a fixed number of words. Enter a number to use the "lines" mode with a maximum number of characters per line. Default is "chars". See section [Paging Modes](#paging-modes) for details.
* **-t, --tocpages**: A list of page numbers to be mapped to the ebook's chapter markers. See section [ToC Pages](#toc-pages) for details.
* **-r, --romanfrontmatter**: The number of pages with Roman numerals in the front matter. Can be in the form of a Roman numeral or a normal integer see [Roman numerals section](#front-matter-with-roman-numbering) for details.
* **-b , --breakmode**: Behavior if a pagebreak is generated in the middle of a word; `next` will go to the next whitespace, `prev` to the previous, `split` will simply keep the break inside the word.
* **-s , --suffix**: Suffix for the newly generated EPUP file. Defaults to `"_paginated"`.
* **-n , --name**: A new name for the newly generated EPUB file. Overrides the `--suffix` argument.
* **-o , --outpath**: Save path for the output file. Does not include file name.
* **-l , --nonlinear** Choose how to handle documents that are desginated as 'nonlinear' in the book's spine. Valid values are `append`, `prepend` and `ignore`. The default value is `append`.
* **-u , --unlisted** Choose how to handle documents not listed in the book's spine. Valid values are `append`, `prepend` and `ignore`. The default value is `ignore`.
* **-h, --help**: show help message and exit.
### flags
* **--noncx**: Do not insert a pageList Element into the EPUB2 ToC NCX file.
* **--nonav**: Do not insert a page-list nav element into the EPUB3 navigation file.
* **--page-map**: Add a page-map.xml for ADE based readers. This is not part of the EPUB spec and will generate errors with EPUB checkers.
* **--autopage**: Use the value of the 'pages' argument as the definition of a single page according to the current pagingmode and generate an automatic page count. For details see section [Automatic Pagination](#automatic-pagination)
* **--suggest**: Only display automatically generated page count without applying it to the file. Only works if the `--autopage` flag is also set.

## How?
The script will generate the pagination as follows:
1. Extract the book text* from the EPUB HTML.
2. Divide the text equally based on the number of pages provided.
3. Use node manipulation to map the page break locations to their corresponding locations in the HTML files.
4. Insert invisible page-break span elements at those locations.
5. Insert the reference list of pages into the navigation file of EPUB3 books or the table of contents NCX file of EPUB2 books (or both if a EPUB3 book contains an NCX as a fallback).
6. Save the paginated ebook.

Suffice to say that since everything is indeed only an *approximation*, so expect the produced numbers to be a few pages off compared to the print edition.  

*Page Approximator defines the text of the book as the text within all HTML tags that can reasonably be assumed to be visible to the reader, documents sorted by the order they are listed in the book's spine.

## Advanced Pagination
In case the page approximations produced by the script's default settings are not accurate enough, Print Page Approximator includes a few more advanced options for modifying the output.

---
### Paging Modes
Using the `-p` or `--pagingmode` argument you can choose how the script will go about actually defining page breaks.

* **"chars"**: This is the default mode and also the simplest of all. All it does is divide the number of characters of the books text by the number of pages we want, arriving at a fixed character count per page. This generally works well, but is best used for dense books with very long paragraphs, think of the styles of Proust or Saramago as examples.
* **"lines"**: In this mode the script divides the text up by line breaks and then calculates a fixed number of lines per page. The more predefined line breaks a book contains the better this mode works, so books of poetry are a good fit, as are books with lots of terse dialogue.
* **"words"**: In this mode the text will be split into individual words [defined as any sequence of non-whitespace characters; The output of the Python str.split()] and then calculates the average number of words on a page based on the total number of words in the text.
* ***number***: The final and most advanced paging mode is activated by passing a number as the argument. It works by using the `lines` mode and applying the provided number as a maximum character count per line. Shorter lines are left as-is, longer lines are split up. This can give you very accurate results, especially if you use the line length of the print edition as a reference (It's still not perfect of course, unless the book is typeset in a monospace font).

---
### ToC Pages
Back in the days of paper many physical books had a table of contents which included page numbers because paper didn't support links. The `-t` or `--tocpages` argument lets us use this ancient knowledge to guarantee that our generated page numbers don't get too inaccurate.  
The only requirement is that our ebook has a functioning table of contents as well.
The argument accepts a list of page numbers, each corresponding to a chapter.

In this example we have a book with 100 pages and 5 chapters and we know that the chapters begin on page 5, 20, 50, 70 and 90 respectively:
```powershell
py .\page_approximator.py ".\book.epub" 100 --tocpages 5 20 50 70 90
```

Now that we can map those pages to specific parts of the book using the toc.ncx/nav.xhtml of the file the script only needs to interpolate page numbers in the ranges between those known pages, increasing the accuracy immensely.

It's required that the number of the `--tocpages` list matches the number of content markers in the ebook. If they do not match, the script will abort and show a message listing all entries in the table of contents for reference.  
Chapters can be skipped by putting a 0 in their position.  
Should we only want to map every second chapter we can modify our previous example to this:
```powershell
py .\page_approximator.py ".\book.epub" 100 --tocpages 5 0 50 0 90
```

If one of the entries in the `--tocpages` list specifies page 1, and the location of that file is not the absolute beginning of the book, the script will automatically add a "0th" page onto which all content before the actual first page will be pushed.  
According to "proper" publishing convention the front matter before page 1 should be numbered in Roman numerals, which is the subject of the next section.

---
### Front Matter with Roman numbering
The `--romanfrontmatter` option, shortened to `-r` lets us define a front section of the book paginated with Roman numerals before resetting the pagination for the main content.

In this example we keep things simple, using only the page count without a ToC map:
```powershell
py .\page_approximator.py ".\book.epub" 100 --romanfrontmatter 5
```
This tells the script that the first 5 pages are front matter. Note that in this mode the page number argument refers to the total number of pages in the book *including* front matter, so since the numbering restarts after the 5 Roman numerals we only have 95 normal pages.

To get back up to 100 normal pages we have to add the 5 pages to the total once more:
```powershell
py .\page_approximator.py ".\book.epub" 105 --romanfrontmatter 5 
```
This complication does not apply if we are using a ToC map, because in this case the script knows exactly where the first real page of the book starts and calculates the provided number of pages only within the "main text" of the book.

In the following example we assume a book that has a single section before the main content starts at page **1**. Using the `--romanfrontmatter` option we tell the script that this first section consists of 5 pages with roman numbering.
Note that is required to specify a location for the first page in the ToC map when this option is set.
```powershell
py .\page_approximator.py ".\book.epub" 100 --tocpages 0 1 5 20 50 70 90 --romanfrontmatter 5
```
Alternatively it's also possible to pass `--romanfrontmatter 0` which tells the script to decide for itself how many front matter pages to insert, based on the average page size of the main text.

Alternatively the ToC map itself can be used to indicate and further control pages with roman numerals:
```powershell
py .\page_approximator.py ".\book.epub" 100 --tocpages i iv 1 5 20 50 70 90
```
In this example it is not necessary to set the `--romanfrontmatter` option since we have the roman numbering already in the page map.  
In this book we have two sections before the first content page, defined with their roman numbers. How many front matter pages will be inserted between iv and 1 is again calculated via the average page size, although it is possible to pass the `--romanfrontmatter` option to indicate the total number of front matter pages explicitly. Like in the normal section of the page map it is also possible to "skip" sections by filling in a 0 in their spot.

---
### A Complete Demonstration
This section will showcase the full process of paginating a book as precisely as possible using all techniques previously discussed.  
As our example book we will use *The Sirens of Titan* by Kurt Vonnegut, (named `sirens.epub` to keep things concise) with the data about the print version taken from [Google Books]("https://books.google.com/books?id=YuLuAn3itnAC") (the first time this service has been useful to me).

Our first data point is the fact that the number of pages is listed at 336, so we start with the simplest approach:
```powershell
py .\page_approximator.py ".\sirens.epub" 336
```
The result looks good, but comparing it to the Table of Contents in the Google Books preview shows that while the total page count is the same, there's some increasing divergenge; The first few chapters are pretty close, chapter 3 should start on page 62, in our calculations it became 65. Chapter 4 which be 95 is already off by 5 at page 100. At the end of the book we're off by 10 pages, with the epilogue starting on page 308 and 318 respectively.

We can do better, so let's refine our approach. Looking again at the preview of the print edition, we see that the lines in the printed text are pretty short, only about 56 characters per line, so we factor this in using the lines+maximum paging mode:
```powershell
py .\page_approximator.py ".\sirens.epub" 336 --pagingmode 56
```
This helps... only a tiny bit because the text density is quite constant. But we're still off by around 1 page less on average compared to our previous result.

To get truly accurate, we'll have to use the table of contents directly, especially because at least some of the inaccuracy can be traced back to the print version not counting the pages before the start of the first chapter.

The twelve chapters listed in the print edition's Table of Content start on the following pages: `1 41 62 95 105 143 167 187 199 218 256 270 308`  
...But we need to modify this list before using it since the digital edition of the book includes five more content markers before the first chapter: "Praise", "Title Page", "Copyright Page", "Table of Contents" and "Epigraph".  
These need to be included in our page mapping but as far as our table of contents is concerned, the actual first page starts at the first chapter, so we represent that by having those first 5 entries in our page list set to **0**:

```powershell
py .\page_approximator.py ".\sirens.epub" 336 -p 56 -t 0 0 0 0 0 1 41 62 95 105 143 167 187 199 218 256 270 308
```
But to have the book paginated "properly" the section that is now page "0" should instead be paginated with Roman numerals. The table of contents does not tell us how many of those pages there are so, we set the `-r` option to **0** and let the script decide how many to generate:

```powershell
py .\page_approximator.py ".\sirens.epub" 336 -p 56 -t 0 0 0 0 0 1 41 62 95 105 143 167 187 199 218 256 270 308 -r 0
```

Now the final output is as good as it gets, with all chapters on the right pages, Roman numerals in the front matter and thanks to the number of sample points the pages in-between are accurate to within a few lines.

## Automatic Pagination
If rather then applying a predefined page count you want the script to estimated a page count based on custom parameters you can use the `--autopage` flag. This option changes the function of the primary `pages` argument from defining the final number of pages to setting the size of a single page.
As an example:
```powershell
py .\page_approximator.py .\example_book.epub 1500 --autopage
```
This command will not create a book with 1500 pages but rather but rather define that a *single* page has 1500 characters and the final number of pages are calculated based on that.  
Just as with the regular pagination function, the `--pagingmode` argument can be used to modify the behavior of the script but now in the context of how to interpret the single page definition:
```powershell
py .\page_approximator.py .\example_book.epub 30 --autopage --pagingmode lines
```
...Defines that a single page consists of 30 lines of text.
```powershell
py .\page_approximator.py .\example_book.epub 250 --autopage --pagingmode words
```
...Defines that a single page consists of 250 words.

The numeric `--pagingmode` argument for maximum line length also works in this mode.

### Technical Notes
The difference between this automatic pagination of and the similar methods used for *Adobe Digital Editions* page numbers or Kindle "Locations" is that the latter two calculate pages based on the full contents of the HTML files. *Print Page Approximator* omits all HTML tags and other markup, trying to consider only the *actually readable* text of each file.

## Caveats
As a general rule, if you are processing books predominantly written in non-Latin based alphabets, especially with writing systems featuring different reading directions, non-space word boundaries or generally very different characters such as, Japanese, Arabic, Chinese or Braille I can't guarantee any sane results.

There are also a few other cases that can throw off the page count, or produce other unintended effects.  
One such case (especially in the default `chars` mode) are books in which the character density per page varies a lot.

For example, since the first part of Pale Fire is a poem with short lines, there are a lot less characters per page in this part compared to the more dense rest of the book. When approximating by dividing the number of characters in the book by the given number of pages you'll end up with a value that is biased towards the second part, so the general page divisions will be very much out of synch with the print version (but of course, if you have a whole book of *just* poems the average will work out again). In such cases, tweaking the paging mode to `lines` or `lines + maximum` is recommended as laid out in the [Advanced Pagination section](#advanced-pagination).  

Heavily illustrated books are also going to produce less reliable results since images are not taken into account when calculating the pages.

## Roadmap
* More general testing of ebook compatibility.
* Maybe supporting playOrder for EPUB2.