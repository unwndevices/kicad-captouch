"""Mutual-cap slider geometry: the 1-D trackpad reuse, pin mapping, bounds."""

from __future__ import annotations

import pytest

from captouch.geometry import (
    MutualSliderGeometry,
    TrackpadGeometry,
    build_mutual_slider,
)
from captouch.params import MutualSliderError, MutualSliderParams


@pytest.mark.parametrize("segments,rows", [(3, 1), (5, 1), (6, 2)])
def test_net_counts_and_names(segments, rows):
    geo = build_mutual_slider(MutualSliderParams(num_segments=segments, sense_rows=rows))
    assert isinstance(geo, MutualSliderGeometry)
    assert isinstance(geo, TrackpadGeometry)  # reuses the trackpad export/preview path
    assert len(geo.rx_nets) == rows  # sense lines
    assert len(geo.tx_nets) == segments  # drive electrodes = position nodes
    assert [n.pin_name for n in geo.rx_nets] == [f"Rx{i + 1}" for i in range(rows)]
    assert [n.pin_name for n in geo.tx_nets] == [f"Tx{i + 1}" for i in range(segments)]


def test_single_sense_row_is_one_continuous_fcu_line():
    geo = build_mutual_slider(MutualSliderParams(num_segments=5, sense_rows=1))
    (rx,) = geo.rx_nets
    assert len(rx.fcu) == 1  # one connected F.Cu polygon spanning the length
    assert rx.bcu == [] and rx.vias == []  # sense line is via-free (low Cp)


def test_drive_electrodes_are_bridged_on_bcu():
    geo = build_mutual_slider(MutualSliderParams(num_segments=5, sense_rows=1))
    for tx in geo.tx_nets:
        assert tx.bcu, "each Tx column carries a B.Cu strap"
        assert tx.vias, "each Tx column is bridged over the Rx neck by thru-hole vias"


@pytest.mark.parametrize("segments,rows,pitch", [(5, 1, 6.0), (4, 2, 5.0)])
def test_bounds_track_length_and_height(segments, rows, pitch):
    p = MutualSliderParams(num_segments=segments, sense_rows=rows, diamond_pitch=pitch)
    minx, miny, maxx, maxy = build_mutual_slider(p).bounds
    assert maxx - minx == pytest.approx(segments * pitch)  # length along the slider
    assert maxy - miny == pytest.approx(rows * pitch)  # transverse height


def test_centred_on_origin():
    geo = build_mutual_slider(MutualSliderParams(num_segments=6, sense_rows=1))
    minx, miny, maxx, maxy = geo.bounds
    assert minx == pytest.approx(-maxx) and miny == pytest.approx(-maxy)


def test_symbol_columns_split_rx_left_tx_right():
    geo = build_mutual_slider(MutualSliderParams(num_segments=5, sense_rows=1))
    left, right = geo.symbol_columns()
    assert [name for _, name in left] == ["Rx1"]
    assert [name for _, name in right] == [f"Tx{i + 1}" for i in range(5)]


def test_invalid_params_raise_before_build():
    with pytest.raises(MutualSliderError):
        build_mutual_slider(MutualSliderParams(num_segments=2))
