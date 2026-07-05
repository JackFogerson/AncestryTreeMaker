import tkinter as tk
from tkinter import messagebox, filedialog, colorchooser
import json
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class AncestorNode:
    def __init__(self, name, base_ethnicities=None, father=None, mother=None):
        self.name = name
        self.base_ethnicities = base_ethnicities if base_ethnicities else []
        self.father = father  
        self.mother = mother  
        self.computed_ethnicities = {}

class AncestryApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Interactive Ancestry Pie-Chart Tree")
        self.root.geometry("1200x800")
        
        self.ethnicity_options = []
        self.ethnicity_colors = {} 
        
        self.tree = {}  
        self.plus_buttons = {}  
        self.pie_centers = {} 
        
        self.is_dragging = False
        self.press_x = None
        self.press_y = None
        
        self.setup_ui()
        self.initialize_default_tree()
        
    def initialize_default_tree(self):
        if not self.tree:
            self.tree["Jack Fogerson"] = AncestorNode("Jack Fogerson")
            self.refresh_plot()

    def setup_ui(self):
        control_panel = tk.Frame(self.root, width=250, padx=15, pady=15, bg="#f8fafc")
        control_panel.pack(side=tk.LEFT, fill=tk.Y)
        
        tk.Label(control_panel, text="File Actions", font=("Arial", 14, "bold"), bg="#f8fafc", fg="#1e293b").pack(anchor=tk.W, pady=(0,15))
        
        tk.Button(control_panel, text="Save Tree JSON", command=self.save_tree, bg="#2196F3", fg="white", font=("Arial", 10, "bold"), height=2).pack(fill=tk.X, pady=6)
        tk.Button(control_panel, text="Load Tree JSON", command=self.load_tree, bg="#FF9800", fg="white", font=("Arial", 10, "bold"), height=2).pack(fill=tk.X, pady=6)
        tk.Button(control_panel, text="Clear Tree", command=self.clear_tree, bg="#f44336", fg="white", font=("Arial", 10, "bold"), height=2).pack(fill=tk.X, pady=6)
        
        self.plot_panel = tk.Frame(self.root, bg="white")
        self.plot_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.fig, self.ax = plt.subplots(figsize=(8, 8))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_panel)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        self.fig.canvas.mpl_connect('button_press_event', self.on_press)
        self.fig.canvas.mpl_connect('button_release_event', self.on_release)
        self.fig.canvas.mpl_connect('motion_notify_event', self.on_drag)
        self.fig.canvas.mpl_connect('scroll_event', self.on_zoom)

    def calculate_inheritance(self):
        for node in self.tree.values():
            node.computed_ethnicities = {}

        roots = []
        for name, node in self.tree.items():
            if not node.father and not node.mother:
                roots.append(name)
                
        if not roots and self.tree:
            roots = [list(self.tree.keys())[0]]

        for root_name in roots:
            self._compute_node_heritage(root_name, visited=set())

    def _compute_node_heritage(self, name, visited):
        if name in visited or name not in self.tree:
            return
        visited.add(name)
        
        node = self.tree[name]
        
        if node.father or node.mother:
            if node.father:
                self._compute_node_heritage(node.father, visited)
            if node.mother:
                self._compute_node_heritage(node.mother, visited)
                
            father_dna = self.tree[node.father].computed_ethnicities if node.father and node.father in self.tree else {"Unknown": 100.0}
            mother_dna = self.tree[node.mother].computed_ethnicities if node.mother and node.mother in self.tree else {"Unknown": 100.0}
            
            combined = {}
            for eth, pct in father_dna.items():
                combined[eth] = combined.get(eth, 0.0) + (pct * 0.5)
            for eth, pct in mother_dna.items():
                combined[eth] = combined.get(eth, 0.0) + (pct * 0.5)
                
            node.computed_ethnicities = combined
        else:
            if node.base_ethnicities:
                count = len(node.base_ethnicities)
                for eth in node.base_ethnicities:
                    node.computed_ethnicities[eth] = 100.0 / count
            else:
                node.computed_ethnicities = {"Unknown": 100.0}

        for child_name, child_node in self.tree.items():
            if child_node.father == name or child_node.mother == name:
                self._compute_node_heritage(child_name, visited.copy())

    def calculate_positions(self):
        positions = {}
        if not self.tree:
            return positions
            
        children_names = set()
        for node in self.tree.values():
            if node.father: children_names.add(node.father)
            if node.mother: children_names.add(node.mother)
            
        roots = [name for name in self.tree if name not in children_names]
        if not roots:  
            roots = [list(self.tree.keys())[0]]
            
        def assign_coords(node_name, x, y, horizontal_spacing):
            if node_name not in self.tree or node_name in positions:
                return
            positions[node_name] = (x, y)
            
            node = self.tree[node_name]
            # Space out parents cleanly centered above the child node point
            if node.father:
                assign_coords(node.father, x - horizontal_spacing, y + 2.0, horizontal_spacing / 1.7)
            if node.mother:
                assign_coords(node.mother, x + horizontal_spacing, y + 2.0, horizontal_spacing / 1.7)

        for i, root in enumerate(roots):
            assign_coords(root, x=i * 8.0, y=0, horizontal_spacing=3.0)
            
        return positions

    def refresh_plot(self):
        cur_xlim = self.ax.get_xlim() if self.press_x is not None else None
        cur_ylim = self.ax.get_ylim() if self.press_x is not None else None

        self.calculate_inheritance()  
        self.ax.clear()
        self.ax.set_title("Traditional Orthogonal Bracket Layout | Drag Background to Pan | Scroll to Zoom", fontsize=11, weight='bold', pad=10)
        self.ax.axis('off')
        
        positions = self.calculate_positions()
        self.plus_buttons.clear()
        self.pie_centers.clear()
        
        if not positions:
            self.canvas.draw()
            return

        # Upgraded Orthogonal/Square Bracket Line Tracing Engine matching image_003f7b.jpg
        for name, node in self.tree.items():
            if name in positions:
                x, y = positions[name]
                has_father = node.father in positions
                has_mother = node.mother in positions
                
                # Case 1: Both parents present (Construct classic horizontal bridging bar with center dropdown stem)
                if has_father and has_mother:
                    fx, fy = positions[node.father]
                    mx, my = positions[node.mother]
                    
                    mid_y = y + 1.0  # Sideways horizontal split height
                    
                    # Vertical stem straight out of child up to the horizontal bracket line
                    self.ax.plot([x, x], [y, mid_y], color='#10b981', linestyle='-', linewidth=2.5, zorder=1, clip_on=False)
                    # Horizontal bridging line tracking parent span bounds
                    self.ax.plot([fx, mx], [mid_y, mid_y], color='#10b981', linestyle='-', linewidth=2.5, zorder=1, clip_on=False)
                    # Verticals dropping directly down out of father and mother nodes to meet the bridge line
                    self.ax.plot([fx, fx], [fy, mid_y], color='#10b981', linestyle='-', linewidth=2.5, zorder=1, clip_on=False)
                    self.ax.plot([mx, mx], [my, mid_y], color='#10b981', linestyle='-', linewidth=2.5, zorder=1, clip_on=False)
                    
                # Case 2: Only one parent exists (Clean orthogonal linear straight path layout)
                elif has_father:
                    fx, fy = positions[node.father]
                    self.ax.plot([x, fx], [y, fy], color='#94a3b8', linestyle='-', linewidth=2, zorder=1, clip_on=False)
                elif has_mother:
                    mx, my = positions[node.mother]
                    self.ax.plot([x, mx], [y, my], color='#94a3b8', linestyle='-', linewidth=2, zorder=1, clip_on=False)

        for name, (x, y) in positions.items():
            node = self.tree[name]
            size = 0.55  
            
            inset_ax = self.ax.inset_axes([x - size/2, y - size/2, size, size], transform=self.ax.transData)
            inset_ax.zorder = 2
            
            if node.computed_ethnicities:
                labels = [f"{k}\n{v:.2f}%" for k, v in node.computed_ethnicities.items()]
                values = list(node.computed_ethnicities.values())
                pie_colors = [self.ethnicity_colors.get(k, '#e2e8f0') for k in node.computed_ethnicities.keys()]
                inset_ax.pie(values, labels=labels, colors=pie_colors, textprops={'fontsize': 6, 'weight': 'bold'}, radius=1.0)
            else:
                inset_ax.pie([1], colors=['#e2e8f0'], radius=1.0)
                inset_ax.text(0, 0, "Unknown\n100.00%", ha='center', va='center', fontsize=7, color='#64748b', weight='bold')
                
            inset_ax.axis('equal')
            
            self.ax.text(x, y - (size / 1.5), name, ha='center', va='top', 
                         fontsize=9, weight='bold',
                         bbox=dict(boxstyle='round,pad=0.3', facecolor='#ffffff', edgecolor='#cbd5e1', alpha=0.95))
            
            plus_y = y + (size / 1.5)
            self.ax.text(x, plus_y, " + ", ha='center', va='center', 
                         fontsize=10, weight='bold', color='white',
                         bbox=dict(boxstyle='circle,pad=0.2', facecolor='#10b981', edgecolor='#047857', alpha=1.0))
            
            self.plus_buttons[name] = (x, plus_y)
            self.pie_centers[name] = (x, y, size / 2.0)

        if cur_xlim and cur_ylim:
            self.ax.set_xlim(cur_xlim)
            self.ax.set_ylim(cur_ylim)
        else:
            all_x = [pt[0] for pt in positions.values()]
            all_y = [pt[1] for pt in positions.values()]
            self.ax.set_xlim(min(all_x) - 3.0, max(all_x) + 3.0)
            self.ax.set_ylim(min(all_y) - 1.5, max(all_y) + 2.5)
        
        self.canvas.draw()

    def on_press(self, event):
        if event.xdata is None or event.ydata is None:
            return
            
        click_radius = 0.25
        for name, (bx, by) in self.plus_buttons.items():
            if ((event.xdata - bx)**2 + (event.ydata - by)**2)**0.5 <= click_radius:
                self.open_parent_dialog(name)
                return

        for name, (px, py, pradius) in self.pie_centers.items():
            if ((event.xdata - px)**2 + (event.ydata - py)**2)**0.5 <= pradius:
                self.display_ethnic_breakdown(name)
                return

        if event.button == 1:
            self.is_dragging = True
            self.press_x = event.xdata
            self.press_y = event.ydata

    def on_drag(self, event):
        if not self.is_dragging or event.xdata is None or event.ydata is None:
            return
        dx = self.press_x - event.xdata
        dy = self.press_y - event.ydata
        
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        
        self.ax.set_xlim(xlim[0] + dx, xlim[1] + dx)
        self.ax.set_ylim(ylim[0] + dy, ylim[1] + dy)
        self.canvas.draw()

    def on_release(self, event):
        self.is_dragging = False

    def on_zoom(self, event):
        if event.xdata is None or event.ydata is None:
            return
        zoom_factor = 0.85 if event.button == 'up' else 1.15
        
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        
        new_width = (xlim[1] - xlim[0]) * zoom_factor
        new_height = (ylim[1] - ylim[0]) * zoom_factor
        
        rel_x = (event.xdata - xlim[0]) / (xlim[1] - xlim[0])
        rel_y = (event.ydata - ylim[0]) / (ylim[1] - ylim[0])
        
        self.ax.set_xlim(event.xdata - rel_x * new_width, event.xdata + (1 - rel_x) * new_width)
        self.ax.set_ylim(event.ydata - rel_y * new_height, event.ydata + (1 - rel_y) * new_height)
        self.canvas.draw()

    def display_ethnic_breakdown(self, person_name):
        node = self.tree[person_name]
        breakdown_window = tk.Toplevel(self.root)
        breakdown_window.title(f"Composition Breakdown: {person_name}")
        breakdown_window.geometry("380x450")
        breakdown_window.configure(bg="#f8fafc")
        breakdown_window.transient(self.root)
        
        tk.Label(breakdown_window, text=person_name, font=("Arial", 16, "bold"), fg="#1e293b", bg="#f8fafc").pack(pady=(20, 5))
        tk.Label(breakdown_window, text="Inherited Ancestry Composition", font=("Arial", 10, "italic"), fg="#64748b", bg="#f8fafc").pack(pady=(0, 15))
        
        frame_list = tk.Frame(breakdown_window, bg="white", bd=1, relief=tk.SOLID, padx=15, pady=15)
        frame_list.pack(fill=tk.BOTH, expand=True, padx=25, pady=(0, 25))
        
        data = node.computed_ethnicities or {"Unknown": 100.0}
        
        unknown_val = data.get("Unknown", None)
        valid_items = [(k, v) for k, v in data.items() if k != "Unknown"]
        valid_items.sort(key=lambda item: item[1], reverse=True)
        
        sorted_list = valid_items
        if unknown_val is not None:
            sorted_list.append(("Unknown", unknown_val))
            
        for eth, pct in sorted_list:
            if pct <= 0:
                continue
            row = tk.Frame(frame_list, bg="white", pady=6)
            row.pack(fill=tk.X)
            
            color_hex = self.ethnicity_colors.get(eth, "#cbd5e1")
            color_chip = tk.Frame(row, width=14, height=14, bg=color_hex, bd=1, relief=tk.SOLID)
            color_chip.pack(side=tk.LEFT, padx=(0, 10))
            color_chip.pack_propagate(False)
            
            tk.Label(row, text=eth, font=("Arial", 11, "bold" if eth != "Unknown" else "normal"), fg="#334155" if eth != "Unknown" else "#64748b", bg="white").pack(side=tk.LEFT)
            tk.Label(row, text=f"{pct:.2f}%", font=("Arial", 11, "bold"), fg="#0f172a", bg="white").pack(side=tk.RIGHT)

    def open_parent_dialog(self, person_name):
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Manage Profile: {person_name}")
        dialog.geometry("520x660")
        dialog.transient(self.root)
        dialog.grab_set()
        
        node = self.tree[person_name]
        
        tk.Label(dialog, text=f"Editing Family Network for:", font=("Arial", 10)).pack(pady=(12,2))
        tk.Label(dialog, text=person_name, font=("Arial", 14, "bold"), fg="#047857").pack(pady=(0,12))
        
        tk.Label(dialog, text="Father's Full Name:", font=("Arial", 10, "bold")).pack(anchor=tk.W, padx=30)
        f_entry = tk.Entry(dialog, width=40, font=("Arial", 10))
        f_entry.insert(0, node.father or "")
        f_entry.pack(padx=30, pady=(0, 10))
        
        tk.Label(dialog, text="Mother's Full Name:", font=("Arial", 10, "bold")).pack(anchor=tk.W, padx=30)
        m_entry = tk.Entry(dialog, width=40, font=("Arial", 10))
        m_entry.insert(0, node.mother or "")
        m_entry.pack(padx=30, pady=(0, 12))
        
        custom_frame = tk.Frame(dialog)
        custom_frame.pack(fill=tk.X, padx=30, pady=(0, 10))
        tk.Label(custom_frame, text="Add New Ethnicity:", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        new_eth_entry = tk.Entry(custom_frame, width=15, font=("Arial", 10))
        new_eth_entry.pack(side=tk.LEFT, padx=5)
        
        tk.Label(dialog, text="Select Origins (Only applies if parents are left blank):", font=("Arial", 10, "bold")).pack(anchor=tk.W, padx=30, pady=(0,3))
        
        checkbox_frame = tk.LabelFrame(dialog, text=" Custom Palette Options (Click color block to edit) ", padx=10, pady=10)
        checkbox_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=(0,10))
        
        vars_dict = {}
        
        def pick_edit_color(ethnicity):
            current_clr = self.ethnicity_colors.get(ethnicity, "#cbd5e1")
            color_code = colorchooser.askcolor(initialcolor=current_clr, title=f"Choose Color for {ethnicity}")
            if color_code[1]:
                self.ethnicity_colors[ethnicity] = color_code[1]
                render_checkboxes()

        def render_checkboxes():
            for widget in checkbox_frame.winfo_children():
                widget.destroy()
            vars_dict.clear()
            
            for idx, ethnicity in enumerate(self.ethnicity_options):
                var = tk.BooleanVar(value=(ethnicity in node.base_ethnicities))
                vars_dict[ethnicity] = var
                
                row_idx = idx // 2
                col_idx = (idx % 2) * 2
                
                cb = tk.Checkbutton(checkbox_frame, text=ethnicity, variable=var, font=("Arial", 9))
                cb.grid(row=row_idx, column=col_idx, sticky=tk.W, padx=(5,2), pady=3)
                
                clr = self.ethnicity_colors.get(ethnicity, "#cbd5e1")
                lbl_color = tk.Label(checkbox_frame, bg=clr, width=3, relief=tk.RAISED, cursor="hand2")
                lbl_color.grid(row=row_idx, column=col_idx+1, sticky=tk.W, padx=(0,15))
                lbl_color.bind("<Button-1>", lambda e, eth=ethnicity: pick_edit_color(eth))

        def add_custom_ethnicity():
            new_eth = new_eth_entry.get().strip().title()
            if new_eth and new_eth not in self.ethnicity_options:
                color_code = colorchooser.askcolor(title=f"Assign Base Color for {new_eth}")
                assigned_color = color_code[1] if color_code[1] else "#cbd5e1"
                
                self.ethnicity_options.append(new_eth)
                self.ethnicity_colors[new_eth] = assigned_color
                new_eth_entry.delete(0, tk.END)
                render_checkboxes()
            elif new_eth in self.ethnicity_options:
                messagebox.showwarning("Notice", f"'{new_eth}' is already an option.")

        tk.Button(custom_frame, text="Add & Color", command=add_custom_ethnicity, bg="#cbd5e1", font=("Arial", 9, "bold")).pack(side=tk.LEFT)
        render_checkboxes()

        def save_close():
            father = f_entry.get().strip() or None
            mother = m_entry.get().strip() or None
            selected_ethnicities = [eth for eth, var in vars_dict.items() if var.get()]
            
            node.father = father
            node.mother = mother
            node.base_ethnicities = selected_ethnicities
            
            if father and father not in self.tree:
                self.tree[father] = AncestorNode(father)
            if mother and mother not in self.tree:
                self.tree[mother] = AncestorNode(mother)
                
            dialog.destroy()
            self.refresh_plot()
        
        tk.Button(dialog, text="Save & Update Tree", command=save_close, bg="#10b981", fg="white", font=("Arial", 11, "bold"), width=20, height=2).pack(pady=10)

    def save_tree(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")])
        if not file_path: return
            
        serializable_data = {
            "master_ethnicities": self.ethnicity_options,
            "ethnicity_colors": self.ethnicity_colors,
            "nodes": {}
        }
        for name, node in self.tree.items():
            serializable_data["nodes"][name] = {
                "name": node.name,
                "base_ethnicities": node.base_ethnicities,
                "father": node.father,
                "mother": node.mother
            }
            
        with open(file_path, 'w') as f:
            json.dump(serializable_data, f, indent=4)
        messagebox.showinfo("Saved", "Tree state and custom color profiles successfully exported.")

    def load_tree(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if not file_path: return
            
        with open(file_path, 'r') as f:
            raw_data = json.load(f)
            
        self.tree.clear()
        self.ethnicity_options = raw_data.get("master_ethnicities", [])
        self.ethnicity_colors = raw_data.get("ethnicity_colors", {})
        nodes_source = raw_data.get("nodes", {})
            
        for name, data in nodes_source.items():
            self.tree[name] = AncestorNode(
                name=data["name"],
                base_ethnicities=data.get("base_ethnicities", []),
                father=data.get("father"),
                mother=data.get("mother")
            )
            
        self.refresh_plot()
        messagebox.showinfo("Loaded", "Tree configuration imported successfully.")
        
    def clear_tree(self):
        if messagebox.askyesno("Confirm", "Are you sure you want to drop the active workspace state?"):
            self.tree.clear()
            self.ethnicity_options.clear()
            self.ethnicity_colors.clear()
            self.press_x = None  
            self.initialize_default_tree()

if __name__ == "__main__":
    root = tk.Tk()
    app = AncestryApp(root)
    root.mainloop()
