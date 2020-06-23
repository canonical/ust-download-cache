import time

from ust_download_cache import CachedFile


def test_is_expired_true(monkeypatch):
    monkeypatch.setattr(time, "time", lambda: 1591880120.0)

    cf = CachedFile("file:///test", "/.ust_cache/1", 1591880020, 60)
    assert cf.is_expired


def test_is_expired_false(monkeypatch):
    monkeypatch.setattr(time, "time", lambda: 1591880079.0)

    cf = CachedFile("file:///test", "/.ust_cache/1", 1591880020, 60)
    assert not cf.is_expired


def test_from_dict():
    expected_url = "file:///test"
    expected_path = "/.ust_cache/uuuiiidddd-1-2-3"
    expected_timestamp = 1592880020
    expected_ttl = 3600

    src_dict = {
        "url": expected_url,
        "path": expected_path,
        "timestamp": expected_timestamp,
        "ttl": expected_ttl,
    }
    cf = CachedFile.from_dict(src_dict)

    assert cf.url == expected_url
    assert cf.path == expected_path
    assert cf.timestamp == expected_timestamp
    assert cf.ttl == expected_ttl
