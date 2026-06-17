"""Pure geometry layer: parameters -> Shapely polygons.

Functions here turn a widget's :mod:`captouch.params` dataclass into the
polygons (electrodes, courtyard bounds) that the exporters and the GUI both
consume — the single source of truth that keeps the preview byte-faithful to the
exported copper.

**No KiCad or Qt imports.** Depends only on Shapely.
"""

from __future__ import annotations

from .slider import Electrode, SliderGeometry, build_slider

__all__ = ["build_slider", "SliderGeometry", "Electrode"]
