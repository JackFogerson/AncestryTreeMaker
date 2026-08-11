"""Tkinter canvas interaction helpers for the tree view."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable


def handle_press(
    canvas: tk.Canvas,
    event: tk.Event,
    open_parent: Callable[[str], None],
    open_profile: Callable[[str], None],
) -> tuple[int, int] | None:
    """Dispatch a node click or return the starting point for panning."""
    canvas_x, canvas_y = canvas.canvasx(event.x), canvas.canvasy(event.y)
    clicked_items = canvas.find_overlapping(canvas_x - 1, canvas_y - 1, canvas_x + 1, canvas_y + 1)
    if clicked_items:
        for tag in canvas.gettags(clicked_items[-1]):
            if tag.startswith("plus_click:"):
                open_parent(tag.split(":", 1)[1])
                return None
            if tag.startswith("pie_click:"):
                open_profile(tag.split(":", 1)[1])
                return None
    return event.x, event.y


def handle_drag(canvas: tk.Canvas, event: tk.Event, drag_start: tuple[int, int]) -> tuple[int, int, int, int]:
    """Pan the rendered tree and return its new start point and displacement."""
    dx, dy = event.x - drag_start[0], event.y - drag_start[1]
    canvas.move("all", dx, dy)
    return event.x, event.y, dx, dy


def handle_zoom(canvas: tk.Canvas, event: tk.Event, scale: float, pan_x: float, pan_y: float) -> tuple[float, float, float]:
    """Zoom around the cursor and keep text sizes synchronized."""
    factor = 1.1 if (event.num == 4 or event.delta > 0) else 0.9
    center_x, center_y = canvas.canvasx(event.x), canvas.canvasy(event.y)
    pan_x = pan_x * factor + center_x * (1.0 - factor)
    pan_y = pan_y * factor + center_y * (1.0 - factor)
    scale *= factor
    canvas.scale("all", center_x, center_y, factor, factor)
    canvas.itemconfig("node_name", font=("Arial", max(1, int(13 * scale)), "bold"))
    canvas.itemconfig("node_sig", font=("Arial", max(1, int(11 * scale)), "italic"))
    canvas.itemconfig("node_years", font=("Arial", max(1, int(10 * scale)), ""))
    canvas.itemconfig("plus_text", font=("Arial", max(1, int(13 * scale)), "bold"))
    return scale, pan_x, pan_y
