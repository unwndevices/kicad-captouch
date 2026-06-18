"""Slider parameter validation and the W + 2A finger constraint."""

from __future__ import annotations

import pytest

from captouch.params import SLIDER_PRESETS, SliderError, SliderParams, validate_slider


def test_width_derived_from_finger_satisfies_constraint():
    p = SliderParams()  # segment_width None -> derived
    assert p.width == pytest.approx(p.finger_diameter - 2 * p.air_gap)
    assert p.width + 2 * p.air_gap == pytest.approx(p.finger_diameter)
    validate_slider(p)  # must not raise


def test_explicit_width_violating_constraint_is_rejected():
    p = SliderParams(segment_width=8.0, finger_diameter=8.0, air_gap=0.5)
    with pytest.raises(SliderError, match="finger constraint"):
        validate_slider(p)


def test_relax_flag_bypasses_finger_constraint():
    p = SliderParams(segment_width=8.0, finger_diameter=8.0, relax_finger_constraint=True)
    validate_slider(p)  # must not raise


@pytest.mark.parametrize("n", [0, 1, 2])
def test_too_few_segments_rejected(n):
    with pytest.raises(SliderError, match="num_segments"):
        validate_slider(SliderParams(num_segments=n))


def test_unknown_shape_rejected():
    with pytest.raises(SliderError, match="segment_shape"):
        validate_slider(SliderParams(segment_shape="zigzag"))


def test_tooth_depth_must_be_below_half_width():
    # amplitude >= W/2 would let adjacent boundaries collide.
    p = SliderParams(segment_shape="chevron", tooth_depth=10.0)
    with pytest.raises(SliderError, match="tooth_depth"):
        validate_slider(p)


@pytest.mark.parametrize(
    "bad",
    [
        dict(air_gap=0.0),
        dict(segment_height=0.0),
        dict(end_dummies=3),
        dict(segment_width=-1.0, relax_finger_constraint=True),
    ],
)
def test_out_of_range_values_rejected(bad):
    with pytest.raises(SliderError):
        validate_slider(SliderParams(**bad))


def test_tip_radius_default_and_validation():
    assert SliderParams().tip_radius == 0.15
    with pytest.raises(SliderError, match="tip_radius"):
        validate_slider(SliderParams(tip_radius=-0.1))


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_float_rejected(bad):
    with pytest.raises(SliderError, match="finite"):
        validate_slider(SliderParams(air_gap=bad))


@pytest.mark.parametrize("name", sorted(SLIDER_PRESETS))
def test_presets_are_valid(name):
    validate_slider(SLIDER_PRESETS[name])


def test_derived_quantities():
    p = SliderParams(num_segments=4, end_dummies=1)  # W=7, A=0.5
    assert p.num_physical_segments == 6
    assert p.pitch == pytest.approx(7.5)
    # M*W + (M-1)*A
    assert p.total_length == pytest.approx(6 * 7 + 5 * 0.5)


@pytest.mark.parametrize("target", [50, 80, 100, 37])
def test_fit_to_length_lands_within_half_a_pitch(target):
    # Design from an overall length: the achieved total_length is within half the
    # (fixed) pitch of the target, and the result validates.
    p = SliderParams().fit_to_length(target)
    validate_slider(p)
    assert abs(p.total_length - target) <= p.pitch / 2 + 1e-9


def test_fit_to_length_floors_at_three_segments():
    # A tiny target still yields the 3-segment interpolation minimum.
    assert SliderParams().fit_to_length(1.0).num_segments == 3


def test_fit_to_length_keeps_other_fields():
    base = SliderParams(segment_shape="interdigitated", end_dummies=2, name="S")
    p = base.fit_to_length(90)
    assert (p.segment_shape, p.end_dummies, p.name) == ("interdigitated", 2, "S")
