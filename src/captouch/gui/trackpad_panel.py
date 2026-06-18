"""Parameter editor for a :class:`TrackpadParams` (XY diamond trackpad).

Mirrors the slider / wheel panels but for the trackpad's fields: a mutual-cap
diamond matrix has no shape / teeth / finger knobs — just the matrix size, the
diamond pitch and gap, and the bridge / via dimensions. Editing anything emits
:attr:`changed`.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QLineEdit,
    QVBoxLayout,
)

from ..geometry import build_trackpad
from ..params import TRACKPAD_PRESETS, TrackpadParams
from ._panel_base import PRESET_PLACEHOLDER as _PRESET_PLACEHOLDER
from ._panel_base import PanelBase

__all__ = ["TrackpadPanel"]


class TrackpadPanel(PanelBase):
    """Form bound to a :class:`TrackpadParams`; emits :attr:`changed` on any edit."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._build()
        self.set_params(TrackpadParams())

    def build_geometry(self):
        """Build the trackpad geometry for the current form (may raise TrackpadError)."""
        return build_trackpad(self.params())

    # -- construction ------------------------------------------------------- #
    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        self.preset = QComboBox()
        self.preset.addItem(_PRESET_PLACEHOLDER)
        self.preset.addItems(sorted(TRACKPAD_PRESETS))
        self.preset.activated.connect(self._on_preset)
        preset_box = QGroupBox("Preset")
        pl = QVBoxLayout(preset_box)
        pl.addWidget(self.preset)
        root.addWidget(preset_box)

        # Matrix.
        self.name = QLineEdit()
        self.num_rows = self._spin(3, 16, 1)
        self.num_cols = self._spin(3, 16, 1)
        matrix_box = QGroupBox("Matrix")
        mf = QFormLayout(matrix_box)
        mf.addRow("Name", self.name)
        mf.addRow("Rx rows (sense)", self.num_rows)
        mf.addRow("Tx columns (drive)", self.num_cols)
        root.addWidget(matrix_box)

        # Diamonds.
        self.diamond_pitch = self._dspin(2.0, 12.0, 0.5)
        self.diamond_gap = self._dspin(0.1, 2.0, 0.05)
        dim_box = QGroupBox("Diamonds (mm)")
        df = QFormLayout(dim_box)
        df.addRow("Pitch", self.diamond_pitch)
        df.addRow("Gap", self.diamond_gap)
        root.addWidget(dim_box)

        # Bridges & vias.
        self.bridge_width = self._dspin(0.1, 2.0, 0.05)
        self.via_drill = self._dspin(0.1, 1.0, 0.05)
        self.via_diameter = self._dspin(0.2, 2.0, 0.05)
        bridge_box = QGroupBox("Bridges && vias (mm)")
        bf = QFormLayout(bridge_box)
        bf.addRow("Bridge / neck width", self.bridge_width)
        bf.addRow("Via drill", self.via_drill)
        bf.addRow("Via diameter", self.via_diameter)
        root.addWidget(bridge_box)

        root.addStretch(1)

        self.name.textEdited.connect(self._emit)

    # -- signals ------------------------------------------------------------ #
    def _on_preset(self, index: int) -> None:
        if index <= 0:
            return
        key = self.preset.itemText(index)
        self.set_params(TRACKPAD_PRESETS[key])
        self.preset.setCurrentIndex(0)
        self.changed.emit()

    # -- params <-> form ---------------------------------------------------- #
    def params(self) -> TrackpadParams:
        """Read the form into a (possibly invalid, unvalidated) TrackpadParams."""
        return TrackpadParams(
            num_rows=self.num_rows.value(),
            num_cols=self.num_cols.value(),
            diamond_pitch=self.diamond_pitch.value(),
            diamond_gap=self.diamond_gap.value(),
            bridge_width=self.bridge_width.value(),
            via_drill=self.via_drill.value(),
            via_diameter=self.via_diameter.value(),
            name=self.name.text() or "CT_Trackpad",
        )

    def set_params(self, p: TrackpadParams) -> None:
        """Load *p* into the form without emitting :attr:`changed`."""
        self._loading = True
        try:
            self.name.setText(p.name)
            self.num_rows.setValue(p.num_rows)
            self.num_cols.setValue(p.num_cols)
            self.diamond_pitch.setValue(p.diamond_pitch)
            self.diamond_gap.setValue(p.diamond_gap)
            self.bridge_width.setValue(p.bridge_width)
            self.via_drill.setValue(p.via_drill)
            self.via_diameter.setValue(p.via_diameter)
        finally:
            self._loading = False
