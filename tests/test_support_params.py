"""Optional support-copper params: defaults off, validation, JSON round-trip."""

from __future__ import annotations

import pytest

from captouch.params import (
    SliderError,
    SliderParams,
    TrackpadError,
    TrackpadParams,
    WheelError,
    WheelParams,
    check_fab,
    has_support,
    params_from_json,
    params_to_json,
    validate_slider,
    validate_trackpad,
    validate_wheel,
)

_DEFAULTS = [SliderParams(), WheelParams(), TrackpadParams()]


@pytest.mark.parametrize("p", _DEFAULTS)
def test_support_copper_off_by_default(p):
    assert p.ground_hatch is False
    assert p.guard_ring is False
    assert has_support(p) is False


@pytest.mark.parametrize("p", _DEFAULTS)
def test_has_support_true_when_enabled(p):
    from dataclasses import replace

    assert has_support(replace(p, ground_hatch=True))
    assert has_support(replace(p, guard_ring=True))


def test_enabled_features_validate():
    validate_slider(SliderParams(ground_hatch=True, guard_ring=True))
    validate_wheel(WheelParams(ground_hatch=True, guard_ring=True))
    validate_trackpad(TrackpadParams(ground_hatch=True, guard_ring=True))


@pytest.mark.parametrize(
    "kwargs,match",
    [
        ({"ground_hatch": True, "ground_hatch_width": 0.0}, "ground_hatch_width"),
        ({"ground_hatch": True, "ground_hatch_pitch": 0.1}, "ground_hatch_pitch"),
        ({"ground_hatch": True, "ground_margin": -1.0}, "ground_margin"),
        ({"guard_ring": True, "guard_width": 0.0}, "guard_width"),
        ({"guard_ring": True, "guard_gap": 0.0}, "guard_gap"),
        ({"guard_ring": True, "guard_break": -0.1}, "guard_break"),
    ],
)
def test_bad_enabled_values_rejected(kwargs, match):
    with pytest.raises(SliderError, match=match):
        validate_slider(SliderParams(**kwargs))


def test_bad_values_inert_when_feature_off():
    # A nonsense value for a disabled feature must not block generation.
    validate_slider(SliderParams(ground_hatch=False, ground_hatch_width=0.0))
    validate_slider(SliderParams(guard_ring=False, guard_gap=-5.0))


def test_wheel_and_trackpad_use_their_own_error():
    with pytest.raises(WheelError, match="guard_gap"):
        validate_wheel(WheelParams(guard_ring=True, guard_gap=0.0))
    with pytest.raises(TrackpadError, match="ground_hatch_width"):
        validate_trackpad(TrackpadParams(ground_hatch=True, ground_hatch_width=0.0))


@pytest.mark.parametrize(
    "p",
    [
        SliderParams(name="S", ground_hatch=True, guard_ring=True, guard_width=0.6),
        WheelParams(name="W", ground_hatch=True, ground_margin=3.0),
        TrackpadParams(name="T", guard_ring=True, guard_mask_open=False),
    ],
)
def test_json_round_trip_with_support_copper(p):
    back = params_from_json(params_to_json(p))
    assert back == p
    assert params_to_json(back) == params_to_json(p)


def test_guard_ring_width_is_fab_checked():
    # A guard ring thinner than the profile min track must surface as a violation,
    # proving the support copper feeds the existing fab-rule channel (Phase 9 will
    # extend --strict; Phase 8 only warns).
    p = SliderParams(guard_ring=True, guard_width=0.05)
    labels = [v.feature for v in check_fab(p, "default")]
    assert "guard ring width" in labels


def test_support_copper_off_adds_no_fab_features():
    base = len(check_fab(SliderParams(), "default"))
    # toggling the values while disabled changes nothing
    assert (
        len(check_fab(SliderParams(guard_width=0.01, ground_hatch_width=0.01), "default")) == base
    )
