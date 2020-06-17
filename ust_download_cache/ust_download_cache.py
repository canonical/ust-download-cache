import bz2
import json
import os
import uuid
from pathlib import Path

import pycurl

from ust_download_cache import (
    BZ2ExtractionError,
    CachedFile,
    DownloadError,
    FileCacheLoadError,
)


class CacheJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, CachedFile):
            return o.__dict__

        return o


class USTDownloadCache:
    def __init__(self, logger, cache_dir=None):
        self.logger = logger
        self.logger.info("initializing USTDownloadCache")

        self.cache_dir = cache_dir if cache_dir else self._get_cache_dir()
        self.cache_metadata_file = os.path.join(self.cache_dir, "file_cache.json")
        self._try_create_cache_dir()

        self._load_file_cache()

    def save_cache(self):
        self.logger.debug("Saving cache metadata to %s" % self.cache_metadata_file)
        with open(self.cache_metadata_file, "w") as cmf:
            json.dump(self.file_cache, cmf, cls=CacheJSONEncoder, indent=4)

    def _get_cache_dir(self):
        cache_dir = ".ust_cache"

        if "SNAP_USER_COMMON" in os.environ:
            self.logger.debug("Detected that the environment is a snap.")
            cache_dir = os.path.join(os.environ["SNAP_USER_COMMON"], cache_dir)
        else:
            cache_dir = os.path.join(os.environ["HOME"], cache_dir)

        self.logger.debug("Cached files will be saved to %s" % cache_dir)

        return cache_dir

    def _try_create_cache_dir(self):
        if os.path.exists(self.cache_dir):
            self.logger.debug("The cache dir (%s) exists" % self.cache_dir)
            if not os.path.isdir(self.cache_dir):
                raise FileExistsError(
                    "%s exists, but is not a directory." % self.cache_dir
                )

            return

        self.logger.debug(
            "The cache dir (%s) does not exist, creating now" % self.cache_dir
        )
        Path(self.cache_dir).mkdir(parents=True)

    def _load_file_cache(self):
        self.file_cache = {}

        if os.path.exists(self.cache_metadata_file):
            self.logger.debug(
                "Loading cache metadata file from %s" % self.cache_metadata_file
            )
            try:
                with open(self.cache_metadata_file) as cmf:
                    cache_contents = json.load(cmf)
                    for url, cached_file in cache_contents.items():
                        self.file_cache[url] = CachedFile.from_dict(cached_file)
            except KeyError as ke:
                error_msg = (
                    "Error loading the file cache from %s" % self.cache_metadata_file
                )
                raise FileCacheLoadError(
                    "%s: record for %s is missing key %s" % (error_msg, url, ke)
                )
            except json.decoder.JSONDecodeError as jde:
                error_msg = (
                    "Error loading the file cache from %s" % self.cache_metadata_file
                )
                raise FileCacheLoadError(
                    "%s: File contains malformed JSON: %s" % (error_msg, jde)
                )
            except Exception as ex:
                error_msg = (
                    "Error loading the file cache from %s" % self.cache_metadata_file
                )
                raise FileCacheLoadError("%s: %s" % (error_msg, ex))

    def get_from_url(self, url):
        path = self._get_cached_file_path(url)
        file_contents = self._read_cached_file(path)
        json_data = json.loads(file_contents)

        return json_data

    def _get_cached_file_path(self, url):
        if url in self.file_cache.keys():
            self.logger.debug("File for url %s is cached" % url)
            cached_file = self.file_cache[url]
            if not cached_file.is_expired:
                self.logger.debug("The cache file for %s has not expired" % url)
            else:
                self.logger.debug("The cached file for %s has expired" % url)
                self._remove_expired_file(cached_file)
                self._download_and_cache_file(url)
                self.save_cache()
        else:
            self._download_and_cache_file(url)
            self.save_cache()

        return self.file_cache[url].path

    def _remove_expired_file(self, cached_file):
        self.logger.debug(
            "Removing expired cached file %s downloaded from %s"
            % (cached_file.path, cached_file.url)
        )
        os.remove(cached_file.path)
        del self.file_cache[cached_file.url]

    def _download_and_cache_file(self, url):
        file_id = str(uuid.uuid4())
        downloaded_file_path = os.path.join(self.cache_dir, file_id)
        self._download(url, downloaded_file_path)

        if USTDownloadCache._is_bz2(downloaded_file_path):
            self._extract_bz2_file(downloaded_file_path)

        try:
            metadata = self._get_file_metadata(downloaded_file_path)
        except Exception as ex:
            if os.path.exists(downloaded_file_path):
                os.remove(downloaded_file_path)

            raise ex

        self.file_cache[url] = CachedFile(
            url, downloaded_file_path, metadata["timestamp"], metadata["ttl"]
        )

    def _download(self, download_url, filename):
        try:
            self.logger.debug("Downloading %s to %s" % (download_url, filename))
            with open(filename, "wb") as target_file:
                curl = pycurl.Curl()
                curl.setopt(pycurl.URL, download_url)
                curl.setopt(pycurl.WRITEDATA, target_file)
                curl.perform()
                curl.close()
        except Exception as ex:
            raise DownloadError("Downloading %s failed: %s" % (download_url, ex))

    def _extract_bz2_file(self, path):
        try:
            self.logger.debug("Reading bz2 file %s" % path)
            print("Reading bz2 file %s" % path)
            with bz2.open(path, "rb") as f:
                file_contents = f.read()

            self.logger.debug("Writing extracted bz2 file contents to %s" % path)
            with open(path, "wb") as f:
                f.write(file_contents)
        except Exception as ex:
            raise BZ2ExtractionError("Error extracting bz2 archive: %s" % ex)

    def _get_file_metadata(self, path):
        file_contents = self._read_cached_file(path)

        json_data = json.loads(file_contents)

        if "metadata" not in json_data:
            raise Exception("Error parsing metadata from file.")

        return json_data["metadata"]

    def _read_cached_file(self, path):
        with open(path) as f:
            file_contents = f.read()

        return file_contents

    @staticmethod
    def _is_bz2(path):
        with open(path, "rb") as f:
            magic_number = f.read(2)
            return magic_number == b"BZ"
