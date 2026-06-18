"""Trackpad parameters: derivations, constraint validation, presets."""

from __future__ import annotations

import math

import pytest

from captouch.params import (
    TRACKPAD_PRESETS,
    SliderError,
    TrackpadError,
    TrackpadParams,
    validate_trackpad,
)


def test_half_diag_derived_from_pitch_and_gap():
    p = TrackpadParams(diamond_pitch=5.0, diamond_gap=0.5)
    assert p.half_diag == pytest.approx((5.0 - 0.5 * math.sqrt(2.0)) / 2.0)
    assert p.diamond_diag == pytest.approx(2.0 * p.half_diag)


def test_node_and_pin_counts():
    p = TrackpadParams(num_rows=4, num_cols=5)
    assert p.num_nodes == 20
    assert p.num_pins == 9
    assert (p.num_rx, p.num_tx) == (4, 5)


def test_overall_extent_is_lines_times_pitch():
    p = TrackpadParams(num_rows=4, num_cols=5, diamond_pitch=5.0)
    assert p.width == pytest.approx(25.0)
    assert p.height == pytest.approx(20.0)


@pytest.mark.parametrize("key", sorted(TRACKPAD_PRESETS))
def test_presets_validate(key):
    validate_trackpad(TRACKPAD_PRESETS[key])  # must not raise


def test_trackpad_error_is_a_slider_error():
    # so the GUI/CLI `except SliderError` path catches it (like WheelError).
    assert issubclass(TrackpadError, SliderError)


@pytest.mark.parametrize("field,value", [("num_rows", 2), ("num_cols", 2),
                                         ("num_rows", 17), ("num_cols", 17)])
def test_reject_line_counts_out_of_range(field, value):
    with pytest.raises(TrackpadError, match="3..16"):
        validate_trackpad(TrackpadParams(**{field: value}))


def test_reject_too_many_nodes():
    with pytest.raises(TrackpadError, match="node"):
        validate_trackpad(TrackpadParams(num_rows=16, num_cols=16))


def test_reject_gap_too_wide_for_pitch():
    # gap·√2 >= pitch drives the half-diagonal non-positive.
    with pytest.raises(TrackpadError, match="half-diagonal"):
        validate_trackpad(TrackpadParams(diamond_pitch=2.0, diamond_gap=2.0))


def test_reject_nonpositive_gap():
    with pytest.raises(TrackpadError, match="diamond_gap"):
        validate_trackpad(TrackpadParams(diamond_gap=0.0))


def test_reject_bridge_wider_than_corridor():
    # bridge_width must be < gap·√2 so the neck fits between the diamonds.
    with pytest.raises(TrackpadError, match="bridge_width"):
        validate_trackpad(TrackpadParams(diamond_gap=0.3, bridge_width=1.0))


def test_reject_via_without_annular_ring():
    with pytest.raises(TrackpadError, match="annular"):
        validate_trackpad(TrackpadParams(via_drill=0.5, via_diameter=0.55))


def test_reject_nonpositive_via_drill():
    with pytest.raises(TrackpadError, match="via_drill"):
        validate_trackpad(TrackpadParams(via_drill=0.0))
