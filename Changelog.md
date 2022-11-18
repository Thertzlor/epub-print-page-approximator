# Change Log

All notable changes to the EPUP Page Approximator will be documented here.

## [1.1.5]
- added new `--autopage` flag for generating a dynamic number of pages by using the value of the `pages` argument as size definition of a single page.
- added new `--suggest` flag for use together with `--autopage`. This flag will display the dynamically generated page count without saving it to a file.
- Added a new "words" mode for the `--pagingmode` option.
- The `pages` argument accepts the string "bookstats", resulting in displaying the character-, line-  and word count of the current book.

## [1.1.4]
- Added new flag `--page-map` for generating a page-map.xml file for compatibility with Adobe Digital Editions based readers.

## [1.1.3]
- Introduced the `tocpages` option for matching page numbers to Table of Content markers.
- Implemented logic for starting a book at page 0 if the `tocpages` list defines a 'first' page.
- A more pythonic naming scheme for files

## [1.1.2]
- Source code fully documented
- enormous performance improvement.

## [1.1.1]
- Added a new `pagingmode` option to allow finer control over how pages are split up.
- fixed edge cases where page breaks could be generated outside the `body` tag of the document.

## [1.1.0]
- Switched to a proper node manipulation based approach. Much slower compared to the previous regex method, but much more reliable and guarantees that page breaks can't end up in invalid locations.
- Added the `breakmode` option, to handle page breaks in the middle of words.
- Lots of general bugfixes.

## [1.0.0]
- Initial release.