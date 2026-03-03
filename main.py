"""
main.py
────────
Application entry point.

Wires together:
  QApplication  — Qt event loop
  MainWindow    — the dashboard UI
  SessionLoaderWorker — background session fetch

Edit YEAR, ROUND_ID, SESSION_TYPE to load a different race.
"""

import sys
from PySide6.QtWidgets import QApplication, QMessageBox

from views.main_window import MainWindow
from controllers.session_loader import SessionLoaderWorker

# ── Race to load ──────────────────────────────────────────────────────────────
YEAR         = 2023
ROUND_ID     = "Bahrain"
SESSION_TYPE = "R"          # R=Race, Q=Qualifying, FP1/FP2/FP3=Practice


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    # Start background session load
    loader = SessionLoaderWorker(
        year=YEAR,
        round_id=ROUND_ID,
        session_type=SESSION_TYPE,
    )
    loader.session_loaded.connect(window.load_race)
    loader.load_failed.connect(lambda msg: _show_error(window, msg))
    loader.start()

    sys.exit(app.exec())


def _show_error(parent, message: str) -> None:
    QMessageBox.critical(parent, "Failed to load session", message)


if __name__ == "__main__":
    main()
