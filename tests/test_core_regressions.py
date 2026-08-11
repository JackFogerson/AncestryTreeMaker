"""Regression coverage for extracted non-UI application behavior."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from genetics.inheritance import calculate_inheritance
from mapview.timeline import build_timeline_steps
from models import AncestorNode
from storage.json_io import load_tree_file, save_tree_file
from tree.layout import calculate_positions


class CoreRegressionTests(unittest.TestCase):
    def test_save_overwrites_and_reloads(self) -> None:
        tree = {"A": AncestorNode("A", base_ethnicities=["German"], signifiers=["Test"])}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tree.json"
            save_tree_file(path, tree, ["German"], {"German": "#123456"})
            tree["A"].display_name = "Updated"
            save_tree_file(path, tree, ["German"], {"German": "#123456"})
            loaded, options, colors = load_tree_file(path)

        self.assertEqual("Updated", loaded["A"].display_name)
        self.assertEqual(["German"], options)
        self.assertEqual("#123456", colors["German"])

    def test_two_parent_inheritance(self) -> None:
        tree = {
            "Child": AncestorNode("Child", father="Father", mother="Mother"),
            "Father": AncestorNode("Father", base_ethnicities=["German"]),
            "Mother": AncestorNode("Mother", base_ethnicities=["English"]),
        }
        calculate_inheritance(tree)
        self.assertEqual({"German": 50.0, "English": 50.0}, tree["Child"].computed_ethnicities)

    def test_legacy_save_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "legacy.json"
            path.write_text('{"nodes": {"A": {"name": "A"}}}', encoding="utf-8")
            tree, options, colors = load_tree_file(path)

        self.assertEqual([], options)
        self.assertEqual({}, colors)
        self.assertEqual([], tree["A"].signifiers)

    def test_tree_layout_and_timeline(self) -> None:
        tree = {
            "Child": AncestorNode("Child", father="Father", mother="Mother"),
            "Father": AncestorNode("Father", birth_year="1900", locations=[{"year": 1901, "lat": 1, "lon": 2}]),
            "Mother": AncestorNode("Mother"),
        }
        positions = calculate_positions(tree, None)
        timeline, minimum, maximum = build_timeline_steps(tree)

        self.assertEqual(set(tree), set(positions))
        self.assertLess(positions["Father"][1], positions["Child"][1])
        self.assertEqual((1900, 1901), (minimum, maximum))
        self.assertEqual([(1900, 1), (1901, 1)], timeline)


if __name__ == "__main__":
    unittest.main()
