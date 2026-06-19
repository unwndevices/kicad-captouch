"""Keypad (discrete self-cap button grid) parameters: derivations, validation,
presets, advisories, fab dispatch, JSON round-trip."""

from __future__ import annotations

import math

import pytest

from captouch.params import (
    BUTTON_GAP_MM,
    BUTTON_SHAPES,
    KEYPAD_PRESETS,
    KeypadError,
    KeypadParams,
    SliderError,
    check_advisories,
    check_fab,
    params_from_json,
    params_to_json,
    recommended_series_r,
    validate_keypad,
)
from captouch.params.advisory import BUTTON_OVERLAY_SIZE_FACTOR


def test_pin_and_button_counts():
    p = KeypadParams(num_rows=4, num_cols=3)
    assert p.num_buttons == 12
    assert p.num_pins == 12  # one pin per button (self-cap, no shared lines)


def test_pitch_and_extent_track_size_and_gap():
    p = KeypadParams(num_rows=2, num_cols=3, button_size=10.0, gap=4.0)
    assert p.pitch == pytest.approx(14.0)  # size + gap
    assert p.width == pytest.approx(3 * 14.0 - 4.0)  # cols*pitch - gap
    assert p.height == pytest.approx(2 * 14.0 - 4.0)


@pytest.mark.parametrize(
    "shape,expected",
    [
        ("rect", 100.0),  # 10*10
        ("circle", math.pi * 25.0),  # pi*r^2, r=5
        ("diamond", 50.0),  # d^2/2
    ],
)
def test_button_area_per_shape(shape, expected):
    assert KeypadParams(button_shape=shape, button_size=10.0).button_area == pytest.approx(expected)


def test_error_is_a_slider_error():
    # so the GUI/CLI `except SliderError` path catches it with one handler.
    assert issubclass(KeypadError, SliderError)


def test_default_gap_is_the_guideline_baseline():
    assert KeypadParams().gap == BUTTON_GAP_MM == 4.0


@pytest.mark.parametrize("shape", BUTTON_SHAPES)
def test_valid_shapes_accepted(shape):
    assert validate_keypad(KeypadParams(button_shape=shape)) is not None


def test_reject_unknown_shape():
    with pytest.raises(KeypadError, match="button_shape"):
        validate_keypad(KeypadParams(button_shape="hexagon"))


@pytest.mark.parametrize("field", ["num_rows", "num_cols"])
def test_reject_zero_dimensions(field):
    with pytest.raises(KeypadError, match=field):
        validate_keypad(KeypadParams(**{field: 0}))


def test_single_button_grid_is_valid():
    assert validate_keypad(KeypadParams(num_rows=1, num_cols=1)) is not None


def test_reject_nonpositive_size_and_gap():
    with pytest.raises(KeypadError, match="button_size"):
        validate_keypad(KeypadParams(button_size=0))
    with pytest.raises(KeypadError, match="gap"):
        validate_keypad(KeypadParams(gap=0))


def test_reject_corner_radius_over_half_button():
    with pytest.raises(KeypadError, match="corner_radius"):
        validate_keypad(KeypadParams(button_size=8.0, corner_radius=5.0))


def test_self_cap_series_r_is_560():
    value, mode = recommended_series_r(KeypadParams())
    assert value == "560 Ω" and "self" in mode.lower()


def test_series_r_advisory_always_present():
    adv = check_advisories(KeypadParams())
    series = [a for a in adv if a.feature == "series resistor"]
    assert series and "560 Ω" in series[0].message


def test_overlay_advisories_off_without_overlay():
    # No overlay specified -> only the always-on series-R (no sizing/separation note).
    features = {a.feature for a in check_advisories(KeypadParams())}
    assert "button vs overlay sizing" not in features
    assert "button separation" not in features


def test_button_too_small_for_overlay_blocks():
    # button_size below 3x overlay trips the sizing advisory (blocking under --strict).
    p = KeypadParams(button_size=5.0, overlay_thickness=2.0)  # need >= 6 mm
    sizing = [a for a in check_advisories(p) if a.feature == "button vs overlay sizing"]
    assert sizing and sizing[0].blocks
    assert BUTTON_OVERLAY_SIZE_FACTOR == 3.0


def test_button_gap_too_tight_for_overlay_blocks():
    # gap below 4 mm + overlay trips the separation advisory.
    p = KeypadParams(button_size=12.0, gap=4.0, overlay_thickness=2.0)  # need >= 6 mm
    sep = [a for a in check_advisories(p) if a.feature == "button separation"]
    assert sep and sep[0].blocks


def test_overlay_never_changes_geometry_fields():
    # The advisory-only overlay fields leave the geometry params untouched.
    bare = KeypadParams(button_size=10.0, gap=4.0)
    overlaid = KeypadParams(button_size=10.0, gap=4.0, overlay_thickness=2.0)
    assert (bare.pitch, bare.width, bare.height) == (
        overlaid.pitch,
        overlaid.width,
        overlaid.height,
    )


def test_fab_check_flags_subclearance_gap():
    feats = {v.feature for v in check_fab(KeypadParams(gap=0.05))}
    assert any("button-to-button" in f for f in feats)


def test_json_round_trip_preserves_widget_identity():
    p = KeypadParams(num_rows=2, num_cols=5, button_shape="circle", name="RT")
    text = params_to_json(p)
    assert '"widget": "keypad"' in text
    back = params_from_json(text)
    assert isinstance(back, KeypadParams) and back == p


@pytest.mark.parametrize("key", sorted(KEYPAD_PRESETS))
def test_presets_are_valid_and_clear_default_fab(key):
    p = KEYPAD_PRESETS[key]
    assert validate_keypad(p) is p
    assert p.num_buttons >= 1
    assert check_fab(p, "default") == [], f"{p.name} trips the default fab profile"
