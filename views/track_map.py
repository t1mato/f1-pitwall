"""
views/track_map.py
───────────────────
Center panel — 2D track outline with live car position dots.

Two layers drawn on one pyqtgraph PlotItem:
  1. Track outline  — a static white polyline from X/Y telemetry of one full lap
  2. Car dots       — a ScatterPlotItem updated on every scrubber tick

Coordinate system:
  X/Y are in metres, track-relative (FastF1 GPS data).
  The aspect ratio is locked (1:1) so the circuit isn't distorted.
"""

import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import QWidget, QVBoxLayout

# Team color map — keyed by driver abbreviation for the MVP set.
# Extend as needed; unknown drivers fall back to white.
DRIVER_COLORS: dict[str, str] = {
    "VER": "#3671C6", "PER": "#3671C6",   # Red Bull
    "HAM": "#27F4D2", "RUS": "#27F4D2",   # Mercedes
    "LEC": "#E8002D", "SAI": "#E8002D",   # Ferrari
    "NOR": "#FF8000", "PIA": "#FF8000",   # McLaren
    "ALO": "#358C75", "STR": "#358C75",   # Aston Martin
    "GAS": "#0093CC", "OCO": "#0093CC",   # Alpine
    "TSU": "#6692FF", "RIC": "#6692FF",   # RB / AlphaTauri
    "HUL": "#B6BABD", "MAG": "#B6BABD",   # Haas
    "BOT": "#C92D4B", "ZHO": "#C92D4B",   # Kick Sauber
    "ALB": "#64C4FF", "SAR": "#64C4FF",   # Williams
}


class TrackMapWidget(QWidget):
    """Pyqtgraph-based track map with live car position dots."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        canvas = pg.GraphicsLayoutWidget()
        layout.addWidget(canvas)

        self._plot: pg.PlotItem = canvas.addPlot()
        self._plot.setAspectLocked(True)       # keep circuit proportions
        self._plot.hideAxis("bottom")
        self._plot.hideAxis("left")
        self._plot.setMenuEnabled(False)

        # Track outline — drawn once, never updated
        self._outline: pg.PlotDataItem = self._plot.plot(
            pen=pg.mkPen(color="#444466", width=12),   # wide grey for track width feel
        )

        # Car dots — updated on every scrubber tick
        self._scatter: pg.ScatterPlotItem = pg.ScatterPlotItem(size=10, pxMode=True)
        self._plot.addItem(self._scatter)

    # ── Coordinate transform ──────────────────────────────────────────────────

    @staticmethod
    def _rotate(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """
        Rotate GPS coordinates 90° clockwise so the circuit faces north-up.
        FastF1 Bahrain (and most circuits) need this to match broadcast orientation.
        270° clockwise (90° counter-clockwise): new_x = -y,  new_y = x
        """
        return -y, x

    # ── Public API ────────────────────────────────────────────────────────────

    def draw_track_outline(self, x: np.ndarray, y: np.ndarray) -> None:
        """
        Draw the static circuit shape from one full lap's GPS coordinates.

        Called once after the session loads.
        x, y are numpy arrays of equal length in metres.
        """
        rx, ry = self._rotate(x, y)
        self._outline.setData(rx, ry)

    def draw_pit_lane(self, x: np.ndarray, y: np.ndarray) -> None:
        """
        Overlay the pit lane path on the track map.

        Drawn as a brighter line so it's visually distinct from the circuit.
        Called once after the session loads, after draw_track_outline().
        """
        rx, ry = self._rotate(x, y)
        self._plot.plot(
            rx, ry,
            pen=pg.mkPen(color="#888899", width=8),
        )

    def update_cars(self, positions: dict[str, tuple[float, float]]) -> None:
        """
        Reposition all car dots on the track map.

        Called on every scrubber tick. positions comes directly from
        RaceState.get_positions_at() → {abbr: (x, y)}.

        TODO(human): implement this method.
        You need to build a list of spot dicts for pg.ScatterPlotItem.setSpots().
        Each spot dict has keys:
            "pos"    : (x, y)        — position tuple
            "brush"  : pg.mkBrush()  — fill color
            "pen"    : pg.mkPen()    — outline (use pg.mkPen(None) for no outline)
        Use DRIVER_COLORS.get(abbr, "#FFFFFF") to look up each driver's color.
        Then call: self._scatter.setSpots(spots)
        """

        spots = []

        for abbr, (x, y) in positions.items():
            color = DRIVER_COLORS.get(abbr, "#FFFFFF")
            rx, ry = self._rotate(
                np.array([x], dtype=float), np.array([y], dtype=float)
            )
            spots.append({
                "pos": (float(rx[0]), float(ry[0])),
                "brush": pg.mkBrush(color),
                "pen": pg.mkPen(None),
            })

        self._scatter.setData(spots=spots)
        
