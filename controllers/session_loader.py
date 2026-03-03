"""
controllers/session_loader.py
──────────────────────────────
Background QThread worker — loads a FastF1 session without blocking the UI.

Why a background thread?
  session.load() downloads ~100 MB of timing + telemetry data and can take
  5–20 seconds. Running it on the main thread freezes the Qt event loop,
  making the window unresponsive. QThread keeps the UI live while data loads.

Signal flow:
  main thread                        worker thread
  ───────────                        ─────────────
  SessionLoaderWorker(...)
  loader.start()          ────────▶  run()
                                       load_session(...)
  load_race(session)  ◀────────────    session_loaded.emit(session)
     (or)
  show_error(msg)     ◀────────────    load_failed.emit(msg)
"""

import fastf1.core
from PySide6.QtCore import QThread, Signal

from models.session import load_session


class SessionLoaderWorker(QThread):
    """Fetches and parses a FastF1 session on a background thread."""

    # Emitted on success — delivers the loaded session to the main thread
    session_loaded = Signal(object)

    # Emitted on failure — delivers a human-readable error message
    load_failed = Signal(str)

    def __init__(
        self,
        year: int,
        round_id: int | str,
        session_type: str = "R",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._year         = year
        self._round_id     = round_id
        self._session_type = session_type

    def run(self) -> None:
        """
        Entry point for the background thread.

        Called automatically by Qt when loader.start() is invoked.
        Must emit either session_loaded or load_failed before returning —
        the main thread is waiting on one of these signals.

        TODO(human): implement this method.
        Guidance:
          - Call load_session(self._year, self._round_id, self._session_type)
          - On success:  emit self.session_loaded with the returned session
          - On failure:  catch the Exception and emit self.load_failed
                         with str(e) so the UI can show the error message
          - Never touch any UI object here — only emit signals
        """
      

        try:
            session = load_session(self._year, self._round_id, self._session_type)
            self.session_loaded.emit(session)
        except Exception as e:
            self.load_failed.emit(str(e))
    
        
