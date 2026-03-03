"""
models/session.py
─────────────────
Thin wrapper around FastF1's session loading.

FastF1 identifies sessions by:
  - year           : int  (e.g. 2023)
  - round_id       : int | str  (e.g. 5 or "Monaco")
  - session_type   : str  — one of:
        "FP1" | "FP2" | "FP3" | "Q" | "S" | "SS" | "R"
        (Practice 1-3, Qualifying, Sprint, Sprint Shootout, Race)
"""

import fastf1
from pathlib import Path

CACHE_DIR = Path(__file__).parent.parent / "cache"


def _enable_cache() -> None:
    """Point FastF1 at our local cache directory."""
    fastf1.Cache.enable_cache(str(CACHE_DIR))


def load_session(
    year: int,
    round_id: int | str,
    session_type: str = "R",
) -> fastf1.core.Session:
    """
    Load a FastF1 session with telemetry data.

    First call downloads ~50-100 MB and caches locally.
    Subsequent calls load from disk in seconds.

    Args:
        year:         Season year (e.g. 2023)
        round_id:     Round number or GP name (e.g. 5 or "Monaco")
        session_type: Session code — default "R" (Race)

    Returns:
        A fully loaded fastf1.core.Session with laps + telemetry.

    Example:
        >>> session = load_session(2023, "Bahrain", "Q")
        >>> fastest = session.laps.pick_fastest()
    """
    _enable_cache()
    session = fastf1.get_session(year, round_id, session_type)
    session.load()
    return session
