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
