# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2020-07-21
### Added
- get_data_from_url() method
- get_cache_metadata_from_url() method
### Changed
- the USTDownloadCache.get_from_url() method used to return a dictionary from
  which the user could chose the "data" or "metadata" key. This interface is
  sub-optimal and has been replaced instead by 2 methods that allow the user to
  request either the data or the cache metadata.
### Removed
- get_from_url() method

## [1.1.0] - 2020-06-29
### Changed
- Switched from pycurl to requests for downloading files.

## [1.0.1] - 2020-06-24
### Fixed
- Bug that caused the cache to become corrupt if a download was interrupted.

## [1.0.0] - 2020-06-23
### Added
- README.md
- CHANGELOG.md
- LICENSE
- setup.py, setup.cfg
- USTDownloadCache class for caching downloads of certain JSON files
- Unit test suite
