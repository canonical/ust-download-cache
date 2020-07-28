# USTDownloadCache
<p align="center">
	<a href="https://github.com/canonical/ust-download-cache">
		<img alt="GitHub license" src="https://img.shields.io/github/license/canonical/ust-download-cache">
	</a>
	<img src="https://img.shields.io/github/v/tag/canonical/ust-download-cache" alt="GitHub tag (latest by date)">
	<img alt="GitHub last commit" src="https://img.shields.io/github/last-commit/canonical/ust-download-cache">
</p>

## About

The USTDownloadCache is used by the Ubuntu Security Team to improve the runtime
of other packages by caching certain JSON files.

## Using USTDownloadCache

### Example:

```python
import logging
from ust_download_cache import USTDownloadCache

logger = logging.getLogger("")
download_cache = USTDownloadCache(logger)

url = "URL_GOES_HERE"
data = download_cache.get_data_from_url(url)
metadata = download_cache.get_cache_metadata_from_url(url) # used by USTDownloadCache
```

### Extracting zipped files

USTDownloadCache has the ability to download, extract, and cache either bz2 or
gz archives. These files are extracted and stored uncompressed so that the data
can be accessed as quickly as possible.

### Metadata

The USTDownloadCache relies on metadata contained within the file it is
downloading/caching. The JSON must supply a "metadata" key, which provides a
timestamp (seconds since the Unix epoch) and time to live (ttl) in seconds. The
cached version of the file is considered to be expired when `timestamp + ttl >
now`

```json
{
    "metadata": {
        "timestamp": 1591887905,
        "ttl": 3600,
        "version": "1.0"
    },
    "data": {
        "name1": "value1",
        "name2": "value2"
    }
}
```

## Installation

### From Source
To install from source, you can clone this repository and install
USTDownloadCache:

```
$> git clone https://github.com/canonical/ust-download-cache
$> pip3 install --user ./ust-download-cache/
```

### As a dependency

As USTDownloadCache is not in PyPI at the moment, you must use the github
tarball in your setup.py:

```python
install_requires = [
        "ust-download-cache @ https://github.com/canonical/ust-download-cache/archive/v1.0.1.tar.gz",
]
```

## Development

### Installing precommit hooks
To install the precommit hooks, run

    pip3 install --user pre-commit
    ~/.local/bin/pre-commit install

### Running the test suite
You can run the automated test suite by running

```
$> python3 -m pytest
```

An HTML code coverage report will be generated at `./htmlcov`. You can view
this with any web browser (e.g. `firefox ./htmlcov/index.html`).
