# Change Log

All notable changes to the EPUP Page Approximator will be documented here.

## [1.1.8]
- yes
- mp
- Fixed some bugs involving HTML decoding and zip file handling.
- Guides moved to the new Wiki

## [1.1.7]
- The order in which the HTML documents are parsed is now defined by the order they are listed in the spine instead of their order in the content.opf.
- There are two new options for dealing with special cases pertaining to the book spine. `--nonlinear\-l` for documents with the `linear='no'` setting and `--unlisted\-u` for documents not listed in the spine.
- More bugfixes with path handling.

## [1.1.6]
- added new `--romanfrontmatter\-f` option to specif if and how many pages of front matter the book contains, which will be paginated in Roman numerals.
- The `--tocpages` option now also supports roman numerals for defining the page number of sections before page one.
- More bugfixes and performance improvements.

## [1.1.5]
- Added new `--autopage` flag for generating a dynamic number of pages by using the value of the `pages` argument as size definition of a single page.
- Added new `--suggest` flag for use together with `--autopage`. This flag will display the dynamically generated page count without saving it to a file.
- Added a new "words" mode for the `--pagingmode` option.
- The `pages` argument accepts the string "bookstats", resulting in displaying the character-, line-  and word count of the current book.

## [1.1.4]
- Added new flag `--page-map` for generating a page-map.xml file for compatibility with Adobe Digital Editions based readers.

## [1.1.3]
- Introduced the `--tocpages\-t` option for matching page numbers to Table of Content markers.
- Implemented logic for starting a book at page 0 if the `--tocpages` list defines a 'first' page.
- A more pythonic naming scheme for files

## [1.1.2]
- Source code fully documented
- Enormous performance improvement.

## [1.1.1]
- Added a new `--pagingmode\-p` option to allow finer control over how pages are split up.
- Fixed edge cases where page breaks could be generated outside the `body` tag of the document.

## [1.1.0]
- Switched to a proper node manipulation based approach. Much slower compared to the previous regex method, but much more reliable and guarantees that page breaks can't end up in invalid locations.
- Added the `--breakmode\-b` option, to handle page breaks in the middle of words.
- Lots of general bugfixes.

## [1.0.0]
- Initial release.