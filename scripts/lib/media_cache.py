"""The generated-media cache: content-addressed, read by the build, written
only by the out-of-band commissioner.

    tenants/<tenant>/assets/generated/<job_hash>.<ext>

One file per distinct picture, named by the hash of the job that asked for it.
That single choice carries every property this needs:

- **A rebuild costs nothing.** The same declaration + the same compiled palette
  produce the same `job_hash`, so the file is already there.
- **A changed design invalidates exactly what changed.** Move the accent and
  the hash moves, because the picture should.
- **Five sections asking for one picture share one file.** `job_hash` excludes
  the demanding section's id (see `image_jobs.cache_key_json`), so the five
  identical HERO backdrops on this site are one entry and one charge.

**The build never writes here and never calls a provider.** A miss is a
reported gap — the slot stays empty and named — never a placeholder and never
a blocked build. An unfunded or offline run degrades to a site with fewer
pictures, which is a site, rather than to a hang.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

#: Extensions the cache may hold, in preference order. `resolve_cached` scans
#: rather than assuming `.png`, because the provider chooses the container and
#: the hash does not encode it.
CACHE_EXTENSIONS = ("png", "jpg", "jpeg", "webp", "avif")

_HASH_RE = re.compile(r"^[0-9a-f]{6,64}$")

#: Where a generated file is served from inside the built site. Deliberately
#: distinct from `/images/...` (extracted source imagery) so a glance at a
#: rendered page's network tab tells you which pictures this system commissioned
#: and which it fetched.
PUBLIC_PREFIX = "/images/generated"


def cache_root(web_builder_root: Path, tenant: str) -> Path:
    """`tenants/<tenant>/assets/generated/` under the web-builder root.

    Inside the repo rather than beside the build output, deliberately: the
    build output is disposable and re-created by `--clean`, and a cache that
    `--clean` deletes is a cache that re-bills on every run.
    """
    return Path(web_builder_root) / "tenants" / str(tenant) / "assets" / "generated"


def cache_path(cache_dir: Path, job_hash: str, ext: str = "png") -> Path:
    """The one legal filename for a given hash. No version suffix, no job id —
    two machines that computed the same hash must name the same file."""
    if not _HASH_RE.match(str(job_hash)):
        raise ValueError("not a job hash: %r" % (job_hash,))
    ext = str(ext).lstrip(".").lower()
    return Path(cache_dir) / ("%s.%s" % (job_hash, ext))


def resolve_cached(cache_dir: Path, job_hash: str):
    """The cached file for this hash, or None.

    None is a first-class answer, not an error: it is what an un-commissioned
    slot looks like, and the caller's job is to record it as an empty slot with
    a name. A zero-byte file counts as a miss — a truncated download from an
    interrupted commission must not be adopted as art.
    """
    cache_dir = Path(cache_dir)
    if not cache_dir.is_dir() or not _HASH_RE.match(str(job_hash)):
        return None
    for ext in CACHE_EXTENSIONS:
        p = cache_dir / ("%s.%s" % (job_hash, ext))
        if p.is_file() and p.stat().st_size > 0:
            return p
    return None


def publish_to_site(cached: Path, public_dir: Path) -> tuple:
    """Copy a cached file into the site's public tree; return (src, bytes).

    `src` is the site-absolute URL the .tsx will carry. Copying rather than
    symlinking because the deploy step tars/copies `site/public` and a symlink
    out of the repo would not survive it. Idempotent: same hash, same
    destination, and an identical existing file is left alone.
    """
    cached = Path(cached)
    dest_dir = Path(public_dir) / PUBLIC_PREFIX.strip("/")
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / cached.name
    if not dest.exists() or dest.stat().st_size != cached.stat().st_size:
        shutil.copyfile(cached, dest)
    return "%s/%s" % (PUBLIC_PREFIX, cached.name), dest.stat().st_size


# ── Placing a generated file into the section that asked for it ────────────
#
# By the time the build reaches asset resolution, the filler has already
# substituted the section's tokens. An art slot with no source became an empty
# default in the emitted component:
#
#     imageUrl = "",
#
# — which every one of these templates guards on (`const x = url && url.trim()
# ? url : null`), so an empty slot renders as no picture rather than as a
# broken one. Placement is therefore a single, precisely-targeted rewrite of
# that default: `imageUrl = ""` -> `imageUrl = "/images/generated/<hash>.png"`.
#
# The prop name is the slot name in camelCase — the convention every template
# in this library follows and the one the filler already relies on. Anything
# else (a repeater slot, a prop that is not there, a slot already carrying a
# value) is NOT rewritten and is reported as unplaced, because a rewrite that
# guessed would corrupt a component for the sake of a decoration.

def _camel(slot: str) -> str:
    head, *rest = slot.split("_")
    return head + "".join(p[:1].upper() + p[1:] for p in rest)


def place_slot(tsx: str, slot: str, src: str):
    """Fill one empty art slot in an already-filled component.

    Returns `(tsx, placed: bool)`. `placed` is False — leaving the tsx
    untouched — when the slot is a repeater (`members[].image_url`), when the
    prop is absent, or when it already carries a value. False is a reported
    outcome, never an exception: a decoration that could not be placed is a
    missing decoration, not a failed build.
    """
    if not slot or "[]" in slot:
        return tsx, False
    prop = _camel(slot)
    pattern = re.compile(
        r'(?P<head>\b%s\s*=\s*)(?P<q>["\'])(?P=q)' % re.escape(prop))
    new_tsx, n = pattern.subn(
        lambda m: '%s"%s"' % (m.group("head"), src), tsx, count=1)
    return (new_tsx, True) if n else (tsx, False)
