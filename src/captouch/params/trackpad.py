"""Mutual-capacitance XY diamond trackpad parameters, validation, and presets.

A trackpad is a **diamond (rhombus) row/column matrix** sensed in mutual-cap
(CSX) mode: every Rx row crosses every Tx column, and each crossing is an
independently-read node, so an ``R×C`` pad needs only ``R + C`` pins yet resolves
``R·C`` nodes with sub-pitch interpolation on both axes (Microchip AN2934 §1.2.5;
Infineon AN234185 §3.1; see ``docs/capacitive-touch-design-guidelines.md`` §4).

Two interlocking diamond sub-lattices, offset by half a pitch on both axes, tile
the pad:

* **Rx rows** run horizontally and are **continuous on F.Cu** — their diamonds are
  joined edge-to-edge by F.Cu necks;
* **Tx columns** run vertically and are **bridged on B.Cu** — their diamonds sit on
  F.Cu but the column-to-column link that would cross an Rx neck is carried by a
  B.Cu strap between two thru-hole vias (Microchip AN2934 §2.2.5; Azoteq AZD068
  §2.1). Bridging the drive (Tx) axis keeps the sense (Rx) lines via-free and
  low-Cp, which the guidelines recommend (#Rx ≤ #Tx, route Rx shortest — §4.3/§4.5).

Geometry (``geometry/trackpad.py``):

* diamond half-diagonal ``d = (pitch − gap·√2) / 2`` so the facing 45° edges of
  adjacent Rx/Tx diamonds are exactly ``gap`` apart;
* same-axis neighbours, ``gap·√2`` apart at their facing vertices, are joined by a
  ``bridge_width``-wide neck (F.Cu for Rx) or strap + vias (B.Cu for Tx);
* the lattice is clipped to the panel rectangle so every edge terminates in a
  **half-diamond** (Infineon AN234185 §4.3).

This module has **no KiCad, geometry, or Qt imports** — it is pure data.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

from .slider import SliderError

__all__ = ["TrackpadParams", "TrackpadError", "validate_trackpad", "TRACKPAD_PRESETS"]

#: Min annular ring (mm) required between a via's drill and its outer diameter
#: (i.e. ``via_diameter >= via_drill + 2 * MIN_ANNULAR``). 0.1 mm = 4 mil, a
#: conservative fab floor (Infineon AN85951 §7.4.9 places vias at the pad edge).
MIN_ANNULAR = 0.1

#: Hard limits on the matrix dimensions (Microchip AT11849: 3–16 rows/columns,
#: <=100 total nodes).
MIN_LINES = 3
MAX_LINES = 16
MAX_NODES = 100


class TrackpadError(SliderError):
    """Raised when a :class:`TrackpadParams` violates a design constraint.

    Subclasses :class:`SliderError` so the GUI/CLI ``except SliderError`` paths
    catch trackpad errors with one handler, as :class:`WheelError` does.
    """


@dataclass(frozen=True)
class TrackpadParams:
    """Parameters for a mutual-cap XY diamond trackpad.

    All lengths are in millimetres. Defaults follow the guidelines (§4.2 / §6.4).

    Attributes
    ----------
    num_rows:
        Number of **Rx (sense)** rows — horizontal, continuous-on-F.Cu electrode
        lines. ``3``..``16`` (Microchip AT11849).
    num_cols:
        Number of **Tx (drive)** columns — vertical, B.Cu-bridged electrode lines.
        ``3``..``16``. For lowest sense-line noise keep ``num_rows <= num_cols``
        (#Rx <= #Tx; guidelines §4.3) — recommended, not enforced.
    diamond_pitch:
        Row/column centre-to-centre spacing ``P``. ~5 mm suits an 8 mm finger so a
        contact always overlaps >=2 diamonds per axis (§4.2).
    diamond_gap:
        Nominal copper-to-copper gap ``A`` between the parallel edges of adjacent
        Rx/Tx diamonds. Vendor range 0.1–1 mm (typ 0.3); the default 0.5 mm keeps
        the connecting-neck *pinch* clearance (necessarily tighter than ``A`` in
        any diamond pattern, ~``A/√2``) above common fab/DRC minimums. Smaller
        gaps need a finer fab clearance.
    bridge_width:
        Width of the F.Cu necks (Rx) and B.Cu straps (Tx) that join same-axis
        diamonds. Sized to the fab's min trace (guidelines give no mm; §4.4).
    via_drill:
        Finished hole diameter of the bridge vias (Infineon: 10 mil/0.25 mm at the
        pad edge; §5.6).
    via_diameter:
        Outer copper diameter of the bridge vias (``>= via_drill + 2*MIN_ANNULAR``).
    name:
        Base name for the emitted footprint / symbol.
    """

    num_rows: int = 4
    num_cols: int = 5
    diamond_pitch: float = 5.0
    diamond_gap: float = 0.5
    bridge_width: float = 0.2
    via_drill: float = 0.3
    via_diameter: float = 0.6
    name: str = "CT_Trackpad"

    # -- resolved (derived) quantities ------------------------------------- #
    @property
    def half_diag(self) -> float:
        """Diamond half-diagonal ``d = (pitch − gap·√2) / 2``."""
        return (self.diamond_pitch - self.diamond_gap * math.sqrt(2.0)) / 2.0

    @property
    def diamond_diag(self) -> float:
        """Full diamond diagonal (vertex-to-opposite-vertex), ``2·d``."""
        return 2.0 * self.half_diag

    @property
    def num_rx(self) -> int:
        """Number of Rx (sense) lines = rows."""
        return self.num_rows

    @property
    def num_tx(self) -> int:
        """Number of Tx (drive) lines = columns."""
        return self.num_cols

    @property
    def num_nodes(self) -> int:
        """Independently-sensed crossings, ``num_rows · num_cols``."""
        return self.num_rows * self.num_cols

    @property
    def num_pins(self) -> int:
        """Total pins / pads, ``num_rows + num_cols`` (one per Rx/Tx line)."""
        return self.num_rows + self.num_cols

    @property
    def width(self) -> float:
        """Overall pad width (mm); half-diamond edges → ``num_cols · pitch``."""
        return self.num_cols * self.diamond_pitch

    @property
    def height(self) -> float:
        """Overall pad height (mm); half-diamond edges → ``num_rows · pitch``."""
        return self.num_rows * self.diamond_pitch

    def resolved(self) -> "TrackpadParams":
        """Return a copy (parity with slider/wheel; nothing to resolve here)."""
        return replace(self)


def validate_trackpad(p: TrackpadParams) -> TrackpadParams:
    """Validate *p*, raising :class:`TrackpadError` on any constraint violation.

    Returns *p* unchanged on success so it can be used inline.
    """
    for field, val in (("num_rows", p.num_rows), ("num_cols", p.num_cols)):
        if not MIN_LINES <= val <= MAX_LINES:
            raise TrackpadError(
                f"{field} must be {MIN_LINES}..{MAX_LINES} (Microchip AT11849), got {val}"
            )
    if p.num_nodes > MAX_NODES:
        raise TrackpadError(
            f"num_rows·num_cols = {p.num_nodes} exceeds the {MAX_NODES}-node limit "
            f"(Microchip AT11849); reduce num_rows or num_cols"
        )
    if p.diamond_pitch <= 0:
        raise TrackpadError(f"diamond_pitch must be > 0, got {p.diamond_pitch}")
    if p.diamond_gap <= 0:
        raise TrackpadError(f"diamond_gap must be > 0, got {p.diamond_gap}")
    if p.half_diag <= 0:
        raise TrackpadError(
            f"diamond_gap {p.diamond_gap} mm is too wide for pitch {p.diamond_pitch} mm: "
            f"the diamond half-diagonal would be {p.half_diag:.3f} mm (<=0). "
            f"Need pitch > gap·√2 = {p.diamond_gap * math.sqrt(2.0):.3f} mm."
        )
    if p.bridge_width <= 0:
        raise TrackpadError(f"bridge_width must be > 0, got {p.bridge_width}")
    # The neck must fit through the gap·√2-wide corridor between the diamonds it
    # passes, leaving copper on each side (else it merges with the crossing axis).
    corridor = p.diamond_gap * math.sqrt(2.0)
    if p.bridge_width >= corridor:
        raise TrackpadError(
            f"bridge_width {p.bridge_width} mm must be < gap·√2 = {corridor:.3f} mm "
            f"so the connecting neck fits between the diamonds it bridges"
        )
    if p.bridge_width >= 2.0 * p.half_diag:
        raise TrackpadError(
            f"bridge_width {p.bridge_width} mm must be < the diamond diagonal "
            f"{p.diamond_diag:.3f} mm"
        )
    if p.via_drill <= 0:
        raise TrackpadError(f"via_drill must be > 0, got {p.via_drill}")
    if p.via_diameter < p.via_drill + 2.0 * MIN_ANNULAR:
        raise TrackpadError(
            f"via_diameter {p.via_diameter} mm must be >= via_drill + 2·{MIN_ANNULAR} "
            f"= {p.via_drill + 2.0 * MIN_ANNULAR:.3f} mm (min annular ring)"
        )
    if p.via_diameter >= p.half_diag:
        raise TrackpadError(
            f"via_diameter {p.via_diameter} mm must be < the diamond half-diagonal "
            f"{p.half_diag:.3f} mm so each via sits well inside a diamond, clear of "
            f"its tip and of the perpendicular axis"
        )
    return p


#: Named starting points drawn from the guidelines doc (§4.2 / §4.3 tables).
TRACKPAD_PRESETS: dict[str, TrackpadParams] = {
    # Infineon AN234185 §4.3 reference: 5x5 diamond matrix, ~5 mm pitch, 10 pins.
    "infineon": TrackpadParams(
        name="CT_Trackpad_Infineon",
        num_rows=5,
        num_cols=5,
        diamond_pitch=5.0,
        diamond_gap=0.5,
    ),
    # Microchip AN2934 (Table 1-6) compact pad: 4x6, 6 mm pitch.
    "microchip": TrackpadParams(
        name="CT_Trackpad_Microchip",
        num_rows=4,
        num_cols=6,
        diamond_pitch=6.0,
        diamond_gap=0.5,
    ),
    # Small smoke/demo pad — the smallest matrix with interior crossings.
    "compact": TrackpadParams(
        name="CT_Trackpad_Compact",
        num_rows=3,
        num_cols=3,
        diamond_pitch=5.0,
        diamond_gap=0.5,
    ),
}
