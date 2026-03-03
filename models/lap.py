"""
models/lap.py
─────────────
Wraps a single FastF1 Lap and exposes cleaned telemetry for plotting.

A FastF1 Lap is one row of session.laps — a pandas Series containing
metadata (LapTime, Driver, Compound, etc.) plus methods to fetch the
associated high-frequency telemetry (240 Hz position/channel data).

Telemetry channels available from FastF1:
  Speed     — km/h
  Throttle  — 0–100 (%)
  Brake     — bool (0 or 1)
  nGear     — 1–8
  DRS       — 0/8/10/12/14 (0 = off, >8 = open)
  RPM       — engine revolutions per minute
  X, Y      — GPS coordinates (metres, track-relative)
  Distance  — cumulative metres from lap start (added via add_distance())
"""

import pandas as pd
from fastf1.core import Lap


class LapData:
    """Wraps a FastF1 Lap and exposes cleaned telemetry for plotting."""

    def __init__(self, lap: Lap) -> None:
        self.lap = lap
        self.driver: str = lap["Driver"]
        self.lap_time = lap["LapTime"]

        # Fetch 240 Hz telemetry and compute distance along the track.
        # add_distance() integrates Speed over Time using the trapezoid rule
        # to produce a cumulative Distance column in metres.
        self._telemetry: pd.DataFrame = lap.get_telemetry().add_distance()

    @property
    def distance(self) -> pd.Series:
        """Cumulative track distance in metres — the shared x-axis for all plots."""
        return self._telemetry["Distance"]

    def get_telemetry_channels(self) -> dict[str, pd.Series]:
        """
        Return the telemetry channels to display in the UI.

        Each key becomes a plot panel label; each value is a Series
        aligned to self.distance as the x-axis.

        TODO(human): implement this method.
        Decide which channels to include and return them as a dict.
        Example shape:
            {
                "Speed (km/h)": <Series>,
                ...
            }
        """
        return {
            "Speed (km/h)": self._telemetry["Speed"],
            "Throttle (%)": self._telemetry["Throttle"],
            "Brake": self._telemetry["Brake"],
            "nGear (1-8)": self._telemetry["nGear"],
        }


