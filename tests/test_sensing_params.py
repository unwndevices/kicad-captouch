"""Overlay / board-stack sensing params: defaults off, validation, JSON round-trip."""

from __future__ import annotations

from dataclasses import replace

import pytest

from captouch.params import (
    BOARD_THICKNESS,
    OVERLAY_ER,
    SliderError,
    SliderParams,
    TrackpadError,
    TrackpadParams,
    WheelError,
    WheelParams,
    has_overlay,
    params_from_json,
    params_to_json,
    validate_slider,
    validate_trackpad,
    validate_wheel,
)

_DEFAULTS = [SliderParams(), WheelParams(), TrackpadParams()]
_VALIDATORS = [
    (SliderParams, validate_slider, SliderError),
    (WheelParams, validate_wheel, WheelError),
    (TrackpadParams, validate_trackpad, TrackpadError),
]


@pytest.mark.parametrize("p", _DEFAULTS)
def test_overlay_off_by_default(p):
    assert p.overlay_thickness == 0.0
    assert p.overlay_er == OVERLAY_ER
    assert p.board_thickness == BOARD_THICKNESS
    assert has_overlay(p) is False


@pytest.mark.parametrize("p", _DEFAULTS)
def test_has_overlay_true_when_thickness_set(p):
    assert has_overlay(replace(p, overlay_thickness=1.0)) is True


@pytest.mark.parametrize("cls,validate,_err", _VALIDATORS)
def test_defaults_and_overlay_validate(cls, validate, _err):
    validate(cls())  # overlay off
    validate(cls(overlay_thickness=1.0, overlay_er=3.0, board_thickness=1.6))


@pytest.mark.parametrize("cls,validate,err", _VALIDATORS)
def test_negative_overlay_thickness_rejected(cls, validate, err):
    with pytest.raises(err, match="overlay_thickness"):
        validate(cls(overlay_thickness=-0.5))


@pytest.mark.parametrize("cls,validate,err", _VALIDATORS)
def test_nonpositive_board_thickness_rejected(cls, validate, err):
    with pytest.raises(err, match="board_thickness"):
        validate(cls(board_thickness=0.0))


@pytest.mark.parametrize("cls,validate,err", _VALIDATORS)
def test_overlay_er_below_one_rejected_only_with_overlay(cls, validate, err):
    # εr < 1 is unphysical, but only checked when an overlay is actually specified.
    validate(cls(overlay_thickness=0.0, overlay_er=0.5))  # inert -> allowed
    with pytest.raises(err, match="overlay_er"):
        validate(cls(overlay_thickness=1.0, overlay_er=0.5))


@pytest.mark.parametrize("cls", [SliderParams, WheelParams, TrackpadParams])
def test_sensing_fields_round_trip_through_json(cls):
    p = cls(overlay_thickness=1.5, overlay_er=7.8, board_thickness=0.8)
    back = params_from_json(params_to_json(p))
    assert back.overlay_thickness == 1.5
    assert back.overlay_er == 7.8
    assert back.board_thickness == 0.8
