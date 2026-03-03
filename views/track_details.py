"""
views/track_details.py
───────────────────────
Top-left panel — static session metadata displayed as styled labels.

Shows:
  • Circuit name and country
  • Session type (Race / Qualifying / etc.)
  • Total laps
  • Current lap (updates as scrubber moves)
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt


class TrackDetailsWidget(QWidget):
    """Displays circuit and session info in the top-left corner."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedWidth(220)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 8)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignTop)

        # ── Labels ────────────────────────────────────────────────────────────
        self._circuit   = self._make_label("─", bold=True, size=15)
        self._country   = self._make_label("─", size=11, muted=True)
        self._session   = self._make_label("─", size=11)
        self._total_lap = self._make_label("─", size=11)
        self._cur_lap   = self._make_label("Lap ─", bold=True, size=13)

        layout.addWidget(self._circuit)
        layout.addWidget(self._country)
        layout.addWidget(self._make_divider())
        layout.addWidget(self._session)
        layout.addWidget(self._total_lap)
        layout.addWidget(self._make_divider())
        layout.addWidget(self._cur_lap)
        layout.addStretch()

    # ── Public API ────────────────────────────────────────────────────────────

    def set_session_info(
        self,
        circuit: str,
        country: str,
        session_type: str,
        total_laps: int,
    ) -> None:
        """Populate static session metadata. Call once after session loads."""
        self._circuit.setText(circuit)
        self._country.setText(country)
        self._session.setText(f"Session: {session_type}")
        self._total_lap.setText(f"Total laps: {total_laps}")

    def set_current_lap(self, lap: int) -> None:
        """Update the current lap display as the scrubber moves."""
        self._cur_lap.setText(f"Lap {lap}")

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _make_label(
        text: str,
        bold: bool = False,
        size: int = 12,
        muted: bool = False,
    ) -> QLabel:
        label = QLabel(text)
        color = "#888888" if muted else "#e0e0e0"
        weight = "bold" if bold else "normal"
        label.setStyleSheet(
            f"color: {color}; font-size: {size}px; font-weight: {weight};"
        )
        return label

    @staticmethod
    def _make_divider() -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #333355;")
        return line
