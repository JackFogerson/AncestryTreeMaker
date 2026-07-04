import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog
import json
import os
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class AncestorNode:
    def __init__(self, name, ethnicities=None, father=None, mother=None):
        self.name = name
        # Dict format: {"Irish": 50, "German": 50}
        self.ethnicities = ethnicities if ethnicities else {}
        self.father = father  # Name string
        self.mother = mother  # Name string

class AncestryApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Interactive Ancestry Pie-Chart Tree")
        self.root.geometry("1200x800")
        
        self.tree = {}  # key: name string, value: AncestorNode object
        
        self.setup_ui()
        
    def setup_ui(self):
        # Left Control Panel
        control_panel = tk.Frame(self.root, width=300, padx=10, pady=10)
        control_panel.pack(side=tk.LEFT, fill=tk.Y)
        
        # Add Node Section
        tk.Label(control_panel, text="Add / Edit Ancestor", font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=(0,10))
        
        tk.Label(control_panel, text="Full Name:").pack(anchor=tk.W)
        self.name_entry = tk.Entry(control_panel, width=30)
        self.name_entry.pack(fill=tk.X, pady=(0,5))
        
        tk.Label(control_panel, text="Father's Name (Optional):").pack(anchor=tk.W)
        self.father_entry = tk.Entry(control_panel, width=30)
        self.father_entry.pack(fill=tk.X, pady=(0,5))
        
        tk.Label(control_panel, text="Mother's Name (Optional):").pack(anchor=tk.W)
        self.mother_entry = tk.Entry(control_panel, width=30)
        self.mother_entry.pack(fill=tk.X, pady=(0,10))
        
        tk.Label(control_panel, text="Ethnicities (e.g., Irish:50, German:50):").pack(anchor=tk.W)
        self.ethnicity_entry = tk.Entry(control_panel, width=30)
        self.ethnicity_entry.pack(fill=tk.X, pady=(0,10))
        
        tk.Button(control_panel, text="Save/Update Person", command=self.add_ancestor, bg="#4CAF50", fg="white").pack(fill=tk.X, pady=5)
        
        tk.Frame(control_panel, height=2, bd=1, relief=tk.SUNKEN).pack(fill=tk.X, pady=15)
        
        # IO Operations Section
        tk.Label(control_panel, text="File Actions", font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=(0,5))
        tk.Button(control_panel, text="Save Tree JSON", command=self.save_tree, bg="#2196F3", fg="white").pack(fill=tk.X, pady=5)
        tk.Button(control_panel, text="Load Tree JSON", command=self.load_tree, bg="#FF9800", fg="white").pack(fill=tk.X, pady=5)
        tk.Button(control_panel, text="Clear Tree", command=self.clear_tree, bg="#f44336", fg="white").pack(fill=tk.X, pady=5)
        
        # Right Tree View Plot Area
        self.plot_panel = tk.Frame(self.root, bg="white")
        self.plot_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.fig, self.ax = plt.subplots(figsize=(8, 8))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_panel)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        self.refresh_plot()

    def add_ancestor(self):
        name = self.name_entry.get().strip()
        father = self.father_entry.get().strip() or None
        mother = self.mother_entry.get().strip() or None
        eth_str = self.ethnicity_entry.get().strip()
        
        if not name:
            messagebox.showerror("Error", "Name field is required.")
            return
            
        # Parse Ethnicity Input
        ethnicities = {}
        if eth_str:
            try:
                pairs = eth_str.split(",")
                for pair in pairs:
                    k, v = pair.split(":")
                    ethnicities[k.strip()] = float(v.strip())
            except ValueError:
                messagebox.showerror("Error", "Invalid ethnicity format. Please use 'Key:Value, Key:Value'")
                return

        # Initialize or Update Node
        if name in self.tree:
            self.tree[name].ethnicities = ethnicities
            self.tree[name].father = father
            self.tree[name].mother = mother
        else:
            self.tree[name] = AncestorNode(name, ethnicities, father, mother)
            
        # Auto-create empty shells for parents if they don't exist yet to support visualization links
        if father and father not in self.tree:
            self.tree[father] = AncestorNode(father)
        if mother and mother not in self.tree:
            self.tree[mother] = AncestorNode(mother)
            
        # Clear fields
        self.name_entry.delete(0, tk.END)
        self.father_entry.delete(0, tk.END)
        self.mother_entry.delete(0, tk.END)
        self.ethnicity_entry.delete(0, tk.END)
        
        self.refresh_plot()
        messagebox.showinfo("Success", f"Saved {name} to tree.")

    def calculate_positions(self):
        """Generates coordinate positions for nodes dynamically based on parent relationships."""
        positions = {}
        if not self.tree:
            return positions
            
        # Find root nodes (nodes that are not listed as anyone's mother or father)
        children_names = set()
        for node in self.tree.values():
            if node.father: children_names.add(node.father)
            if node.mother: children_names.add(node.mother)
            
        roots = [name for name in self.tree if name not in children_names]
        if not roots:  # Fallback if there is a circular reference loop
            roots = [list(self.tree.keys())[0]]
            
        def assign_coords(node_name, x, y, horizontal_spacing):
            if node_name not in self.tree or node_name in positions:
                return
            positions[node_name] = (x, y)
            
            node = self.tree[node_name]
            # Move parents up one level
            if node.father:
                assign_coords(node.father, x - horizontal_spacing, y + 1.5, horizontal_spacing / 2)
            if node.mother:
                assign_coords(node.mother, x + horizontal_spacing, y + 1.5, horizontal_spacing / 2)

        for i, root in enumerate(roots):
            assign_coords(root, x=i * 6.0, y=0, horizontal_spacing=2.0)
            
        return positions

    def refresh_plot(self):
        self.ax.clear()
        self.ax.set_title("Ancestry Tree Visualizer")
        self.ax.axis('off')
        
        positions = self.calculate_positions()
        
        if not positions:
            self.ax.text(0.5, 0.5, "No ancestors added yet.\nUse the left panel to populate your tree.", 
                         ha='center', va='center', transform=self.ax.transAxes, fontsize=12)
            self.canvas.draw()
            return

        # Draw relationship lines first so they sit behind the pie graphs
        for name, node in self.tree.items():
            if name in positions:
                x, y = positions[name]
                if node.father in positions:
                    fx, fy = positions[node.father]
                    self.ax.plot([x, fx], [y, fy], color='#7f8c8d', linestyle='-', linewidth=1.5, zorder=1)
                if node.mother in positions:
                    mx, my = positions[node.mother]
                    self.ax.plot([x, mx], [y, my], color='#7f8c8d', linestyle='-', linewidth=1.5, zorder=1)

        # Draw Pie Charts for each Individual
        for name, (x, y) in positions.items():
            node = self.tree[name]
            
            # Sub-axis wrapper inside plot for individual pie graphs
            size = 0.55  
            inset_ax = self.ax.inset_axes([x - size/2, y - size/2, size, size], transform=self.ax.transData)
            inset_ax.zorder = 2
            
            if node.ethnicities:
                labels = list(node.ethnicities.keys())
                values = list(node.ethnicities.values())
                inset_ax.pie(values, labels=labels, textprops={'fontsize': 7}, radius=1.0)
            else:
                # Placeholder gray circle for empty data fields
                inset_ax.pie([1], colors=['#e0e0e0'], radius=1.0)
                inset_ax.text(0, 0, "?", ha='center', va='center', fontsize=10, color='#7f8c8d')
                
            inset_ax.axis('equal')
            
            # Label banner below the pie graph
            self.ax.text(x, y - (size / 1.6), name, ha='center', va='top', 
                         fontsize=9, weight='bold',
                         bbox=dict(boxstyle='round,pad=0.2', facecolor='#ffffff', edgecolor='#cbd5e1', alpha=0.9))

        # Adjust viewport limits dynamically based on tree bounds
        all_x = [pt[0] for pt in positions.values()]
        all_y = [pt[1] for pt in positions.values()]
        self.ax.set_xlim(min(all_x) - 1.5, max(all_x) + 1.5)
        self.ax.set_ylim(min(all_y) - 1.0, max(all_y) + 2.0)
        
        self.canvas.draw()

    def save_tree(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")])
        if not file_path:
            return
            
        serializable_data = {}
        for name, node in self.tree.items():
            serializable_data[name] = {
                "name": node.name,
                "ethnicities": node.ethnicities,
                "father": node.father,
                "mother": node.mother
            }
            
        with open(file_path, 'w') as f:
            json.dump(serializable_data, f, indent=4)
        messagebox.showinfo("Saved", "Tree state successfully saved.")

    def load_tree(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if not file_path:
            return
            
        with open(file_path, 'r') as f:
            raw_data = json.load(f)
            
        self.tree.clear()
        for name, data in raw_data.items():
            self.tree[name] = AncestorNode(
                name=data["name"],
                ethnicities=data["ethnicities"],
                father=data["father"],
                mother=data["mother"]
            )
            
        self.refresh_plot()
        messagebox.showinfo("Loaded", "Tree state successfully updated from file Data.")
        
    def clear_tree(self):
        if messagebox.askyesno("Confirm", "Are you sure you want to delete the active tree workspace?"):
            self.tree.clear()
            self.refresh_plot()

if __name__ == "__main__":
    root = tk.Tk()
    app = AncestryApp(root)
    root.mainloop()
