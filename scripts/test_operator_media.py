"""Operator-supplied media resolves from disk, not from the network.

WHAT THIS GUARDS
----------------
THURIS is greenfield: its source page is operator-authored and its imagery is
an operator-supplied pack, not a crawl. The resolver only binds an image whose
host a crawl vouched for and fetches it over HTTP, so `<img src="/media/x.webp">`
(absolutised by the harvest onto the source host) was unresolvable and every
image slot stayed empty.

`operator_media()` turns `intake/<tenant>/assets/media/` into (a) asset entries
on the source host, so those URLs are recognised, and (b) a download function
that COPIES those exact URLs from disk and defers everything else to the normal
downloader. Only files that are really in the directory map; a path that
escapes it never does.

Run: `python3 -m pytest scripts/test_operator_media.py -v` from web-builder/.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.asset_resolver import operator_media  # noqa: E402

WEBP = b"RIFF\x24\x00\x00\x00WEBPVP8 " + b"\x00" * 24


def _media(tmp_path):
    d = tmp_path / "media"
    d.mkdir()
    (d / "07_frankincense.webp").write_bytes(WEBP)
    (d / "notes.md").write_text("not an image")
    return d


def test_files_become_entries_on_the_source_host(tmp_path):
    entries, _ = operator_media(_media(tmp_path), "thuris.myshopify.com")
    assert [e["src"] for e in entries] == ["https://thuris.myshopify.com/media/07_frankincense.webp"]


def test_known_urls_are_copied_from_disk_and_others_defer(tmp_path):
    calls = []
    _, fetch = operator_media(_media(tmp_path), "thuris.myshopify.com",
                              fallback=lambda url, dest: calls.append(url) or 0)
    dest = tmp_path / "out" / "a.webp"
    n = fetch("https://thuris.myshopify.com/media/07_frankincense.webp", dest)
    assert n == len(WEBP) and dest.read_bytes() == WEBP
    assert calls == []
    assert fetch("https://elsewhere.example/x.webp", tmp_path / "b.webp") == 0
    assert calls == ["https://elsewhere.example/x.webp"]


def test_a_path_outside_the_media_dir_never_maps(tmp_path):
    (tmp_path / "secret.webp").write_bytes(WEBP)
    calls = []
    _, fetch = operator_media(_media(tmp_path), "thuris.myshopify.com",
                              fallback=lambda url, dest: calls.append(url) or 0)
    assert fetch("https://thuris.myshopify.com/media/../secret.webp", tmp_path / "c.webp") == 0
    assert calls  # deferred, not copied


def test_no_media_dir_is_empty_not_an_error(tmp_path):
    entries, fetch = operator_media(tmp_path / "absent", "thuris.myshopify.com",
                                    fallback=lambda url, dest: 0)
    assert entries == []
