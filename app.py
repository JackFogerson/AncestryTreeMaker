"""Application entry coordination for Ancestor Tree Creator.

Feature behavior remains in the legacy controller during the first refactor
milestone. Subsequent milestones will move feature-specific collaborators out
of ``app_logic`` and into their dedicated packages.
"""

from __future__ import annotations

import tkinter as tk

from app_logic import AncestryApp


def create_application(root: tk.Tk | None = None) -> tuple[tk.Tk, AncestryApp]:
    """Create the Tk root and the current application controller."""
    application_root = root if root is not None else tk.Tk()
    return application_root, AncestryApp(application_root)


def run() -> None:
    """Run the desktop application."""
    root, _application = create_application()
    root.mainloop()
