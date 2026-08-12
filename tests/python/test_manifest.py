"""Tests that lock down the provider manifest contract."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


MANIFEST_PATH = Path(__file__).resolve().parents[2] / "ytmusic_free" / "manifest.json"


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_manifest_required_top_level_fields(manifest):
    for key in ("type", "domain", "name", "description", "codeowners", "requirements"):
        assert key in manifest, f"manifest is missing required key: {key}"


def test_manifest_domain_matches_package_dir(manifest):
    assert manifest["domain"] == "ytmusic_free"
    assert MANIFEST_PATH.parent.name == manifest["domain"]


def test_manifest_type_is_music(manifest):
    assert manifest["type"] == "music"


def test_manifest_codeowners_non_empty(manifest):
    assert isinstance(manifest["codeowners"], list)
    assert manifest["codeowners"], "manifest must list at least one codeowner"


def test_manifest_requirements_pin_known_libs(manifest):
    requirements = manifest["requirements"]
    assert isinstance(requirements, list)
    joined = " ".join(requirements)
    assert "ytmusicapi" in joined
    assert "yt-dlp" in joined
    # duration-parser was dropped once timestamp parsing moved in-house (PR #29);
    # guard against it creeping back as a needless dependency.
    assert "duration-parser" not in joined


def test_manifest_yt_dlp_floor_covers_the_preroll_field(manifest):
    """A fresh install must land on a yt-dlp the pre-roll fix can trust.

    ``available_at`` exists from 2025.08.20 but is a flat +6s on every format
    until 2025.12.08, so the floor has to clear the later date. The provider
    also guards at runtime (``_ytdlp_honours_preroll``), because pip will not
    upgrade an already-satisfied requirement and existing installs keep
    whatever they first resolved. See issue #51.
    """
    import ytmusic_free as ytm

    requirement = next(r for r in manifest["requirements"] if r.startswith("yt-dlp"))
    _, _, floor = requirement.partition(">=")
    assert floor, f"expected a >= floor on yt-dlp, got {requirement!r}"
    parsed = tuple(int(part) for part in floor.split("."))
    assert parsed >= ytm.MIN_YTDLP_VERSION_FOR_PREROLL, (
        f"manifest allows yt-dlp {floor}, which predates ad-derived "
        "available_at; a fresh install would wait 6s before every track"
    )


def test_manifest_documentation_url_present(manifest):
    assert manifest.get("documentation", "").startswith("https://")


def test_manifest_declares_multi_instance(manifest):
    # Identity check, not truthiness: Music Assistant reads this straight into
    # ProviderManifest, and the string "true" would be just as truthy in a test
    # while meaning nothing to the config flow. See issue #40.
    assert manifest["multi_instance"] is True
