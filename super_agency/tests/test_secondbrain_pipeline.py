"""Tests for tools.secondbrain_pipeline"""

import os
import sys

root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, root)
sys.path.insert(0, os.path.join(root, "tools"))

import pytest
from tools.secondbrain_pipeline import _video_id, _base_dir, list_ingested


class TestVideoId:
    def test_standard_url(self):
        assert _video_id(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_short_url(self):
        assert _video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_url_with_params(self):
        vid = _video_id("https://www.youtube.com/watch?v=abc123DEF_-&t=120")
        assert vid == "abc123DEF_-"

    def test_invalid_url(self):
        with pytest.raises(ValueError, match="Cannot extract video ID"):
            _video_id("https://example.com/notayt")


class TestBaseDir:
    def test_returns_path(self):
        p = _base_dir("dQw4w9WgXcQ")
        assert "dQw4w9WgXcQ" in str(p)
        assert "secondbrain" in str(p)


class TestListIngested:
    def test_empty_when_no_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "tools.secondbrain_pipeline.KNOWLEDGE_DIR", tmp_path /
            "nonexistent")
        assert list_ingested() == []

    def test_finds_ingested(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "tools.secondbrain_pipeline.KNOWLEDGE_DIR", tmp_path)
        vid_dir = tmp_path / "2025" / "06" / "testVidId1234"
        vid_dir.mkdir(parents=True)
        (vid_dir / "raw.txt").write_text("hello world transcript")
        items = list_ingested()
        assert len(items) >= 1
        assert items[0]["video_id"] == "testVidId1234"
