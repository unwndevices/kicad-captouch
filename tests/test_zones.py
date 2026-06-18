"""Support-copper geometry: ground pour, guard ring (broken), net-tie, fab grow."""

from __future__ import annotations

import pytest
from shapely.geometry import Point as GeoPoint

from captouch.geometry import build_slider, build_trackpad, build_wheel
from captouch.geometry.zones import build_support, net_tie_number
from captouch.params import SliderParams, TrackpadParams, WheelParams


def _slider(**kw):
    return build_slider(SliderParams(name="S", **kw))


def test_disabled_builds_nothing():
    for geo in (_slider(), build_wheel(WheelParams()), build_trackpad(TrackpadParams())):
        assert build_support(geo) is None
        assert net_tie_number(geo) is None


def test_net_tie_number_follows_electrodes():
    geo = _slider(num_segments=4, end_dummies=1, ground_hatch=True)  # 4 active + 2 dummy
    nums = {int(e.pad_number) for e in geo.electrodes}
    assert net_tie_number(geo) == str(max(nums) + 1)


def test_net_tie_number_follows_trackpad_nets():
    geo = build_trackpad(TrackpadParams(num_rows=3, num_cols=3, guard_ring=True))  # 6 nets
    nums = {int(n.pad_number) for n in geo.nets}
    assert net_tie_number(geo) == str(max(nums) + 1)


def test_ground_only_has_no_guard():
    sc = build_support(_slider(ground_hatch=True))
    assert sc is not None
    assert sc.ground is not None and sc.ground.area > 0
    assert sc.guard is None and sc.mask_open is None


def test_guard_only_has_no_ground():
    sc = build_support(_slider(guard_ring=True))
    assert sc is not None
    assert sc.guard is not None and sc.ground is None


def test_guard_ring_is_a_single_hole_free_polygon():
    # The top break turns the annulus into an open C — one simple polygon, so it
    # emits as a single zone outline (KiCad zone polygons cannot carry a hole).
    sc = build_support(_slider(guard_ring=True))
    assert sc.guard.geom_type == "Polygon"
    assert len(sc.guard.interiors) == 0


def test_guard_break_actually_opens_the_ring():
    geo = _slider(guard_ring=True, guard_gap=2.0, guard_width=0.8)
    sc = build_support(geo)
    _, miny, _, maxy = geo.bounds
    mid = 2.0 + 0.8 / 2.0  # band centreline offset
    top = GeoPoint(0.0, miny - mid)  # where the break is cut
    bottom = GeoPoint(0.0, maxy + mid)  # solid, opposite the break
    assert not sc.guard.covers(top), "break should remove copper at the top centre"
    assert sc.guard.covers(bottom), "band should be solid opposite the break"


def test_mask_open_tracks_the_flag():
    assert build_support(_slider(guard_ring=True, guard_mask_open=True)).mask_open is not None
    assert build_support(_slider(guard_ring=True, guard_mask_open=False)).mask_open is None


def test_wheel_ground_punches_the_centre_hole():
    sc = build_support(build_wheel(WheelParams(name="W", ground_hatch=True)))
    assert len(sc.ground.interiors) == 1  # centre keep-out preserved
    assert "circle" in [o[0] for o in sc.fab_outlines]  # inner-hole fab circle kept


def test_fab_and_courtyard_grow_to_enclose_support():
    geo = _slider(guard_ring=True, guard_gap=2.0, guard_width=0.8)
    sc = build_support(geo)
    assert sc.fab_outlines[0][0] == "poly"
    # The courtyard ring must enclose the whole guard band.
    from shapely.geometry import Polygon

    crt = Polygon(sc.courtyard_pts)
    assert crt.covers(sc.guard)


@pytest.mark.parametrize(
    "kw", [{"mask_shape": "circle"}, {"mask_shape": "rrect", "corner_radius": 2.0}]
)
def test_guard_follows_curved_trackpad_mask(kw):
    geo = build_trackpad(TrackpadParams(num_rows=4, num_cols=4, guard_ring=True, **kw))
    sc = build_support(geo)
    assert sc.guard is not None and sc.guard.geom_type == "Polygon"
