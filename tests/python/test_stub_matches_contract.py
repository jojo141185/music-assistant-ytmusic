"""Hold the conftest stubs to the same contract as the real package.

``tests/python_integration/test_models_contract.py`` asserts that the genuine
``music_assistant_models`` matches ``tests/ma_contract.py``. This file asserts
that our stand-ins match the same table, which is the half that catches drift
introduced on our side rather than upstream.

Without this, the stubs can be edited into something more forgiving than
reality and every other test in this directory keeps passing. That is not
hypothetical: a stub with an invented ``ContentType.WEBM`` is why the suite was
green while real Music Assistant reported every Opus stream as ``"?"``.
"""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

import pytest

# Imports below are resolved against the stubs registered in conftest.py.
from music_assistant_models.enums import ContentType, MediaType

# Imported from media_items, not streamdetails, because that is the path the
# provider itself uses. Upstream re-exports the same class from both.
from music_assistant_models.media_items import AudioFormat, Podcast, PodcastEpisode
from music_assistant_models.streamdetails import StreamDetails

TESTS_ROOT = Path(__file__).resolve().parents[1]
if str(TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(TESTS_ROOT))

import ma_contract  # noqa: E402


def test_stub_is_actually_the_stub():
    """Guard against this file silently testing the real package instead."""
    assert getattr(sys.modules["music_assistant_models"], "__file__", None) is None, (
        "music_assistant_models resolved to a real installed package here; the "
        "unit suite is meant to run against the conftest stubs"
    )


def test_stub_has_the_required_members():
    missing = [
        name
        for name in ma_contract.REQUIRED_CONTENT_TYPE_MEMBERS
        if not hasattr(ContentType, name)
    ]
    assert not missing, f"stub ContentType is missing {missing}; see tests/ma_contract.py"


def test_stub_does_not_invent_members_upstream_lacks():
    """The exact failure that made the old suite lie."""
    present = [
        name
        for name in ma_contract.FORBIDDEN_CONTENT_TYPE_MEMBERS
        if hasattr(ContentType, name)
    ]
    assert not present, (
        f"stub ContentType invented {present}, which upstream does not have. A "
        "test double that is kinder than reality tests nothing."
    )


def test_stub_unknown_sentinel_matches():
    assert ContentType.UNKNOWN.value == ma_contract.UNKNOWN_VALUE


@pytest.mark.parametrize(
    ("raw", "expected_member"), sorted(ma_contract.TRY_PARSE_EXPECTATIONS.items())
)
def test_stub_try_parse_matches_the_contract(raw, expected_member):
    assert ContentType.try_parse(raw) is getattr(ContentType, expected_member)


def test_stub_audio_format_has_the_required_fields():
    fields = {f.name for f in dataclasses.fields(AudioFormat)}
    missing = set(ma_contract.REQUIRED_AUDIO_FORMAT_FIELDS) - fields
    assert not missing, f"stub AudioFormat is missing {missing}"


def test_stub_bit_rate_defaults_to_none():
    assert AudioFormat().bit_rate is None


def test_stub_media_type_has_the_required_members():
    missing = [
        name for name in ma_contract.REQUIRED_MEDIA_TYPE_MEMBERS if not hasattr(MediaType, name)
    ]
    assert not missing, f"stub MediaType is missing {missing}; see tests/ma_contract.py"


def test_stub_podcast_has_the_required_fields():
    fields = {f.name for f in dataclasses.fields(Podcast)}
    missing = set(ma_contract.REQUIRED_PODCAST_FIELDS) - fields
    assert not missing, f"stub Podcast is missing {missing}"


def test_stub_podcast_episode_has_the_required_fields():
    fields = {f.name for f in dataclasses.fields(PodcastEpisode)}
    missing = set(ma_contract.REQUIRED_PODCAST_EPISODE_FIELDS) - fields
    assert not missing, f"stub PodcastEpisode is missing {missing}"


def test_stub_stream_details_has_the_required_fields():
    fields = {f.name for f in dataclasses.fields(StreamDetails)}
    missing = set(ma_contract.REQUIRED_STREAM_DETAILS_FIELDS) - fields
    assert not missing, f"stub StreamDetails is missing {missing}"


def test_stub_stream_details_does_not_invent_a_delayed_availability_field():
    """The stub must not offer an escape hatch upstream does not have.

    ``get_stream_details`` blocks on a pre-roll ad window because there is no
    field to hand the timestamp to (issue #51). A stub that invented one would
    let a "cleaner" fix pass the unit suite and break in production.
    """
    fields = {f.name for f in dataclasses.fields(StreamDetails)}
    present = sorted(fields.intersection(ma_contract.FORBIDDEN_STREAM_DETAILS_FIELDS))
    assert not present, (
        f"stub StreamDetails invented {present}, which upstream does not have"
    )
