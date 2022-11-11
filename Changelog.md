# Change Log

All notable changes to the EPUP Page Approximator will be documented here.

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