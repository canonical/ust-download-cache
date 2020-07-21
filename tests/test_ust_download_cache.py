import bz2
import json
import logging
import os
import shutil
import uuid

import pytest
import requests

from ust_download_cache import (
    BZ2ExtractionError,
    CachedFile,
    DownloadError,
    FileCacheLoadError,
    USTDownloadCache,
)


class MockResponse:
    def __init__(self, content, status_code, url=None):
        self.content = str.encode(content)
        self.status_code = status_code

        if url is not None and url.startswith("file:///"):
            with open(url[7:], "rb") as f:
                self.content = f.read()

    def raise_for_status(self):
        if self.status_code != requests.codes.ok:
            raise requests.exceptions.HTTPError(self.status_code)


def load_file_cache(tmp_dir):
    with open(tmp_dir.join("file_cache.json")) as fc:
        file_cache = json.load(fc)

    return file_cache


def gen_uuid4():
    for x in range(99, 200):
        yield x


class MockUUID4:
    def __init__(self):
        self.x = 99

    def get(self):
        self.x += 1
        return self.x - 1


@pytest.fixture
def uuid4():
    return MockUUID4()


@pytest.fixture
def null_logger():
    logger = logging.getLogger("cvescan.null")
    if not logger.hasHandlers():
        logger.addHandler(logging.NullHandler())

    return logger


def test_set_cache_dir_constructor(null_logger, tmpdir):
    udc = USTDownloadCache(null_logger, cache_dir=tmpdir.join("my_ust_cache"))
    assert udc.cache_dir == tmpdir.join("my_ust_cache")


def test_set_cache_home(null_logger, tmpdir, monkeypatch):
    monkeypatch.setenv("HOME", str(tmpdir.join("HOME_TEST")))
    udc = USTDownloadCache(null_logger)
    assert udc.cache_dir == tmpdir.join("HOME_TEST").join(".ust_cache")


def test_set_cache_snap(null_logger, tmpdir, monkeypatch):
    monkeypatch.setenv("SNAP_USER_COMMON", str(tmpdir.join("SNAP_TEST")))
    udc = USTDownloadCache(null_logger)
    assert udc.cache_dir == tmpdir.join("SNAP_TEST").join(".ust_cache")


def test_create_cache_dir(null_logger, tmpdir, monkeypatch):
    USTDownloadCache(null_logger, tmpdir.join(".ust_cache"))
    assert os.path.isdir(tmpdir.join(".ust_cache"))


def test_create_cache_dir_file_exists(null_logger, tmpdir, monkeypatch):
    tmpdir.join(".ust_cache").write("")
    with pytest.raises(FileExistsError):
        USTDownloadCache(null_logger, tmpdir.join(".ust_cache"))


def test_download_creates_file_cache(null_logger, tmpdir, monkeypatch, uuid4):
    monkeypatch.setattr(uuid, "uuid4", uuid4.get)
    url = "file://%s" % os.path.abspath("./tests/assets/1.json")

    mr = MockResponse("", 200, url=url)
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: mr)

    udc = USTDownloadCache(null_logger, tmpdir)
    udc.get_data_from_url(url)
    assert os.path.exists(tmpdir.join("file_cache.json"))


def test_download_creates_file_cache_contents(null_logger, tmpdir, monkeypatch, uuid4):
    monkeypatch.setattr(uuid, "uuid4", uuid4.get)
    url = "file://%s" % os.path.abspath("./tests/assets/1.json")

    mr = MockResponse("", 200, url=url)
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: mr)

    udc = USTDownloadCache(null_logger, tmpdir)
    udc.get_data_from_url(url)
    with open(tmpdir.join("file_cache.json")) as f:
        cache_contents = json.load(f)

    expected_cache_contents = {
        url: {
            "url": url,
            "path": str(tmpdir.join("99")),
            "timestamp": 1591401600,
            "ttl": 60,
        }
    }
    assert cache_contents == expected_cache_contents


def test_download_creates_file_cache_contents_2(
    null_logger, tmpdir, monkeypatch, uuid4
):
    monkeypatch.setattr(uuid, "uuid4", uuid4.get)
    url1 = "file://%s" % os.path.abspath("./tests/assets/1.json")
    url2 = "file://%s" % os.path.abspath("./tests/assets/2.json.bz2")

    udc = USTDownloadCache(null_logger, tmpdir)

    mr = MockResponse("", 200, url=url1)
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: mr)
    udc.get_data_from_url(url1)

    mr = MockResponse("", 200, url=url2)
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: mr)
    udc.get_data_from_url(url2)
    with open(tmpdir.join("file_cache.json")) as f:
        cache_contents = json.load(f)

    expected_cache_contents = {
        url1: {
            "url": url1,
            "path": str(tmpdir.join("99")),
            "timestamp": 1591401600,
            "ttl": 60,
        },
        url2: {
            "url": url2,
            "path": str(tmpdir.join("100")),
            "timestamp": 1591402600,
            "ttl": 3600,
        },
    }
    assert cache_contents == expected_cache_contents


def test_download_cache_expired(null_logger, tmpdir, monkeypatch, uuid4):
    monkeypatch.setattr(uuid, "uuid4", uuid4.get)
    monkeypatch.setattr(CachedFile, "is_expired", True)
    url = "file://%s" % os.path.abspath("./tests/assets/1.json")

    udc = USTDownloadCache(null_logger, tmpdir)

    mr = MockResponse("", 200, url=url)
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: mr)
    udc.get_data_from_url(url)
    # Downloading a second time will cause the mock uuid to increment
    udc.get_data_from_url(url)
    with open(tmpdir.join("file_cache.json")) as f:
        cache_contents = json.load(f)

    expected_cache_contents = {
        url: {
            "url": url,
            "path": str(tmpdir.join("100")),
            "timestamp": 1591401600,
            "ttl": 60,
        }
    }
    assert cache_contents == expected_cache_contents


def test_download_cache_not_expired(null_logger, tmpdir, monkeypatch, uuid4):
    monkeypatch.setattr(uuid, "uuid4", uuid4.get)
    monkeypatch.setattr(CachedFile, "is_expired", False)
    url = "file://%s" % os.path.abspath("./tests/assets/1.json")

    udc = USTDownloadCache(null_logger, tmpdir)

    mr = MockResponse("", 200, url=url)
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: mr)

    mr = MockResponse("", 200, url=url)
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: mr)
    udc.get_data_from_url(url)
    # Downloading a second time will NOT cause the mock uuid to increment
    udc.get_data_from_url(url)
    with open(tmpdir.join("file_cache.json")) as f:
        cache_contents = json.load(f)

    expected_cache_contents = {
        url: {
            "url": url,
            "path": str(tmpdir.join("99")),
            "timestamp": 1591401600,
            "ttl": 60,
        }
    }
    assert cache_contents == expected_cache_contents


def write_test_file_cache(tmpdir):
    with open(tmpdir.join("file_cache.json"), "w") as f:
        f.write(
            """
{
    "file:///home/msalvatore/git/ust-download-cache/tests/assets/1.json": {
        "url": "file://%s",
        "path": "%s/98",
        "timestamp": 1591401600,
        "ttl": 60
    }
}
"""
            % (os.path.abspath("./tests/assets/1.json"), tmpdir)
        )


def test_download_cache_load_not_expired(null_logger, tmpdir, monkeypatch, uuid4):
    monkeypatch.setattr(uuid, "uuid4", uuid4.get)
    monkeypatch.setattr(CachedFile, "is_expired", False)
    url = "file://%s" % os.path.abspath("./tests/assets/1.json")

    write_test_file_cache(tmpdir)
    shutil.copy("./tests/assets/1.json", tmpdir.join("98"))

    udc = USTDownloadCache(null_logger, tmpdir)

    mr = MockResponse("", 200, url=url)
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: mr)
    udc.get_data_from_url(url)
    with open(tmpdir.join("file_cache.json")) as f:
        cache_contents = json.load(f)

    expected_cache_contents = {
        url: {
            "url": url,
            "path": str(tmpdir.join("98")),
            "timestamp": 1591401600,
            "ttl": 60,
        }
    }
    assert cache_contents == expected_cache_contents


def test_download_cache_load_expired(null_logger, tmpdir, monkeypatch, uuid4):
    monkeypatch.setattr(uuid, "uuid4", uuid4.get)
    monkeypatch.setattr(CachedFile, "is_expired", True)
    url = "file://%s" % os.path.abspath("./tests/assets/1.json")

    write_test_file_cache(tmpdir)
    shutil.copy("./tests/assets/1.json", tmpdir.join("98"))

    udc = USTDownloadCache(null_logger, tmpdir)

    mr = MockResponse("", 200, url=url)
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: mr)
    udc.get_data_from_url(url)
    with open(tmpdir.join("file_cache.json")) as f:
        cache_contents = json.load(f)

    expected_cache_contents = {
        url: {
            "url": url,
            "path": str(tmpdir.join("99")),
            "timestamp": 1591401600,
            "ttl": 60,
        }
    }
    assert cache_contents == expected_cache_contents


def test_download_missing_metadata(null_logger, tmpdir, monkeypatch, uuid4):
    monkeypatch.setattr(uuid, "uuid4", uuid4.get)
    url = "file://%s" % os.path.abspath("./tests/assets/3.json")

    with pytest.raises(Exception):
        udc = USTDownloadCache(null_logger, tmpdir)

        mr = MockResponse("", 200, url=url)
        monkeypatch.setattr(requests, "get", lambda *args, **kwargs: mr)
        udc.get_data_from_url(url)

    assert not os.path.exists(tmpdir.join("99"))


def raise_test_exception():
    raise Exception("Test")


def test_download_error(null_logger, tmpdir, monkeypatch, uuid4):
    monkeypatch.setattr(uuid, "uuid4", uuid4.get)
    monkeypatch.setattr(requests, "get", raise_test_exception)
    url = "file://%s" % os.path.abspath("./tests/assets/1.json")

    with pytest.raises(DownloadError):
        udc = USTDownloadCache(null_logger, tmpdir)

        monkeypatch.setattr(
            requests, "get", lambda *args, **kwargs: raise_test_exception
        )
        udc.get_data_from_url(url)


def test_download_404(null_logger, tmpdir, monkeypatch, uuid4):
    monkeypatch.setattr(uuid, "uuid4", uuid4.get)

    mr = MockResponse("", 404)
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: mr)

    url = "file://%s" % os.path.abspath("./tests/assets/1.json")

    with pytest.raises(DownloadError) as de:
        udc = USTDownloadCache(null_logger, tmpdir)
        udc.get_data_from_url(url)

    assert "404" in str(de.value)


def test_bz2_error(null_logger, tmpdir, monkeypatch, uuid4):
    monkeypatch.setattr(uuid, "uuid4", uuid4.get)
    monkeypatch.setattr(bz2, "open", raise_test_exception)
    url = "file://%s" % os.path.abspath("./tests/assets/2.json.bz2")

    with pytest.raises(BZ2ExtractionError):
        udc = USTDownloadCache(null_logger, tmpdir)

        mr = MockResponse("", 200, url=url)
        monkeypatch.setattr(requests, "get", lambda *args, **kwargs: mr)
        udc.get_data_from_url(url)


def test_download_cache_load_failed_key_error(null_logger, tmpdir, monkeypatch, uuid4):
    write_test_file_cache(tmpdir)
    shutil.copy(
        "./tests/assets/malformed_file_cache.json", tmpdir.join("file_cache.json")
    )

    with pytest.raises(FileCacheLoadError) as fcle:
        USTDownloadCache(null_logger, tmpdir)

    assert "missing key 'url'" in str(fcle.value)


def test_download_cache_load_failed_json_error(null_logger, tmpdir, monkeypatch, uuid4):
    write_test_file_cache(tmpdir)
    shutil.copy(
        "./tests/assets/malformed_json_file_cache.json", tmpdir.join("file_cache.json")
    )

    with pytest.raises(FileCacheLoadError) as fcle:
        USTDownloadCache(null_logger, tmpdir)

    assert "File contains malformed JSON" in str(fcle.value)


def test_download_cache_load_permission_denied_error(
    null_logger, tmpdir, monkeypatch, uuid4
):
    write_test_file_cache(tmpdir)
    cache_file = tmpdir.join("file_cache.json")
    shutil.copy("./tests/assets/malformed_json_file_cache.json", cache_file)
    os.chmod(cache_file, 0o000)

    with pytest.raises(FileCacheLoadError) as fcle:
        USTDownloadCache(null_logger, tmpdir)

    assert "Permission denied" in str(fcle.value)


def test_download_get_data(null_logger, tmpdir, monkeypatch, uuid4):
    monkeypatch.setattr(uuid, "uuid4", uuid4.get)
    url = "file://%s" % os.path.abspath("./tests/assets/1.json")

    mr = MockResponse("", 200, url=url)
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: mr)

    udc = USTDownloadCache(null_logger, tmpdir)
    data = udc.get_data_from_url(url)
    assert data["a"] == 1
    assert data["b"] == 2
    assert data["c"] == 3


def test_download_get_cache_metadata(null_logger, tmpdir, monkeypatch, uuid4):
    monkeypatch.setattr(uuid, "uuid4", uuid4.get)
    url = "file://%s" % os.path.abspath("./tests/assets/1.json")

    mr = MockResponse("", 200, url=url)
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: mr)

    udc = USTDownloadCache(null_logger, tmpdir)
    metadata = udc.get_cache_metadata_from_url(url)
    assert metadata["version"] == "1.0"
    assert metadata["timestamp"] == 1591401600
    assert metadata["ttl"] == 60
