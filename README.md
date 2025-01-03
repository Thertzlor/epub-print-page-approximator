![version](https://img.shields.io/badge/version-1.2.0-blue)
[![CodeFactor](https://www.codefactor.io/repository/github/thertzlor/epub-print-page-approximator/badge/main)](https://www.codefactor.io/repository/github/thertzlor/epub-print-page-approximator/overview/main)
![license](https://img.shields.io/github/license/Thertzlor/epub-print-page-approximator)
# Print Page Approximator for EPUB and EPUB3
One of the biggest advantages of Ebooks is the freedom that dynamically reflowing text grants the reader.
However, having constantly shifting page numbers whenever you resize the text or change the font is often annoying. Static print pages, even if they are technically no longer applicable, still have the advantage of being consistent.
This is why both EPUB2 and EPUB3 standards support so called "print page" references, so that even when reading a book digitally you know which "actual" page you are on.

However, with the exceptions of some very high end digital releases, most ebooks don't implement this feature (most ebook reader apps also do not support it, but that's their loss, [KOreader](https://github.com/koreader/koreader), is a great option that does). So you are stuck with dynamic pages unless you own the print version and painstakingly insert hundreds page breaks by hand in an EPUB editor.

This script offers a quick and easy, if not super accurate alternative and all you need is the ebook and the number of pages you know the book has.  
You can also generate a custom page count based on a specific number of characters, lines or words per page.

As development went on, the script grew to support even more advanced features such as automatically pgainating based on a user defined page size, roman numeral pages for front matter and building a page list based on page markers that were defined in a non-compliant manner.  
*Details about advanced functionality **[can be found in the repository's Wiki](https://github.com/Thertzlor/epub-print-page-approximator/wiki)***.

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
* **pages**: The number of print pages you want to insert into to the book. You can also pass the word `"bookstats"` to print out the number of characters, lines and words in the book, or put the script into Page List restoration mode by [passing a node selector](https://github.com/Thertzlor/epub-print-page-approximator/wiki/Page-Lists-from-Existing-Tags#selectors).
### options:
* **-p , --pagingmode**: Define how to divide pages. "chars" uses a fixed number of characters per page, "lines" a fixed number of lines/paragraphs, and "words" a fixed number of words. Enter a number to use the "lines" mode with a maximum number of characters per line. Default is "chars". See section [Paging Modes](#paging-modes) for details.
* **-t, --tocpages**: A list of page numbers to be mapped to the ebook's chapter markers. See section [ToC Pages](https://github.com/Thertzlor/epub-print-page-approximator/wiki/Advanced-Manual-Pagination#toc-pages) in the wiki for details.
* **-r, --romanfrontmatter**: The number of pages with Roman numerals in the front matter. Can be in the form of a Roman numeral or a normal integer see [Roman numerals section](https://github.com/Thertzlor/epub-print-page-approximator/wiki/Advanced-Manual-Pagination#front-matter-with-roman-numbering) in the wiki for details.
* **-b , --breakmode**: Behavior if a pagebreak is generated in the middle of a word; `next` will go to the next whitespace, `prev` to the previous, `split` will simply keep the break inside the word.
* **-a , --attribute** If you are restoring the page list based on a tag selection, this optionally specifies [the name of the attribute](https://github.com/Thertzlor/epub-print-page-approximator/wiki/Page-Lists-from-Existing-Tags#fetching-values-from-other-attributes) containing the number of the page.
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
* **--autopage**: Use the value of the 'pages' argument as the definition of a single page according to the current pagingmode and generate an automatic page count. For details see the wiki page for [Automatic Pagination](https://github.com/Thertzlor/epub-print-page-approximator/wiki/Automatic-Pagination)
* **--suggest**: Only display automatically generated page count without applying it to the file. Only works if the `--autopage` flag is also set.

## How?
By default the script will generate the pagination as follows:
1. Extract the book's text* from the EPUB HTML.
2. Divide the text equally based on the number of pages provided.
3. Use node manipulation to map the page break locations to their corresponding locations in the HTML files.
4. Insert invisible page-break span elements at those locations.
5. Insert the reference list of pages into the navigation file of EPUB3 books or the table of contents NCX file of EPUB2 books (or both if a EPUB3 book contains an NCX as a fallback).
6. Save the paginated ebook.

Suffice to say that since everything is indeed only an *approximation*, expect the resulting numbers to be a few pages off compared to the print edition.  

*Page Approximator defines the text of the book as the text within all HTML tags that can reasonably be assumed to be visible to the reader, documents sorted by the order they are listed in the book's spine.

## Advanced Pagination
In case the page approximations produced by the script's default settings are not accurate enough, Print Page Approximator includes a few more advanced options for modifying the output.

Using the `-p` or `--pagingmode` argument you can choose how the script will go about actually defining page breaks.

* **"chars"**: This is the default mode and also the simplest of all. All it does is divide the number of characters of the books text by the number of pages we want, arriving at a fixed character count per page. This generally works well, but is best used for dense books with very long paragraphs, think of the styles of Proust or Saramago as examples.
* **"lines"**: In this mode the script divides the text up by line breaks and then calculates a fixed number of lines per page. The more predefined line breaks a book contains the better this mode works, so books of poetry are a good fit, as are books with lots of terse dialogue.
* **"words"**: In this mode the text will be split into individual words [defined as any sequence of non-whitespace characters; The output of the Python str.split()] and then calculates the average number of words on a page based on the total number of words in the text.
* ***number***: The final and most advanced paging mode is activated by passing a number as the argument. It works by using the `lines` mode and applying the provided number as a maximum character count per line. Shorter lines are left as-is, longer lines are split up. This can give you very accurate results, especially if you use the line length of the print edition as a reference (It's still not perfect of course, unless the book is typeset in a monospace font).

For a detailed description on how to fine tune your page count, check out the [Advanced Manual Pagination Wiki page](https://github.com/Thertzlor/epub-print-page-approximator/wiki/Advanced-Manual-Pagination).  
The wiki also includes guides for [dealing with roman front matter numbering](https://github.com/Thertzlor/epub-print-page-approximator/wiki/Advanced-Manual-Pagination#front-matter-with-roman-numbering), [Automatic Pagination](https://github.com/Thertzlor/epub-print-page-approximator/wiki/Automatic-Pagination), as well as some further [technical notes](https://github.com/Thertzlor/epub-print-page-approximator/wiki/Technical-Notes)

## Caveats
As a general rule, if you are processing books predominantly written in non-Latin based alphabets, especially with writing systems featuring different reading directions, non-space word boundaries or generally very different characters such as, Japanese, Arabic, Chinese or Braille I can't guarantee any sane results.

There are also a few other cases that can throw off the page count, or produce other unintended effects.
One such case (especially in the default `chars` mode) are books in which the character density per page varies a lot.

For example, since the first part of Pale Fire is a poem with short lines, there are a lot less characters per page in this part compared to the more dense rest of the book. When approximating by dividing the number of characters in the book by the given number of pages you'll end up with a value that is biased towards the second part, so the general page divisions will be very much out of synch with the print version (but of course, if you have a whole book of *just* poems the average will work out again). In such cases, tweaking the paging mode to `lines` or `lines + maximum` is recommended as laid out in the [Advanced Pagination section](#advanced-pagination).

Heavily illustrated books are also going to produce less reliable results since images are not taken into account when calculating the pages.

## Roadmap
* More general testing of ebook compatibility.
* Maybe supporting playOrder for EPUB2.
