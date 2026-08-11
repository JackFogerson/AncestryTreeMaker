"""Canvas rendering for the ancestor tree.

This module deliberately receives calculated positions and ethnicity values.
It does not calculate layout, mutate genealogy data, or handle click events.
"""

from __future__ import annotations

import math
import tkinter as tk
from collections.abc import Mapping

from models import AncestorNode


class TreeRenderer:
    """Draw the ancestor tree onto a Tkinter canvas."""

    PIE_RADIUS = 35.0
    PARENT_CONNECTOR_COLOR = "#10b981"
    SINGLE_PARENT_CONNECTOR_COLOR = "#94a3b8"

    def render(
        self,
        canvas: tk.Canvas,
        tree: Mapping[str, AncestorNode],
        positions: Mapping[str, tuple[float, float]],
        ethnicity_colors: Mapping[str, str],
        show_decorations: bool,
        canvas_scale: float,
        pan_x: float,
        pan_y: float,
    ) -> None:
        """Clear and redraw the complete tree using already-derived data."""
        canvas.delete("all")
        self._draw_connectors(canvas, tree, positions)
        self._draw_nodes(canvas, tree, positions, ethnicity_colors, show_decorations)
        self._apply_view_transform(canvas, canvas_scale, pan_x, pan_y)

    def _draw_connectors(
        self,
        canvas: tk.Canvas,
        tree: Mapping[str, AncestorNode],
        positions: Mapping[str, tuple[float, float]],
    ) -> None:
        for name, node in tree.items():
            if name not in positions:
                continue

            x, y = positions[name]
            has_father = node.father in positions
            has_mother = node.mother in positions

            if has_father and has_mother:
                father_x, father_y = positions[node.father]
                mother_x, mother_y = positions[node.mother]
                midpoint_y = y - 250.0

                canvas.create_line(x, y, x, midpoint_y, fill=self.PARENT_CONNECTOR_COLOR, width=3)
                canvas.create_line(father_x, midpoint_y, mother_x, midpoint_y, fill=self.PARENT_CONNECTOR_COLOR, width=3)
                canvas.create_line(father_x, midpoint_y, father_x, father_y, fill=self.PARENT_CONNECTOR_COLOR, width=3)
                canvas.create_line(mother_x, midpoint_y, mother_x, mother_y, fill=self.PARENT_CONNECTOR_COLOR, width=3)
            elif has_father:
                father_x, father_y = positions[node.father]
                canvas.create_line(x, y, father_x, father_y, fill=self.SINGLE_PARENT_CONNECTOR_COLOR, width=2)
            elif has_mother:
                mother_x, mother_y = positions[node.mother]
                canvas.create_line(x, y, mother_x, mother_y, fill=self.SINGLE_PARENT_CONNECTOR_COLOR, width=2)

    def _draw_nodes(
        self,
        canvas: tk.Canvas,
        tree: Mapping[str, AncestorNode],
        positions: Mapping[str, tuple[float, float]],
        ethnicity_colors: Mapping[str, str],
        show_decorations: bool,
    ) -> None:
        for name, (x, y) in positions.items():
            node = tree[name]
            chart_tag = f"pie_click:{name}"

            self._draw_pie_chart(canvas, x, y, self.PIE_RADIUS, node.computed_ethnicities, ethnicity_colors)
            canvas.create_oval(
                x - self.PIE_RADIUS,
                y - self.PIE_RADIUS,
                x + self.PIE_RADIUS,
                y + self.PIE_RADIUS,
                fill="",
                outline="",
                tags=(chart_tag, "interactive", "pie"),
            )

            if show_decorations:
                self._draw_node_decorations(canvas, name, node, x, y)

    def _draw_pie_chart(
        self,
        canvas: tk.Canvas,
        x: float,
        y: float,
        radius: float,
        ethnicities: Mapping[str, float],
        ethnicity_colors: Mapping[str, str],
    ) -> None:
        active_ethnicities = {name: value for name, value in ethnicities.items() if value > 0}
        if not active_ethnicities:
            canvas.create_oval(x - radius, y - radius, x + radius, y + radius, fill="#e2e8f0", outline="#cbd5e1", width=1)
            return

        sorted_ethnicities = sorted(active_ethnicities.items(), key=lambda item: item[1], reverse=True)
        largest_ethnicity, _largest_value = sorted_ethnicities[0]
        base_color = self._ethnicity_color(largest_ethnicity, ethnicity_colors)
        canvas.create_oval(x - radius, y - radius, x + radius, y + radius, fill=base_color, outline="#cbd5e1", width=1)

        if len(active_ethnicities) == 1:
            return

        total = sum(active_ethnicities.values())
        current_angle = 0.0
        for ethnicity, value in active_ethnicities.items():
            extent = (value / total) * 360.0
            if ethnicity != largest_ethnicity:
                points = [x, y]
                steps = max(4, int(extent / 3))
                for step in range(steps + 1):
                    angle = current_angle + (extent * step / steps)
                    radians = math.radians(angle)
                    points.extend((x + radius * math.cos(radians), y - radius * math.sin(radians)))
                canvas.create_polygon(points, fill=self._ethnicity_color(ethnicity, ethnicity_colors), outline="#ffffff", width=0.5)
            current_angle += extent

    @staticmethod
    def _ethnicity_color(ethnicity: str, ethnicity_colors: Mapping[str, str]) -> str:
        return "#e2e8f0" if ethnicity == "Unknown" else ethnicity_colors.get(ethnicity, "#e2e8f0")

    def _draw_node_decorations(self, canvas: tk.Canvas, name: str, node: AncestorNode, x: float, y: float) -> None:
        text_y = y + self.PIE_RADIUS + 14.0
        node_items: list[int] = []

        name_label = canvas.create_text(
            x,
            text_y,
            text=self.format_split_name(node.display_name),
            font=("Arial", 13, "bold"),
            fill="#0f172a",
            justify=tk.CENTER,
            tags=("node_name",),
        )
        node_items.append(name_label)
        name_bounds = canvas.bbox(name_label)
        current_y = name_bounds[3] + 4 if name_bounds else text_y + 20

        if node.signifiers:
            signifier_label = canvas.create_text(
                x,
                current_y,
                text=", ".join(node.signifiers),
                font=("Arial", 11, "italic"),
                fill="#475569",
                justify=tk.CENTER,
                tags=("node_sig",),
            )
            node_items.append(signifier_label)
            signifier_bounds = canvas.bbox(signifier_label)
            current_y = signifier_bounds[3] + 4 if signifier_bounds else current_y + 16

        if node.birth_year or node.death_year or node.is_living:
            birth = node.birth_year or "?"
            death = "Present" if node.is_living else (node.death_year or "?")
            year_label = canvas.create_text(
                x,
                current_y,
                text=f"({birth} - {death})",
                font=("Arial", 10),
                fill="#64748b",
                justify=tk.CENTER,
                tags=("node_years",),
            )
            node_items.append(year_label)

        self._draw_label_background(canvas, node_items)
        self._draw_parent_button(canvas, name, x, y)

    @staticmethod
    def format_split_name(name: str) -> str:
        """Split a name before its surname, preserving conventional suffixes."""
        words = name.strip().split()
        if not words:
            return ""
        if len(words) == 1:
            return words[0]

        suffixes = {"jr", "jr.", "sr", "sr.", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x", "2nd", "3rd", "4th"}
        surname_index = len(words) - 1
        while surname_index >= 0 and words[surname_index].lower().strip(",.") in suffixes:
            surname_index -= 1
        if surname_index <= 0:
            surname_index = len(words) - 1
        return f"{' '.join(words[:surname_index])}\n{' '.join(words[surname_index:])}"

    @staticmethod
    def _draw_label_background(canvas: tk.Canvas, item_ids: list[int]) -> None:
        if not item_ids:
            return

        x1, y1, x2, y2 = canvas.bbox(item_ids[0])
        for item_id in item_ids[1:]:
            item_x1, item_y1, item_x2, item_y2 = canvas.bbox(item_id)
            x1 = min(x1, item_x1)
            y1 = min(y1, item_y1)
            x2 = max(x2, item_x2)
            y2 = max(y2, item_y2)
        background = canvas.create_rectangle(x1 - 6, y1 - 4, x2 + 6, y2 + 4, fill="#ffffff", outline="#cbd5e1", width=1)
        canvas.tag_lower(background, item_ids[0])

    def _draw_parent_button(self, canvas: tk.Canvas, name: str, x: float, y: float) -> None:
        plus_tag = f"plus_click:{name}"
        plus_y = y - self.PIE_RADIUS - 15.0
        canvas.create_rectangle(
            x - 8,
            plus_y - 8,
            x + 8,
            plus_y + 8,
            fill="#10b981",
            outline="#047857",
            tags=(plus_tag, "interactive", "plus"),
        )
        canvas.create_text(x, plus_y, text="+", font=("Arial", 13, "bold"), fill="white", tags=(plus_tag, "interactive", "plus_text"))

    @staticmethod
    def _apply_view_transform(canvas: tk.Canvas, canvas_scale: float, pan_x: float, pan_y: float) -> None:
        canvas.scale("all", 0, 0, canvas_scale, canvas_scale)
        canvas.move("all", pan_x, pan_y)

        canvas.itemconfig("node_name", font=("Arial", max(1, int(13 * canvas_scale)), "bold"))
        canvas.itemconfig("node_sig", font=("Arial", max(1, int(11 * canvas_scale)), "italic"))
        canvas.itemconfig("node_years", font=("Arial", max(1, int(10 * canvas_scale)), ""))
        canvas.itemconfig("plus_text", font=("Arial", max(1, int(13 * canvas_scale)), "bold"))
