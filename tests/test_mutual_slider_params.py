"""Mutual-cap slider parameters: derivations, validation, mapping, presets, dispatch."""

from __future__ import annotations

import pytest

from captouch.params import (
    MAX_SENSE_ROWS,
    MIN_SEGMENTS,
    MUTUAL_SLIDER_PRESETS,
    MutualSliderError,
    MutualSliderParams,
    SliderError,
    TrackpadParams,
    check_advisories,
    check_fab,
    params_from_json,
    params_to_json,
    recommended_series_r,
    validate_mutual_slider,
    validate_trackpad,
)


def test_pin_and_node_counts():
    # N Tx drive electrodes + sense_rows Rx lines; N*sense_rows crossings.
    p = MutualSliderParams(num_segments=6, sense_rows=1)
    assert (p.num_segments, p.sense_rows) == (6, 1)
    assert p.num_nodes == 6
    assert p.num_pins == 7  # N + 1 (single sense line)
    assert MutualSliderParams(num_segments=6, sense_rows=2).num_pins == 8


def test_length_and_height_track_pitch():
    p = MutualSliderParams(num_segments=5, sense_rows=2, diamond_pitch=6.0)
    assert p.total_length == pytest.approx(30.0)  # N * pitch
    assert p.height == pytest.approx(12.0)  # sense_rows * pitch


def test_error_is_a_slider_error():
    # so the GUI/CLI `except SliderError` path catches it with one handler.
    assert issubclass(MutualSliderError, SliderError)


@pytest.mark.parametrize("n", [2, 1, 0])
def test_reject_too_few_segments(n):
    with pytest.raises(MutualSliderError, match="num_segments"):
        validate_mutual_slider(MutualSliderParams(num_segments=n))


@pytest.mark.parametrize("rows", [0, 3, 5])
def test_reject_out_of_range_sense_rows(rows):
    with pytest.raises(MutualSliderError, match="sense_rows"):
        validate_mutual_slider(MutualSliderParams(sense_rows=rows))


@pytest.mark.parametrize("rows", range(1, MAX_SENSE_ROWS + 1))
def test_valid_sense_rows_accepted(rows):
    assert validate_mutual_slider(MutualSliderParams(sense_rows=rows)) is not None


def test_diamond_geometry_constraints_deferred_to_trackpad():
    # A gap too wide for the pitch must still be rejected (via the shared validator).
    with pytest.raises(SliderError, match="diamond"):
        validate_mutual_slider(MutualSliderParams(diamond_pitch=3.0, diamond_gap=2.5))


def test_to_trackpad_maps_axes_and_is_buildable():
    p = MutualSliderParams(num_segments=5, sense_rows=1, name="MS")
    tp = p.to_trackpad()
    assert isinstance(tp, TrackpadParams)
    assert tp.num_cols == p.num_segments  # Tx drive electrodes along the length
    assert tp.num_rows == p.sense_rows  # Rx sense rows
    assert tp.mask_shape == "rect" and tp.name == "MS"
    # The mapped trackpad must pass the shared validator at the 1-line floor.
    validate_trackpad(tp, min_lines=1)


def test_support_and_overlay_pass_through_to_trackpad():
    p = MutualSliderParams(
        ground_hatch=True, guard_ring=True, overlay_thickness=1.0, overlay_er=3.0
    )
    tp = p.to_trackpad()
    assert tp.ground_hatch and tp.guard_ring
    assert tp.overlay_thickness == 1.0 and tp.overlay_er == 3.0


def test_fit_to_length_rounds_segments_to_pitch():
    p = MutualSliderParams(diamond_pitch=6.0, num_segments=5)
    assert p.fit_to_length(60.0).num_segments == 10  # 60 / 6
    assert p.fit_to_length(1.0).num_segments == MIN_SEGMENTS  # floored


def test_mutual_cap_series_r_is_2k():
    value, mode = recommended_series_r(MutualSliderParams())
    assert value == "2 kΩ" and "mutual" in mode.lower()


def test_advisories_dispatch_as_mutual_cap():
    # The series-R recommendation is always present and reflects the mutual mode.
    adv = check_advisories(MutualSliderParams())
    series = [a for a in adv if a.feature == "series resistor"]
    assert series and "2 kΩ" in series[0].message


def test_fab_check_uses_trackpad_features():
    # A sub-clearance diamond gap is flagged by the (shared) trackpad fab features.
    p = MutualSliderParams(diamond_gap=0.05, bridge_width=0.03)
    feats = {v.feature for v in check_fab(p)}
    assert any("diamond" in f or "bridge" in f for f in feats)


def test_json_round_trip_preserves_widget_identity():
    p = MutualSliderParams(num_segments=7, sense_rows=2, name="RT")
    text = params_to_json(p)
    assert '"widget": "mutual-slider"' in text
    back = params_from_json(text)
    assert isinstance(back, MutualSliderParams) and back == p


@pytest.mark.parametrize("key", sorted(MUTUAL_SLIDER_PRESETS))
def test_presets_are_valid(key):
    p = MUTUAL_SLIDER_PRESETS[key]
    assert validate_mutual_slider(p) is p
    assert p.num_segments >= MIN_SEGMENTS and 1 <= p.sense_rows <= MAX_SENSE_ROWS
