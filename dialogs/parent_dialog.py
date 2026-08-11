"""Dialog for linking an ancestor's parents."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable, MutableMapping

from models import AncestorNode


def open_parent_dialog(
    root: tk.Misc,
    tree: MutableMapping[str, AncestorNode],
    person_name: str,
    on_saved: Callable[[], None],
) -> None:
    """Open the existing parent-linking workflow without calculating ancestry."""
    dialog = tk.Toplevel(root)
    dialog.title(f"Link Parents: {person_name}")
    dialog.geometry("450x350")
    dialog.transient(root)
    dialog.grab_set()
    node = tree[person_name]

    tk.Label(dialog, text="Link Family Network For:", font=("Arial", 10)).pack(pady=(12, 2))
    tk.Label(dialog, text=node.display_name, font=("Arial", 14, "bold"), fg="#047857").pack(pady=(0, 12))

    def parent_entry(title: str, parent_id: str | None) -> tk.Entry:
        group = tk.LabelFrame(dialog, text=title, font=("Arial", 10, "bold"), padx=10, pady=10)
        group.pack(fill=tk.X, padx=20, pady=10)
        tk.Label(group, text="Full Name:", font=("Arial", 9, "bold")).pack(side=tk.LEFT)
        entry = tk.Entry(group, font=("Arial", 10), width=28)
        entry.pack(side=tk.LEFT, padx=10)
        parent = tree.get(parent_id) if parent_id else None
        entry.insert(0, parent.display_name if parent else (parent_id or ""))
        return entry

    father_entry = parent_entry(" Father ", node.father)
    mother_entry = parent_entry(" Mother ", node.mother)

    def save() -> None:
        _set_parent(tree, node, father_entry.get().strip(), is_father=True)
        _set_parent(tree, node, mother_entry.get().strip(), is_father=False)
        dialog.destroy()
        on_saved()

    tk.Button(dialog, text="Link Ancestors", command=save, bg="#3b82f6", fg="white", font=("Arial", 10, "bold")).pack(pady=15)


def _set_parent(tree: MutableMapping[str, AncestorNode], node: AncestorNode, parent_id: str, *, is_father: bool) -> None:
    current_id = node.father if is_father else node.mother
    if not parent_id:
        if is_father:
            node.father = None
        else:
            node.mother = None
        return
    if current_id == parent_id:
        return
    if parent_id not in tree:
        tree[parent_id] = AncestorNode(name=parent_id, display_name=parent_id)
    if is_father:
        node.father = parent_id
    else:
        node.mother = parent_id
