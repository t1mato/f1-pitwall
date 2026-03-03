"""
views/main_window.py
─────────────────────
Top-level window — assembles all panels and owns the time scrubber.

Layout:
  ┌──────────────────────┬──────────────────────────┬─────────────────┐
  │ TrackDetails         │                          │                 │
  │  (top-left)          │       TrackMapWidget     │  Leaderboard    │
  ├──────────────────────│         (center)         │   (right)       │
  │ [scroll area]        │                          │                 │
  │  ● VER card          │                          │                 │
  │  ● HAM card          │                          │                 │
  └──────────────────────┴──────────────────────────┴─────────────────┘
                  [ ◀──────●───────────────▶ ]   scrubber
"""

import pandas as pd
import fastf1.core
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSlider, QLabel, QSplitter, QPushButton, QScrollArea,
)
from PySide6.QtCore import Qt, QTimer

from models.race_state import RaceState
from views.track_details import TrackDetailsWidget
from views.telemetry_panel import TelemetryPanel
from views.track_map import TrackMapWidget
from views.leaderboard import LeaderboardWidget


class MainWindow(QMainWindow):
    """Root application window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("F1 Telemetry Visualizer")
        self.resize(1440, 860)
        self.setStyleSheet("background-color: #1a1a2e;")

        self._race_state: RaceState | None = None
        self._tick_count = 0

        # Per-driver card and telemetry cache
        self._telemetry_cards: dict[str, TelemetryPanel] = {}
        self._cached_tel_dfs:  dict[str, pd.DataFrame]   = {}

        self._play_timer = QTimer()
        self._play_timer.setInterval(50)
        self._play_timer.timeout.connect(self._advance_scrubber)
        self._play_step = 50

        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        root.addWidget(self._build_panels(), stretch=1)
        root.addWidget(self._build_scrubber())

    # ── Layout builders ───────────────────────────────────────────────────────

    def _build_panels(self) -> QSplitter:
        """Horizontal splitter: left column | track map | leaderboard."""
        h_split = QSplitter(Qt.Horizontal)

        # Left column: track details + scrollable driver cards
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)

        self._track_details = TrackDetailsWidget()
        left_layout.addWidget(self._track_details)

        # Scroll area for stacked driver cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent; border: none;")

        self._cards_content = QWidget()
        self._cards_layout  = QVBoxLayout(self._cards_content)
        self._cards_layout.setContentsMargins(0, 0, 4, 0)
        self._cards_layout.setSpacing(6)
        self._cards_layout.addStretch()   # cards insert before this

        scroll.setWidget(self._cards_content)
        left_layout.addWidget(scroll)

        self._track_map   = TrackMapWidget()
        self._leaderboard = LeaderboardWidget()

        h_split.addWidget(left_widget)
        h_split.addWidget(self._track_map)
        h_split.addWidget(self._leaderboard)
        h_split.setStretchFactor(0, 1)
        h_split.setStretchFactor(1, 3)
        h_split.setStretchFactor(2, 1)

        self._leaderboard.driver_added.connect(self._add_driver_card)
        self._leaderboard.driver_removed.connect(self._remove_driver_card)

        return h_split

    def _build_scrubber(self) -> QWidget:
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(4, 0, 4, 0)

        self._time_label = QLabel("00:00:00")
        self._time_label.setStyleSheet(
            "color: white; font-size: 11px; font-family: monospace;"
        )
        self._time_label.setFixedWidth(68)

        self._scrubber = QSlider(Qt.Horizontal)
        self._scrubber.setRange(0, 0)
        self._scrubber.setValue(0)
        self._scrubber.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 4px; background: #333355; border-radius: 2px;
            }
            QSlider::handle:horizontal {
                width: 12px; height: 12px; margin: -4px 0;
                border-radius: 6px; background: #E8002D;
            }
            QSlider::sub-page:horizontal {
                background: #E8002D; border-radius: 2px;
            }
        """)
        self._scrubber.valueChanged.connect(self._on_scrubber_moved)

        self._play_btn = QPushButton("⏸")
        self._play_btn.setFixedSize(32, 24)
        self._play_btn.setStyleSheet(
            "color: white; background-color: #333355; border: none; "
            "border-radius: 4px; font-size: 13px;"
        )
        self._play_btn.clicked.connect(self._toggle_play)

        row.addWidget(self._play_btn)
        row.addWidget(self._time_label)
        row.addWidget(self._scrubber)
        return container

    # ── Public API ────────────────────────────────────────────────────────────

    def load_race(self, session: fastf1.core.Session) -> None:
        """Initialise the dashboard with a loaded FastF1 session."""
        self._race_state = RaceState(session)

        lap = session.laps.pick_fastest()
        tel = lap.get_telemetry().add_distance()
        self._track_map.draw_track_outline(
            tel["X"].to_numpy(), tel["Y"].to_numpy()
        )

        self._track_details.set_session_info(
            circuit      = session.event["EventName"],
            country      = session.event["Country"],
            session_type = session.name,
            total_laps   = int(session.laps["LapNumber"].max()),
        )

        t_min, t_max = self._race_state.time_range
        try:
            race_start_ms = int(session.laps["LapStartTime"].min().total_seconds() * 1000)
        except Exception:
            race_start_ms = int(t_min.total_seconds() * 1000)

        self._scrubber.setRange(race_start_ms, int(t_max.total_seconds() * 1000))
        self._scrubber.setValue(race_start_ms)

        px, py = self._extract_pit_coords(session)
        if px is not None:
            self._track_map.draw_pit_lane(px, py)

        self._play_timer.start()

    # ── Card management ───────────────────────────────────────────────────────

    def _add_driver_card(self, abbr: str) -> None:
        """
        Create a telemetry card for abbr and insert it into the scroll area.

        TODO(human): implement this method.
        Steps:
          1. Guard: if abbr is already in self._telemetry_cards, return early.

          2. Create a new card:
                card = TelemetryPanel(driver_abbr=abbr)
                card.closed.connect(self._remove_driver_card)

          3. Insert the card before the trailing stretch:
                count = self._cards_layout.count()
                self._cards_layout.insertWidget(count - 1, card)
                self._telemetry_cards[abbr] = card

          4. Fetch telemetry and cache it:
                t = pd.Timedelta(milliseconds=self._scrubber.value())
                lap_data = self._race_state.get_lap_data_for(abbr, t)
                if lap_data:
                    tel = lap_data.lap.get_telemetry().add_distance()
                    self._cached_tel_dfs[abbr] = tel
                    row = tel.loc[(tel["SessionTime"] - t).abs().idxmin()]
                    card.set_current_position(
                        float(row["Distance"]), float(row["Throttle"]),
                        float(row["Speed"]),    int(row["nGear"]),
                        int(row["Brake"]) * 100, int(row["DRS"]),
                    )
        """
        if abbr in self._telemetry_cards:
            return

        card = TelemetryPanel(driver_abbr = abbr)
        card.closed.connect(self._remove_driver_card)

        count = self._cards_layout.count()
        self._cards_layout.insertWidget(count - 1, card)
        self._telemetry_cards[abbr] = card

        t = pd.Timedelta(milliseconds = self._scrubber.value())
        lap_data = self._race_state.get_lap_data_for(abbr, t)
        if lap_data:
            tel = lap_data.lap.get_telemetry().add_distance()
            self._cached_tel_dfs[abbr] = tel
            row = tel.loc[(tel["SessionTime"] - t).abs().idxmin()]
            card.set_current_position(
                float(row["Distance"]), 
                float(row["Throttle"]),
                float(row["Speed"]), 
                int(row["nGear"]),
                int(row["Brake"]) * 100, 
                int(row["DRS"]),
            )

    def _remove_driver_card(self, abbr: str) -> None:
        """Remove and destroy a driver's telemetry card."""
        card = self._telemetry_cards.pop(abbr, None)
        if card:
            card.hide()
            card.deleteLater()
        self._cached_tel_dfs.pop(abbr, None)
        self._leaderboard.deselect_driver(abbr)

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _extract_pit_coords(session):
        try:
            pitted = session.laps.dropna(subset=["PitInTime", "PitOutTime"])
            if pitted.empty:
                return None, None
            pit_lap    = pitted.iloc[0]
            num_row    = session.results[session.results["Abbreviation"] == pit_lap["Driver"]]
            if num_row.empty:
                return None, None
            driver_num = str(int(num_row.iloc[0]["DriverNumber"]))
            if driver_num not in session.pos_data:
                return None, None
            pos_df  = session.pos_data[driver_num]
            margin  = pd.Timedelta(seconds=5)
            mask    = (pos_df["Time"] >= pit_lap["PitInTime"] - margin) & \
                      (pos_df["Time"] <= pit_lap["PitOutTime"] + margin)
            pit_pos = pos_df[mask]
            if pit_pos.empty:
                return None, None
            return pit_pos["X"].to_numpy(), pit_pos["Y"].to_numpy()
        except Exception:
            return None, None

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _toggle_play(self) -> None:
        if self._play_timer.isActive():
            self._play_timer.stop()
            self._play_btn.setText("▶")
        else:
            self._play_timer.start()
            self._play_btn.setText("⏸")

    def _advance_scrubber(self) -> None:
        val      = self._scrubber.value()
        next_val = val + self._play_step
        if next_val >= self._scrubber.maximum():
            self._play_timer.stop()
        self._scrubber.setValue(min(next_val, self._scrubber.maximum()))

    def _on_scrubber_moved(self, value: int) -> None:
        if self._race_state is None:
            return

        total_secs = value / 1000.0
        t = pd.Timedelta(seconds=total_secs)

        hours, rem = divmod(int(total_secs), 3600)
        mins, secs = divmod(rem, 60)
        self._time_label.setText(f"{hours:02}:{mins:02}:{secs:02}")

        # ── Fast path (every tick) ────────────────────────────────────────────
        self._track_map.update_cars(self._race_state.get_positions_at(t))

        # Update all pinned driver cards
        for abbr, tel in self._cached_tel_dfs.items():
            card = self._telemetry_cards.get(abbr)
            if card is None:
                continue
            closest = (tel["SessionTime"] - t).abs().idxmin()
            row = tel.loc[closest]
            card.set_current_position(
                float(row["Distance"]),
                float(row["Throttle"]),
                float(row["Speed"]),
                int(row["nGear"]),
                int(row["Brake"]) * 100,
                int(row["DRS"]),
            )

        # ── Slow path (every 20 ticks ≈ 1 s) ─────────────────────────────────
        self._tick_count += 1
        if self._tick_count % 20 == 0:
            drivers = self._race_state.get_leaderboard_at(t)
            self._leaderboard.update(drivers)
            if drivers:
                lap_data = self._race_state.get_lap_data_for(drivers[0], t)
                if lap_data:
                    self._track_details.set_current_lap(int(lap_data.lap["LapNumber"]))
