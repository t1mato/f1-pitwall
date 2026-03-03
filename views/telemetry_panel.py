"""
views/telemetry_panel.py
─────────────────────────
Reusable driver telemetry card.

One card is created per selected driver and stacked in the left column.

Layout:
  ┌── ● VER ─────────────────── [×] ─┐
  │   [287]          [7]             │
  │   km/h           GEAR            │
  │         [ DRS ON  ]              │
  │  BRAKE     [██████████████████]  │
  │  THROTTLE  [████████████░░░░░░]  │
  └──────────────────────────────────┘
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton, QFrame,
)
from PySide6.QtCore import Qt, Signal

from models.lap import LapData
from views.track_map import DRIVER_COLORS

_DRS_ON_STYLE  = "background:#00C853; color:#000; font-size:12px; font-weight:bold; border-radius:4px; padding:3px 12px;"
_DRS_OFF_STYLE = "background:#E8002D; color:#fff; font-size:12px; font-weight:bold; border-radius:4px; padding:3px 12px;"
_DRS_UNK_STYLE = "background:#333355; color:#888; font-size:12px; font-weight:bold; border-radius:4px; padding:3px 12px;"


class TelemetryPanel(QWidget):
    """Per-driver telemetry card with name header and close button."""

    closed = Signal(str)   # emits driver abbreviation when × is clicked

    def __init__(self, driver_abbr: str, parent=None) -> None:
        super().__init__(parent)
        self.driver_abbr = driver_abbr
        self._color = DRIVER_COLORS.get(driver_abbr, "#FFFFFF")

        self.setStyleSheet("background-color: #12122a; border-radius: 6px;")

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 6, 8, 8)
        root.setSpacing(8)

        root.addWidget(self._build_header())
        root.addWidget(self._build_readouts())
        root.addWidget(self._build_drs_indicator(), alignment=Qt.AlignHCenter)
        root.addWidget(self._build_bar("BRAKE",    "#E8002D"))
        root.addWidget(self._build_bar("THROTTLE", "#00D2BE"))

    # ── Build helpers ─────────────────────────────────────────────────────────

    def _build_header(self) -> QWidget:
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)

        name = QLabel(f"● {self.driver_abbr}")
        name.setStyleSheet(
            f"color: {self._color}; font-size: 14px; font-weight: bold;"
        )

        close_btn = QPushButton("×")
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet(
            "color: #888888; background: transparent; border: none; font-size: 16px;"
        )
        close_btn.clicked.connect(lambda: self.closed.emit(self.driver_abbr))

        row.addWidget(name)
        row.addStretch()
        row.addWidget(close_btn)

        # Divider below header
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet(f"color: {self._color}44;")

        wrapper = QWidget()
        vbox = QVBoxLayout(wrapper)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(4)
        vbox.addWidget(container)
        vbox.addWidget(divider)
        return wrapper

    def _build_readouts(self) -> QWidget:
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)

        self._speed_val = self._make_big_label("—", self._color)
        self._gear_val  = self._make_big_label("—", "#FFFFFF")

        for val_label, unit_text in [
            (self._speed_val, "km/h"),
            (self._gear_val,  "GEAR"),
        ]:
            block = QVBoxLayout()
            unit = QLabel(unit_text)
            unit.setStyleSheet("color: #666688; font-size: 10px;")
            unit.setAlignment(Qt.AlignCenter)
            block.addWidget(val_label)
            block.addWidget(unit)
            row.addLayout(block)

        return container

    def _build_drs_indicator(self) -> QLabel:
        self._drs_label = QLabel("DRS  —")
        self._drs_label.setStyleSheet(_DRS_UNK_STYLE)
        self._drs_label.setAlignment(Qt.AlignCenter)
        return self._drs_label

    def _build_bar(self, label_text: str, color: str) -> QWidget:
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        lbl = QLabel(label_text)
        lbl.setStyleSheet("color: white; font-size: 11px; font-weight: bold;")
        lbl.setFixedWidth(70)

        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(0)
        bar.setTextVisible(True)
        bar.setFormat("%v%")
        bar.setFixedHeight(18)
        bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #333355;
                border-radius: 3px;
                background-color: #0d0d1f;
                color: white;
                font-size: 10px;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 2px;
            }}
        """)
        row.addWidget(lbl)
        row.addWidget(bar)
        setattr(self, f"_{label_text.lower()}_bar", bar)
        return container

    @staticmethod
    def _make_big_label(text: str, color: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color: {color}; font-size: 40px; font-weight: bold; font-family: monospace;"
        )
        lbl.setAlignment(Qt.AlignCenter)
        return lbl

    # ── Public API ────────────────────────────────────────────────────────────

    def update(self, lap_data: LapData) -> None:
        pass

    def set_current_position(
        self,
        distance_m: float,
        throttle_pct: float,
        speed: float,
        gear: int,
        brake: int,
        drs: int,
    ) -> None:
        self._speed_val.setText(str(int(speed)))
        self._gear_val.setText(str(int(gear)))
        self._throttle_bar.setValue(int(throttle_pct))
        self._brake_bar.setValue(brake)
        if drs > 8:
            self._drs_label.setText("DRS  ON")
            self._drs_label.setStyleSheet(_DRS_ON_STYLE)
        else:
            self._drs_label.setText("DRS  OFF")
            self._drs_label.setStyleSheet(_DRS_OFF_STYLE)

    def clear(self) -> None:
        self._speed_val.setText("—")
        self._gear_val.setText("—")
        self._throttle_bar.setValue(0)
        self._brake_bar.setValue(0)
        self._drs_label.setText("DRS  —")
        self._drs_label.setStyleSheet(_DRS_UNK_STYLE)
