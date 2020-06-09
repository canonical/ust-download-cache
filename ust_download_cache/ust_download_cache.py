import bz2
import json
import os
import time
import uuid
from pathlib import Path

import pycurl


class CachedFile:
    def __init__(self, url, path, timestamp, ttl):
        self.url = url
        self.path = path
        self.timestamp = timestamp
        self.ttl = ttl

    @property
    def is_expired(self):
        now = int(time.time())
        return (now - self.timestamp) > self.ttl


class CacheJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, CachedFile):
            return o.__dict__

        return o


class USTDownloadCache:
    def __init__(self):
        self.cache_dir = self._get_cache_dir()
        self.cache_metadata_file = os.path.join(self.cache_dir, "file_cache.json")
        self._try_create_cache_dir()

        self._load_file_cache()

    def save_cache(self):
        if self.cache_metadata_file is None:
            return

        with open(self.cache_metadata_file, "w") as cmf:
            json.dump(self.file_cache, cmf, cls=CacheJSONEncoder, indent=4)

    def _get_cache_dir(self):
        cache_dir = ".ust_cache"

        if "SNAP_USER_COMMON" in os.environ:
            cache_dir = os.path.join(os.environ["SNAP_USER_COMMON"], cache_dir)
        else:
            cache_dir = os.path.join(str(Path.home()), cache_dir)

        return cache_dir

    def _try_create_cache_dir(self):
        if os.path.exists(self.cache_dir):
            if not os.path.isdir(self.cache_dir):
                raise Exception("%s exists, but is not a directory." % self.cache_dir)

            return

        os.mkdir(self.cache_dir)

    def _load_file_cache(self):
        self.file_cache = {}

        if os.path.exists(self.cache_metadata_file):
            with open(self.cache_metadata_file) as cmf:
                cache_contents = json.load(cmf)
                for url, cached_file in cache_contents.items():
                    self.file_cache[url] = CachedFile(
                        url,
                        cached_file["path"],
                        cached_file["timestamp"],
                        cached_file["ttl"],
                    )

    def get_cached_file_path(self, url):
        if url in self.file_cache.keys():
            print("File is cached")
            cached_file = self.file_cache[url]
            if not cached_file.is_expired:
                print("cached file not expired")
                return cached_file.path
            else:
                print("cache is expired")
                self._remove_expired_file(cached_file)

        file_id = str(uuid.uuid4())
        downloaded_file_path = os.path.join(self.cache_dir, file_id)
        USTDownloadCache._download(url, downloaded_file_path)
        metadata = USTDownloadCache._get_file_metadata(downloaded_file_path)

        self.file_cache[url] = CachedFile(
            url, downloaded_file_path, metadata["timestamp"], metadata["ttl"]
        )

    def _remove_expired_file(self, cached_file):
        os.remove(cached_file.path)
        del self.file_cache[cached_file.url]

    @staticmethod
    def _get_file_metadata(path):
        if USTDownloadCache._is_bz2(path):
            with bz2.open(path, "rb") as f:
                file_contents = f.read()
        else:
            with open(path) as f:
                file_contents = f.read()

        json_data = json.loads(file_contents)

        return json_data["metadata"]

    @staticmethod
    def _is_bz2(path):
        with open(path, "rb") as f:
            magic_number = f.read(2)
            return magic_number == b"BZ"

    @staticmethod
    def _download(download_url, filename):
        try:
            print("Downloading %s to %s" % (download_url, filename))
            with open(filename, "wb") as target_file:
                curl = pycurl.Curl()
                curl.setopt(pycurl.URL, download_url)
                curl.setopt(pycurl.WRITEDATA, target_file)
                curl.perform()
                curl.close()
        except Exception as ex:
            # raise DownloadError("Downloading %s failed: %s" % (download_url, ex))
            raise Exception("Downloading %s failed: %s" % (download_url, ex))


udc = USTDownloadCache()
print(udc.get_cached_file_path("file:///home/msalvatore/compost/test.json.bz2"))
udc.save_cache()
