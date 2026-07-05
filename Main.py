import tkinter as tk
from tkinter import messagebox, filedialog
import json
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class AncestorNode:
    def __init__(self, name, base_ethnicities=None, father=None, mother=None):
        self.name = name
        # Base ethnicities explicitly declared for THIS specific person (e.g., ["English"])
        self.base_ethnicities = base_ethnicities if base_ethnicities else []
        self.father = father  # Name string
        self.mother = mother  # Name string
        
        # Computed dynamic dict format: {"English": 50.0, "French": 50.0}
        self.computed_ethnicities = {}

class AncestryApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Interactive Ancestry Pie-Chart Tree")
        self.root.geometry("1200x800")
        
        # Master list of available ethnicities to choose from
        self.ethnicity_options = ["English", "Irish", "German", "French", "Italian", "Scottish", "Welsh", "Native American", "African", "Asian", "Other"]
        
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
        # Left Control Panel (Only containing configuration management actions now)
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
        """Recursively calculates dynamic ancestral inheritance down the tree structure."""
        # Reset current computed states
        for node in self.tree.values():
            node.computed_ethnicities = {}

        # Helper to find children of a parent
        def get_children(parent_name):
            return [name for name, node in self.tree.items() if node.father == parent_name or node.mother == parent_name]

        # Step 1: Assign 100% distribution split for nodes with designated base ethnicities
        for name, node in self.tree.items():
            if node.base_ethnicities:
                count = len(node.base_ethnicities)
                for eth in node.base_ethnicities:
                    node.computed_ethnicities[eth] = node.computed_ethnicities.get(eth, 0.0) + (100.0 / count)

        # Step 2: Propagate values downwards through generations iteratively
        # Find roots (top level ancestors with no parents in tree)
        for name, node in self.tree.items():
            if not node.father and not node.mother:
                self._push_down_heritage(name)

    def _push_down_heritage(self, parent_name):
        """Passes 50% of the parent's current total computed background profile down to children."""
        parent_node = self.tree[parent_name]
        if not parent_node.computed_ethnicities:
            return

        # Find any direct children linked to this parent
        for child_name, child_node in self.tree.items():
            if child_node.father == parent_name or child_node.mother == parent_name:
                # Add half of parent's percentage weight directly to the child's calculation
                for eth, pct in parent_node.computed_ethnicities.items():
                    child_node.computed_ethnicities[eth] = child_node.computed_ethnicities.get(eth, 0.0) + (pct * 0.5)
                
                # Recurse downstream
                self._push_down_heritage(child_name)

    def calculate_positions(self):
        positions = {}
        if not self.tree:
            return positions
            
        children_names = set()
        for node in self.tree.values():
            if node.father: children_names.add(node.father)
            if node.mother: children_names.add(node.mother)
            
        # Jack Fogerson or absolute roots are mapped at bottom level index coordinate zero
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
        self.calculate_inheritance()  # Process latest generational splits prior to painting canvas
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
                inset_ax.pie(values, labels=labels, textprops={'fontsize': 6, 'weight': 'bold'}, radius=1.0)
            else:
                inset_ax.pie([1], colors=['#e2e8f0'], radius=1.0)
                inset_ax.text(0, 0, "No Data", ha='center', va='center', fontsize=7, color='#64748b', weight='bold')
                
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
        """Interactive Management Window for updating links and base heritage traits."""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Manage Profile: {person_name}")
        dialog.geometry("450x550")
        dialog.transient(self.root)
        dialog.grab_set()
        
        node = self.tree[person_name]
        
        tk.Label(dialog, text=f"Editing Family Network for:", font=("Arial", 10)).pack(pady=(15,2))
        tk.Label(dialog, text=person_name, font=("Arial", 14, "bold"), fg="#047857").pack(pady=(0,15))
        
        # Parent Input Forms
        tk.Label(dialog, text="Father's Full Name:", font=("Arial", 10, "bold")).pack(anchor=tk.W, padx=30)
        f_entry = tk.Entry(dialog, width=40, font=("Arial", 10))
        f_entry.insert(0, node.father or "")
        f_entry.pack(padx=30, pady=(0, 12))
        
        tk.Label(dialog, text="Mother's Full Name:", font=("Arial", 10, "bold")).pack(anchor=tk.W, padx=30)
        m_entry = tk.Entry(dialog, width=40, font=("Arial", 10))
        m_entry.insert(0, node.mother or "")
        m_entry.pack(padx=30, pady=(0, 15))
        
        # Ethnicity Checklist Selection Frame
        tk.Label(dialog, text="Select This Ancestor's Primary Ethnicity Backgrounds:", font=("Arial", 10, "bold")).pack(anchor=tk.W, padx=30, pady=(5,5))
        
        checkbox_frame = tk.LabelFrame(dialog, text=" Available Origins (Check all that apply) ", padx=10, pady=10)
        checkbox_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=(0,15))
        
        # Grid organization layout strategy for options display
        vars_dict = {}
        for idx, ethnicity in enumerate(self.ethnicity_options):
            var = tk.BooleanVar(value=(ethnicity in node.base_ethnicities))
            vars_dict[ethnicity] = var
            cb = tk.Checkbutton(checkbox_frame, text=ethnicity, variable=var, font=("Arial", 9))
            cb.grid(row=idx // 2, column=idx % 2, sticky=tk.W, padx=10, pady=3)

        def save_close():
            father = f_entry.get().strip() or None
            mother = m_entry.get().strip() or None
            
            # Extract checked elements back to list structures
            selected_ethnicities = [eth for eth, var in vars_dict.items() if var.get()]
            
            # Update values inside active memory storage trees
            node.father = father
            node.mother = mother
            node.base_ethnicities = selected_ethnicities
            
            # Initialize blank tracking shells for newly declared upstream components
            if father and father not in self.tree:
                self.tree[father] = AncestorNode(father)
            if mother and mother not in self.tree:
                self.tree[mother] = AncestorNode(mother)
                
            dialog.destroy()
            self.refresh_plot()
        
        tk.Button(dialog, text="Save & Update Tree", command=save_close, bg="#10b981", fg="white", font=("Arial", 11, "bold"), width=20, height=2).pack(pady=15)

    def save_tree(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")])
        if not file_path: return
            
        serializable_data = {}
        for name, node in self.tree.items():
            serializable_data[name] = {
                "name": node.name,
                "base_ethnicities": node.base_ethnicities,
                "father": node.father,
                "mother": node.mother
            }
            
        with open(file_path, 'w') as f:
            json.dump(serializable_data, f, indent=4)
        messagebox.showinfo("Saved", "Tree configuration data safely exported.")

    def load_tree(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if not file_path: return
            
        with open(file_path, 'r') as f:
            raw_data = json.load(f)
            
        self.tree.clear()
        for name, data in raw_data.items():
            # Support backwards legacy load file mapping variables smoothly if keys match old files
            base_eth = data.get("base_ethnicities", list(data.get("ethnicities", {}).keys()))
            self.tree[name] = AncestorNode(
                name=data["name"],
                base_ethnicities=base_eth,
                father=data.get("father"),
                mother=data.get("mother")
            )
            
        self.refresh_plot()
        messagebox.showinfo("Loaded", "Tree configuration imported successfully.")
        
    def clear_tree(self):
        if messagebox.askyesno("Confirm", "Are you sure you want to drop the active workspace state?"):
            self.tree.clear()
            self.initialize_default_tree()

if __name__ == "__main__":
    root = tk.Tk()
    app = AncestryApp(root)
    root.mainloop()
