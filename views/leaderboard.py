"""
views/leaderboard.py
─────────────────────
Right panel — driver standings with multi-pin toggle.

Clicking a driver pins them (adds their telemetry card).
Clicking again unpins (removes the card). Pinned drivers show ●.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor

from views.track_map import DRIVER_COLORS


class LeaderboardWidget(QWidget):
    """Scrollable race-order list with click-to-pin multi-select."""

    driver_added   = Signal(str)   # emits abbr when driver is pinned
    driver_removed = Signal(str)   # emits abbr when driver is unpinned

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedWidth(180)
        self._pinned: set[str] = set()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.setSpacing(6)

        header = QLabel("STANDINGS")
        header.setStyleSheet(
            "color: white; font-size: 12px; font-weight: bold; letter-spacing: 1px;"
        )
        header.setAlignment(Qt.AlignCenter)

        self._list = QListWidget()
        self._list.setSelectionMode(QListWidget.NoSelection)
        self._list.setStyleSheet("""
            QListWidget {
                background-color: #0d0d1f;
                border: 1px solid #333355;
                border-radius: 4px;
                color: white;
                font-size: 12px;
            }
            QListWidget::item {
                padding: 6px 10px;
                border-bottom: 1px solid #1e1e3a;
            }
            QListWidget::item:hover {
                background-color: #2a2a4a;
            }
        """)
        self._list.itemClicked.connect(self._on_item_clicked)

        layout.addWidget(header)
        layout.addWidget(self._list)

    # ── Public API ────────────────────────────────────────────────────────────

    def update(self, drivers: list[str]) -> None:
        """Repopulate with drivers in race order, maintaining pin state."""
        self._list.clear()
        for pos, abbr in enumerate(drivers, start=1):
            pinned = abbr in self._pinned
            prefix = "● " if pinned else "  "
            item = QListWidgetItem(f"{prefix}P{pos:>2}  {abbr}")
            item.setData(Qt.UserRole, abbr)
            item.setForeground(QColor(DRIVER_COLORS.get(abbr, "#FFFFFF")))
            if pinned:
                font = item.font()
                font.setBold(True)
                item.setFont(font)
            self._list.addItem(item)

    def deselect_driver(self, abbr: str) -> None:
        """Remove pin state without emitting a signal (called by main_window)."""
        self._pinned.discard(abbr)
        self._refresh_item(abbr)

    # ── Private ───────────────────────────────────────────────────────────────

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        abbr = item.data(Qt.UserRole)
        if not abbr:
            return
        if abbr in self._pinned:
            self._pinned.discard(abbr)
            self.driver_removed.emit(abbr)
        else:
            self._pinned.add(abbr)
            self.driver_added.emit(abbr)
        self._refresh_item(abbr)

    def _refresh_item(self, abbr: str) -> None:
        """Update the visual state of a single row without rebuilding the list."""
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item.data(Qt.UserRole) == abbr:
                pinned = abbr in self._pinned
                pos_text = item.text().strip().split("  ", 1)[-1]  # keep "P1  VER"
                prefix = "● " if pinned else "  "
                item.setText(f"{prefix}{pos_text}")
                font = item.font()
                font.setBold(pinned)
                item.setFont(font)
                return
