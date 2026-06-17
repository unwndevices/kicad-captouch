"""Build slider electrode polygons from :class:`SliderParams`.

Construction (single source of truth for both exporters and the GUI preview):

1. Lay ``M = num_segments + 2*end_dummies`` segment cells of width ``W`` edge to
   edge, separated by gap ``A`` (centre pitch ``W + A``), centred on the origin.
2. For each of the ``M-1`` inter-segment boundaries, build a waveform polyline
   (straight / triangle / square per shape) and buffer it by ``A/2`` into a
   uniform-width "gap strip". Round joins give the gap rounded corners — the ESD
   relief vendors recommend (guidelines section 2.2 / 5.8) — for free.
3. Subtract the union of the strips from the slider rectangle. The result is
   exactly ``M`` interlocking electrodes, each separated from its neighbours by
   ``A`` everywhere.

The gap is therefore guaranteed uniform (it is an offset of the boundary),
sidestepping the variable clearance a naive horizontal shift would produce.
"""

from __future__ import annotations

from dataclasses import dataclass

from shapely.geometry import LineString, MultiPolygon, Polygon, box
from shapely.ops import unary_union

from ..params import SliderParams, validate_slider
from . import waveform

__all__ = ["Electrode", "SliderGeometry", "build_slider"]

Point = tuple[float, float]

# Maps the user-facing shape name to the waveform kind.
_SHAPE_TO_KIND = {
    "rectangular": "rectangular",
    "chevron": "triangle",
    "interdigitated": "square",
}

# Quarter-circle segments for the gap-strip round joins (and ESD rounding).
# 2 keeps emitted pads lean (~20-50 pts) while still rounding gap corners;
# finer than the fab can resolve at a 0.25 mm fillet anyway.
_ARC_QUAD_SEGS = 2

# Coordinate rounding (mm). 1e-4 mm = 0.1 um, far below fab resolution; keeps
# emitted coordinates and golden files stable.
_ROUND = 4

# Anchor circle radius (mm) for the custom pads (see exporter). The interior
# point each electrode exposes must comfortably contain this.
ANCHOR_RADIUS = 0.25


class GeometryError(ValueError):
    """Raised when slider geometry cannot be built as expected."""


@dataclass(frozen=True)
class Electrode:
    """One physical slider segment and how it maps to a pad / symbol pin."""

    polygon: Polygon
    pad_number: str
    pin_name: str
    role: str  # "active" | "dummy"
    anchor: Point  # interior point for the custom-pad anchor

    @property
    def points(self) -> list[Point]:
        """Exterior ring as ``(x, y)`` vertices, no duplicate closing point."""
        coords = list(self.polygon.exterior.coords)
        if coords and coords[0] == coords[-1]:
            coords = coords[:-1]
        return [(round(x, _ROUND), round(y, _ROUND)) for x, y in coords]


@dataclass(frozen=True)
class SliderGeometry:
    """The complete geometric model of a slider."""

    electrodes: list[Electrode]
    bounds: tuple[float, float, float, float]  # (minx, miny, maxx, maxy)
    params: SliderParams

    @property
    def active(self) -> list[Electrode]:
        return [e for e in self.electrodes if e.role == "active"]

    @property
    def dummies(self) -> list[Electrode]:
        return [e for e in self.electrodes if e.role == "dummy"]


def _anchor_point(poly: Polygon) -> Point:
    """An interior point comfortably containing the anchor circle."""
    inner = poly.buffer(-ANCHOR_RADIUS, quad_segs=_ARC_QUAD_SEGS)
    src = poly if inner.is_empty else inner
    p = src.representative_point()
    return (round(p.x, _ROUND), round(p.y, _ROUND))


def _role_and_naming(params: SliderParams) -> list[tuple[str, str, str]]:
    """Return ``(role, pad_number, pin_name)`` per physical segment, left to right.

    Active electrodes take pad numbers ``1..N`` and pin names ``E1..EN``; end
    dummies take the following numbers and are all named ``GND``.
    """
    n = params.num_segments
    d = params.end_dummies
    m = params.num_physical_segments

    out: list[tuple[str, str, str]] = []
    active_idx = 0
    dummy_idx = 0
    for s in range(m):
        is_active = d <= s < d + n
        if is_active:
            active_idx += 1
            out.append(("active", str(active_idx), f"E{active_idx}"))
        else:
            dummy_idx += 1
            out.append(("dummy", str(n + dummy_idx), "GND"))
    return out


def build_slider(params: SliderParams) -> SliderGeometry:
    """Build a :class:`SliderGeometry` from validated *params*."""
    validate_slider(params)

    w = params.width
    a = params.air_gap
    h = params.segment_height
    m = params.num_physical_segments
    amp = params.amplitude
    kind = _SHAPE_TO_KIND[params.segment_shape]

    total = params.total_length
    x_off = -total / 2.0  # centre the slider on the origin
    rect = box(x_off, -h / 2.0, x_off + total, h / 2.0)

    # Inter-segment boundaries, buffered into uniform gap strips.
    ext = a  # extend boundaries past the rectangle so strips cut cleanly
    strips = []
    for k in range(m - 1):
        x_nom = x_off + (k + 1) * (w + a) - a / 2.0
        pts = waveform.boundary_points(
            x_nom, amp, params.num_fingers, -h / 2.0 - ext, h / 2.0 + ext, kind
        )
        strip = LineString(pts).buffer(
            a / 2.0, cap_style="flat", join_style="round", quad_segs=_ARC_QUAD_SEGS
        )
        strips.append(strip)

    copper = rect.difference(unary_union(strips)) if strips else rect

    parts = list(copper.geoms) if isinstance(copper, MultiPolygon) else [copper]
    if len(parts) != m:
        raise GeometryError(
            f"expected {m} segments but geometry produced {len(parts)}; "
            f"reduce tooth_depth (must stay below W/2 = {w / 2.0:.3f} mm)"
        )
    parts.sort(key=lambda g: g.centroid.x)

    # Optional ESD relief: round convex (outer) corners via a morphological open.
    r = params.corner_radius
    if r > 0:
        rounded = []
        for g in parts:
            g2 = g.buffer(-r, quad_segs=_ARC_QUAD_SEGS).buffer(r, quad_segs=_ARC_QUAD_SEGS)
            if g2.is_empty or g2.geom_type != "Polygon":
                raise GeometryError(
                    f"corner_radius {r} mm erased a segment; reduce it below the "
                    f"thinnest copper feature"
                )
            rounded.append(g2)
        parts = rounded

    naming = _role_and_naming(params)
    electrodes = [
        Electrode(
            polygon=poly,
            pad_number=num,
            pin_name=name,
            role=role,
            anchor=_anchor_point(poly),
        )
        for poly, (role, num, name) in zip(parts, naming)
    ]

    union = unary_union(parts)
    minx, miny, maxx, maxy = union.bounds
    bounds = (round(minx, _ROUND), round(miny, _ROUND), round(maxx, _ROUND), round(maxy, _ROUND))
    return SliderGeometry(electrodes=electrodes, bounds=bounds, params=params)
