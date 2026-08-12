"""Check the real music_assistant_models against tests/ma_contract.py.

These assertions are the ones the unit suite structurally cannot make, because
it replaces the package with stubs before importing the provider. Everything
here is about upstream behaviour the provider silently depends on; a failure
means Music Assistant changed under us, and both the provider and the stubs in
``tests/python/conftest.py`` need attention.
"""

from __future__ import annotations

import dataclasses

import pytest

import ma_contract


def test_content_type_has_the_members_the_provider_uses(real_models):
    content_type = real_models.enums.ContentType
    missing = [
        name
        for name in ma_contract.REQUIRED_CONTENT_TYPE_MEMBERS
        if not hasattr(content_type, name)
    ]
    assert not missing, f"upstream ContentType lost members the provider uses: {missing}"


def test_content_type_still_has_no_webm_member(real_models):
    """The reason ``_get_stream_format`` falls back to the codec.

    yt-dlp hands us Opus inside a WebM container. If upstream ever adds WEBM,
    the fallback becomes unnecessary and this test is the reminder to drop it.
    """
    content_type = real_models.enums.ContentType
    present = [
        name
        for name in ma_contract.FORBIDDEN_CONTENT_TYPE_MEMBERS
        if hasattr(content_type, name)
    ]
    assert not present, (
        f"upstream ContentType gained {present}; the codec fallback in "
        "_get_stream_format can probably be simplified now"
    )


def test_unknown_sentinel_value_is_unchanged(real_models):
    assert real_models.enums.ContentType.UNKNOWN.value == ma_contract.UNKNOWN_VALUE


@pytest.mark.parametrize(
    ("raw", "expected_member"), sorted(ma_contract.TRY_PARSE_EXPECTATIONS.items())
)
def test_try_parse_matches_the_contract(real_models, raw, expected_member):
    """Every container/codec string the provider can produce, parsed for real."""
    content_type = real_models.enums.ContentType
    assert content_type.try_parse(raw) is getattr(content_type, expected_member)


def test_audio_format_is_importable_from_the_path_the_provider_uses(real_models):
    """The provider imports AudioFormat from media_items, StreamDetails from
    streamdetails. Upstream re-exports AudioFormat from both, and the stub
    only registers it on media_items, so pin the arrangement we rely on.
    """
    assert real_models.media_items.AudioFormat is real_models.streamdetails.AudioFormat


def test_audio_format_exposes_the_fields_the_provider_sets(real_models):
    fields = {f.name for f in dataclasses.fields(real_models.media_items.AudioFormat)}
    missing = set(ma_contract.REQUIRED_AUDIO_FORMAT_FIELDS) - fields
    assert not missing, f"upstream AudioFormat lost fields the provider sets: {missing}"


def test_audio_format_accepts_the_values_the_provider_assigns(real_models):
    """Construct one the way the provider does, with a real Opus stream's data."""
    audio_format = real_models.media_items.AudioFormat(
        content_type=real_models.enums.ContentType.OPUS,
    )
    audio_format.sample_rate = 48000
    audio_format.channels = 2
    audio_format.bit_rate = 160
    assert audio_format.content_type is real_models.enums.ContentType.OPUS
    assert audio_format.bit_rate == 160


def test_media_type_has_the_members_the_provider_uses(real_models):
    media_type = real_models.enums.MediaType
    missing = [
        name for name in ma_contract.REQUIRED_MEDIA_TYPE_MEMBERS if not hasattr(media_type, name)
    ]
    assert not missing, f"upstream MediaType lost members the provider uses: {missing}"


def test_podcast_exposes_the_fields_the_provider_sets(real_models):
    fields = {f.name for f in dataclasses.fields(real_models.media_items.Podcast)}
    missing = set(ma_contract.REQUIRED_PODCAST_FIELDS) - fields
    assert not missing, f"upstream Podcast lost fields the provider sets: {missing}"


def test_podcast_episode_exposes_the_fields_the_provider_sets(real_models):
    fields = {f.name for f in dataclasses.fields(real_models.media_items.PodcastEpisode)}
    missing = set(ma_contract.REQUIRED_PODCAST_EPISODE_FIELDS) - fields
    assert not missing, f"upstream PodcastEpisode lost fields the provider sets: {missing}"


# Deliberately not asserted here: that ``position`` and ``podcast`` are
# *mandatory* upstream. The source on the models repo's main branch declares
# them without a default, but ``dataclasses.fields()`` on the released 1.1.186
# reports ``position.default is None``, so an assertion written from the source
# failed against the package users actually run. The provider sets both fields
# explicitly on every episode it builds and the unit suite pins that, which is
# the property worth protecting; how strict upstream chooses to be about it is
# upstream's business.


def test_podcast_episode_resume_state_is_still_nullable(real_models):
    """None means "provider does not know", and MA then uses its own resume point.

    The provider leaves these unset because YouTube's anonymous responses carry
    no reliable position. That is only correct while None keeps this meaning.
    """
    episode_fields = {f.name: f for f in dataclasses.fields(real_models.media_items.PodcastEpisode)}
    for name in ma_contract.NULLABLE_PODCAST_EPISODE_FIELDS:
        assert episode_fields[name].default is None, (
            f"PodcastEpisode.{name} no longer defaults to None; the provider "
            "would now be asserting a resume position it does not have"
        )


def test_stream_details_exposes_the_fields_the_provider_sets(real_models):
    fields = {f.name for f in dataclasses.fields(real_models.streamdetails.StreamDetails)}
    missing = set(ma_contract.REQUIRED_STREAM_DETAILS_FIELDS) - fields
    assert not missing, f"upstream StreamDetails lost fields the provider sets: {missing}"


def test_stream_details_still_cannot_express_delayed_availability(real_models):
    """Why ``get_stream_details`` blocks instead of handing over a timestamp.

    YouTube serves some tracks behind a pre-roll ad and the media url 403s
    until that window passes (issue #51). yt-dlp reports it as ``available_at``
    and sleeps; the provider has to sleep too, because there is no field on
    StreamDetails that would let Music Assistant schedule the wait instead.

    If upstream adds one, this test fails and the sleep in
    ``get_stream_details`` should move behind that field, so the provider call
    stops blocking.
    """
    fields = {f.name for f in dataclasses.fields(real_models.streamdetails.StreamDetails)}
    present = sorted(fields.intersection(ma_contract.FORBIDDEN_STREAM_DETAILS_FIELDS))
    assert not present, (
        f"upstream StreamDetails gained {present}; the pre-roll sleep in "
        "get_stream_details can now be handed to the server instead"
    )


def test_bit_rate_defaults_to_none_so_an_unset_value_is_distinguishable(real_models):
    """The provider only sets bit_rate when yt-dlp reported one.

    That is only meaningful if "not set" is representable. A numeric default
    would make every stream claim a bitrate it never measured.
    """
    assert real_models.media_items.AudioFormat().bit_rate is None
