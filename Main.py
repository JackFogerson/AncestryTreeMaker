import tkinter as tk
from tkinter import messagebox, filedialog, colorchooser
import json
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class AncestorNode:
    def __init__(self, name, base_ethnicities=None, father=None, mother=None):
        self.name = name
        # Base ethnicities explicitly declared for THIS specific person *only if they are a root*
        self.base_ethnicities = base_ethnicities if base_ethnicities else []
        self.father = father  # Name string
        self.mother = mother  # Name string
        
        # Computed dynamic dict format: {"German": 50.0, "Unknown": 50.0}
        self.computed_ethnicities = {}

class AncestryApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Interactive Ancestry Pie-Chart Tree")
        self.root.geometry("1200x800")
        
        # Completely blank initial ethnicity settings to match user constraints
        self.ethnicity_options = []
        self.ethnicity_colors = {} # Maps ethnicity name string -> hex color string
        
        self.tree = {}  
        self.plus_buttons = {}  
        
        self.setup_ui()
        self.initialize_default_tree()
        
    def initialize_default_tree(self):
        """Ensures the tree starts with Jack Fogerson as the base child point."""
        if not self.tree:
            self.tree["Jack Fogerson"] = AncestorNode("Jack Fogerson")
            self.refresh_plot()

    def setup_ui(self):
        # Left Control Panel (Strictly containing workspace and profile actions)
        control_panel = tk.Frame(self.root, width=250, padx=15, pady=15, bg="#f8fafc")
        control_panel.pack(side=tk.LEFT, fill=tk.Y)
        
        tk.Label(control_panel, text="File Actions", font=("Arial", 14, "bold"), bg="#f8fafc", fg="#1e293b").pack(anchor=tk.W, pady=(0,15))
        
        tk.Button(control_panel, text="Save Tree JSON", command=self.save_tree, bg="#2196F3", fg="white", font=("Arial", 10, "bold"), height=2).pack(fill=tk.X, pady=6)
        tk.Button(control_panel, text="Load Tree JSON", command=self.load_tree, bg="#FF9800", fg="white", font=("Arial", 10, "bold"), height=2).pack(fill=tk.X, pady=6)
        tk.Button(control_panel, text="Clear Tree", command=self.clear_tree, bg="#f44336", fg="white", font=("Arial", 10, "bold"), height=2).pack(fill=tk.X, pady=6)
        
        # Right Tree View Plot Area
        self.plot_panel = tk.Frame(self.root, bg="white")
        self.plot_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.fig, self.ax = plt.subplots(figsize=(8, 8))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_panel)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        self.fig.canvas.mpl_connect('button_press_event', self.on_canvas_click)

    def calculate_inheritance(self):
        """Calculates inheritance recursively. Handles missing values cleanly via 'Unknown' states."""
        # Reset current computed states
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
        
        # Condition A: If the person has parents, combine profiles precisely at 50% split each
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
            
        # Condition B: Root block calculation configuration profile
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
            if node.father:
                assign_coords(node.father, x - horizontal_spacing, y + 1.5, horizontal_spacing / 1.8)
            if node.mother:
                assign_coords(node.mother, x + horizontal_spacing, y + 1.5, horizontal_spacing / 1.8)

        for i, root in enumerate(roots):
            assign_coords(root, x=i * 6.0, y=0, horizontal_spacing=2.5)
            
        return positions

    def refresh_plot(self):
        self.calculate_inheritance()  
        self.ax.clear()
        self.ax.set_title("Ancestry Tree (Click '+' above a person to manage family links)", fontsize=12, weight='bold', pad=10)
        self.ax.axis('off')
        
        positions = self.calculate_positions()
        self.plus_buttons.clear()
        
        if not positions:
            self.canvas.draw()
            return

        # Draw relationship lines
        for name, node in self.tree.items():
            if name in positions:
                x, y = positions[name]
                if node.father in positions:
                    fx, fy = positions[node.father]
                    self.ax.plot([x, fx], [y, fy], color='#94a3b8', linestyle='-', linewidth=2, zorder=1)
                if node.mother in positions:
                    mx, my = positions[node.mother]
                    self.ax.plot([x, mx], [y, my], color='#94a3b8', linestyle='-', linewidth=2, zorder=1)

        # Draw Pie Charts & Plus Buttons
        for name, (x, y) in positions.items():
            node = self.tree[name]
            size = 0.55  
            
            inset_ax = self.ax.inset_axes([x - size/2, y - size/2, size, size], transform=self.ax.transData)
            inset_ax.zorder = 2
            
            if node.computed_ethnicities:
                labels = [f"{k}\n{v:.1f}%" for k, v in node.computed_ethnicities.items()]
                values = list(node.computed_ethnicities.values())
                
                # Fetch specific custom hex colors, fall back to soft gray for 'Unknown' fields
                pie_colors = [self.ethnicity_colors.get(k, '#e2e8f0') for k in node.computed_ethnicities.keys()]
                
                inset_ax.pie(values, labels=labels, colors=pie_colors, textprops={'fontsize': 6, 'weight': 'bold'}, radius=1.0)
            else:
                inset_ax.pie([1], colors=['#e2e8f0'], radius=1.0)
                inset_ax.text(0, 0, "Unknown", ha='center', va='center', fontsize=7, color='#64748b', weight='bold')
                
            inset_ax.axis('equal')
            
            # Label banner below
            self.ax.text(x, y - (size / 1.5), name, ha='center', va='top', 
                         fontsize=9, weight='bold',
                         bbox=dict(boxstyle='round,pad=0.3', facecolor='#ffffff', edgecolor='#cbd5e1', alpha=0.95))
            
            # Draw Plus '+' Button directly above
            plus_y = y + (size / 1.5)
            self.ax.text(x, plus_y, " + ", ha='center', va='center', 
                         fontsize=10, weight='bold', color='white',
                         bbox=dict(boxstyle='circle,pad=0.2', facecolor='#10b981', edgecolor='#047857', alpha=1.0))
            
            self.plus_buttons[name] = (x, plus_y)

        all_x = [pt[0] for pt in positions.values()]
        all_y = [pt[1] for pt in positions.values()]
        self.ax.set_xlim(min(all_x) - 2.0, max(all_x) + 2.0)
        self.ax.set_ylim(min(all_y) - 1.2, max(all_y) + 2.2)
        
        self.canvas.draw()

    def on_canvas_click(self, event):
        if event.xdata is None or event.ydata is None:
            return
        click_radius = 0.3
        for name, (bx, by) in self.plus_buttons.items():
            distance = ((event.xdata - bx)**2 + (event.ydata - by)**2)**0.5
            if distance <= click_radius:
                self.open_parent_dialog(name)
                break

    def open_parent_dialog(self, person_name):
        """Interactive Window for updating links, adding custom origins, and editing color properties."""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Manage Profile: {person_name}")
        dialog.geometry("520x660")
        dialog.transient(self.root)
        dialog.grab_set()
        
        node = self.tree[person_name]
        
        tk.Label(dialog, text=f"Editing Family Network for:", font=("Arial", 10)).pack(pady=(12,2))
        tk.Label(dialog, text=person_name, font=("Arial", 14, "bold"), fg="#047857").pack(pady=(0,12))
        
        # Parent Input Forms
        tk.Label(dialog, text="Father's Full Name:", font=("Arial", 10, "bold")).pack(anchor=tk.W, padx=30)
        f_entry = tk.Entry(dialog, width=40, font=("Arial", 10))
        f_entry.insert(0, node.father or "")
        f_entry.pack(padx=30, pady=(0, 10))
        
        tk.Label(dialog, text="Mother's Full Name:", font=("Arial", 10, "bold")).pack(anchor=tk.W, padx=30)
        m_entry = tk.Entry(dialog, width=40, font=("Arial", 10))
        m_entry.insert(0, node.mother or "")
        m_entry.pack(padx=30, pady=(0, 12))
        
        # Custom Ethnicity Insertion Area
        custom_frame = tk.Frame(dialog)
        custom_frame.pack(fill=tk.X, padx=30, pady=(0, 10))
        tk.Label(custom_frame, text="Add New Ethnicity:", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        new_eth_entry = tk.Entry(custom_frame, width=15, font=("Arial", 10))
        new_eth_entry.pack(side=tk.LEFT, padx=5)
        
        # Checklist Selection Frame
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
                
                # Color Block Editor Element
                clr = self.ethnicity_colors.get(ethnicity, "#cbd5e1")
                lbl_color = tk.Label(checkbox_frame, bg=clr, width=3, relief=tk.RAISED, cursor="hand2")
                lbl_color.grid(row=row_idx, column=col_idx+1, sticky=tk.W, padx=(0,15))
                lbl_color.bind("<Button-1>", lambda e, eth=ethnicity: pick_edit_color(eth))

        def add_custom_ethnicity():
            new_eth = new_eth_entry.get().strip().title()
            if new_eth and new_eth not in self.ethnicity_options:
                # Open color picker immediately on declaration
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
        
        # Sync palette states from data file configuration layers
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
            self.initialize_default_tree()

if __name__ == "__main__":
    root = tk.Tk()
    app = AncestryApp(root)
    root.mainloop()
