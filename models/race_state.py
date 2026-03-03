"""
models/race_state.py
─────────────────────
Session-level state for all cars at a given point in time.

Drives three panels in the dashboard:
  • Track map   — car X/Y positions at the current time
  • Leaderboard — race order at the current time
  • Telemetry   — LapData for the selected driver's current lap

Data sources (all from session.load()):
  session.pos_data  — dict[driver_number: str → DataFrame]
                      ~10 Hz X/Y/Z positions, Time-indexed (timedelta)
  session.laps      — all laps for all drivers (LapTime, Position, etc.)
  session.results   — final race results (used for driver metadata)
"""

import pandas as pd
import fastf1.core

from models.lap import LapData


class RaceState:
    """Wraps a loaded FastF1 session and answers time-based queries."""

    def __init__(self, session: fastf1.core.Session) -> None:
        self.session = session

        # Position data: {driver_number → DataFrame with Time/X/Y columns}
        self._pos_data: dict[str, pd.DataFrame] = session.pos_data

        # All laps across all drivers
        self._laps: pd.DataFrame = session.laps

        # Driver abbreviation lookup: number → abbr (e.g. "1" → "VER")
        self._num_to_abbr: dict[str, str] = (
            session.results.set_index("DriverNumber")["Abbreviation"]
            .to_dict()
        )

    # ── Time range ─────────────────────────────────────────────────────────────

    @property
    def time_range(self) -> tuple[pd.Timedelta, pd.Timedelta]:
        """
        (start, end) timedeltas for the scrubber range.
        Derived from the earliest and latest position sample across all cars.
        """
        all_times = pd.concat(
            [df["Time"] for df in self._pos_data.values()]
        )
        return all_times.min(), all_times.max()

    # ── Track map ─────────────────────────────────────────────────────────────

    def get_positions_at(
        self, time_delta: pd.Timedelta
    ) -> dict[str, tuple[float, float]]:
        """
        Return each car's interpolated (X, Y) position at time_delta.

        Uses binary search (searchsorted) to find the surrounding samples,
        then linearly interpolates between them for smooth 20 FPS movement.

        Args:
            time_delta: Time since session start (from the scrubber).

        Returns:
            dict mapping driver abbreviation → (x, y) in metres.
        """
        result = {}

        for driver_num, df in self._pos_data.items():
            abbr = self._num_to_abbr.get(driver_num)
            if not abbr:
                continue

            times = df["Time"]
            # Binary search — O(log n) vs idxmin()'s O(n)
            idx = times.searchsorted(time_delta)

            # Edge cases: before first sample or after last sample
            if idx <= 0:
                result[abbr] = (float(df["X"].iloc[0]), float(df["Y"].iloc[0]))
                continue
            if idx >= len(df):
                result[abbr] = (float(df["X"].iloc[-1]), float(df["Y"].iloc[-1]))
                continue

            # Surrounding samples
            t0, t1 = times.iloc[idx - 1], times.iloc[idx]
            x0, y0 = float(df["X"].iloc[idx - 1]), float(df["Y"].iloc[idx - 1])
            x1, y1 = float(df["X"].iloc[idx]),     float(df["Y"].iloc[idx])

            # TODO(human): compute alpha and interpolate x, y.
            # alpha is a float 0.0–1.0 representing how far time_delta is
            # between t0 and t1:
            #     alpha = (time_delta - t0) / (t1 - t0)
            # Then apply the lerp formula for both axes:
            #     x = x0 + alpha * (x1 - x0)
            #     y = y0 + alpha * (y1 - y0)
            # Finally: result[abbr] = (x, y)
            
            alpha = (time_delta - t0) / (t1 - t0)
            x = x0 + alpha * (x1 - x0)
            y = y0 + alpha * (y1 - y0)

            result[abbr] = (x, y)

        return result

    # ── Leaderboard ───────────────────────────────────────────────────────────

    def get_leaderboard_at(self, time_delta: pd.Timedelta) -> list[str]:
        """
        Return driver abbreviations in race order at the given time.

        Uses lap count + last known Position column from session.laps.
        Drivers who haven't started yet are placed at the back.
        """
        elapsed = self.session.t0_date + time_delta
        completed = self._laps[self._laps["LapStartDate"] <= elapsed].copy()

        if completed.empty:
            return list(self._num_to_abbr.values())

        # Latest lap per driver
        latest = (
            completed.sort_values("LapNumber")
            .groupby("Driver")
            .last()
            .reset_index()
        )
        ordered = latest.sort_values(
            ["LapNumber", "Position"], ascending=[False, True]
        )
        return ordered["Driver"].tolist()

    # ── Telemetry ─────────────────────────────────────────────────────────────

    def get_lap_data_for(
        self, driver_abbr: str, time_delta: pd.Timedelta
    ) -> LapData | None:
        """
        Return a LapData for driver_abbr's current lap at time_delta.

        Returns None if the driver has no lap data at that time.
        """
        elapsed = self.session.t0_date + time_delta
        driver_laps = self._laps[
            (self._laps["Driver"] == driver_abbr)
            & (self._laps["LapStartDate"] <= elapsed)
        ]

        if driver_laps.empty:
            return None

        current_lap = driver_laps.sort_values("LapNumber").iloc[-1]
        return LapData(current_lap)
