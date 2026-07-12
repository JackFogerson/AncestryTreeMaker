import tkinter as tk
from tkinter import messagebox, filedialog, colorchooser, ttk
import json
import math

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
        self.root.title("Ancestor Tree Creator")
        self.root.geometry("1200x800")
        
        self.ethnicity_options = []
        self.ethnicity_colors = {} 
        
        self.tree = {}  
        self.positions = {}
        
        # Camera persistence state properties
        self.canvas_scale = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        
        self.drag_start_x = 0
        self.drag_start_y = 0
        
        self.active_breakdown_window = None
        self.show_decorations = True
        
        # Display the starting workflow wizard
        self.show_welcome_screen()

    def show_welcome_screen(self):
        self.welcome_frame = tk.Frame(self.root, bg="#f8fafc")
        self.welcome_frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(
            self.welcome_frame, 
            text="Ancestor Tree Creator", 
            font=("Arial", 28, "bold"), 
            bg="#f8fafc", 
            fg="#1e293b"
        ).pack(pady=(150, 10))
        
        tk.Label(
            self.welcome_frame, 
            text="Select an option below to initialize your lineage tree workspace.", 
            font=("Arial", 12), 
            bg="#f8fafc", 
            fg="#64748b"
        ).pack(pady=(0, 40))
        
        btn_frame = tk.Frame(self.welcome_frame, bg="#f8fafc")
        btn_frame.pack()
        
        tk.Button(
            btn_frame, 
            text="Create New Tree", 
            command=self.setup_new_tree_input, 
            bg="#10b981", 
            fg="white", 
            font=("Arial", 12, "bold"), 
            width=22, 
            height=2, 
            bd=0, 
            cursor="hand2"
        ).grid(row=0, column=0, padx=15)
        
        tk.Button(
            btn_frame, 
            text="Load Existing Tree", 
            command=lambda: self.load_tree(from_welcome=True), 
            bg="#2196F3", 
            fg="white", 
            font=("Arial", 12, "bold"), 
            width=22, 
            height=2, 
            bd=0, 
            cursor="hand2"
        ).grid(row=0, column=1, padx=15)

    def setup_new_tree_input(self):
        for widget in self.welcome_frame.winfo_children():
            widget.destroy()
            
        tk.Label(
            self.welcome_frame, 
            text="Ancestor Tree Creator", 
            font=("Arial", 28, "bold"), 
            bg="#f8fafc", 
            fg="#1e293b"
        ).pack(pady=(150, 10))
        
        tk.Label(
            self.welcome_frame, 
            text="Enter the full name of the primary root person:", 
            font=("Arial", 12), 
            bg="#f8fafc", 
            fg="#64748b"
        ).pack(pady=(0, 20))
        
        name_entry = tk.Entry(
            self.welcome_frame, 
            font=("Arial", 14), 
            width=32, 
            bd=1, 
            relief=tk.SOLID, 
            highlightthickness=4, 
            highlightbackground="#e2e8f0", 
            highlightcolor="#cbd5e1"
        )
        name_entry.pack(pady=10)
        name_entry.focus_set()
        
        def confirm_name(event=None):
            name = name_entry.get().strip()
            if not name:
                messagebox.showwarning("Naming Error", "Please provide a valid name to create the root profile.")
                return
            
            self.tree[name] = AncestorNode(name)
            self.welcome_frame.destroy()
            self.setup_ui()
            self.reset_view_to_root()
            
        name_entry.bind("<Return>", confirm_name)
        
        tk.Button(
            self.welcome_frame, 
            text="Initialize Workspace", 
            command=confirm_name, 
            bg="#10b981", 
            fg="white", 
            font=("Arial", 12, "bold"), 
            width=22, 
            height=2, 
            bd=0, 
            cursor="hand2"
        ).pack(pady=20)

    def setup_ui(self):
        control_panel = tk.Frame(self.root, width=250, padx=15, pady=15, bg="#f8fafc")
        control_panel.pack(side=tk.LEFT, fill=tk.Y)
        
        tk.Label(control_panel, text="File Actions", font=("Arial", 14, "bold"), bg="#f8fafc", fg="#1e293b").pack(anchor=tk.W, pady=(0,15))
        
        tk.Button(control_panel, text="Save Tree JSON", command=self.save_tree, bg="#2196F3", fg="white", font=("Arial", 10, "bold"), height=2).pack(fill=tk.X, pady=6)
        tk.Button(control_panel, text="Load Tree JSON", command=lambda: self.load_tree(from_welcome=False), bg="#FF9800", fg="white", font=("Arial", 10, "bold"), height=2).pack(fill=tk.X, pady=6)
        tk.Button(control_panel, text="Clear Tree Workspace", command=self.clear_tree, bg="#f44336", fg="white", font=("Arial", 10, "bold"), height=2).pack(fill=tk.X, pady=6)
        
        tk.Label(control_panel, text="View Actions", font=("Arial", 14, "bold"), bg="#f8fafc", fg="#1e293b").pack(anchor=tk.W, pady=(20,15))
        tk.Button(control_panel, text="Toggle Names/Buttons", command=self.toggle_decorations, bg="#475569", fg="white", font=("Arial", 10, "bold"), height=2).pack(fill=tk.X, pady=6)
        
        self.canvas = tk.Canvas(self.root, bg="white", highlightthickness=0)
        self.canvas.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<MouseWheel>", self.on_zoom)  
        self.canvas.bind("<Button-4>", self.on_zoom)    
        self.canvas.bind("<Button-5>", self.on_zoom)    

    def toggle_decorations(self):
        self.show_decorations = not self.show_decorations
        self.refresh_plot()

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
                
            has_father = node.father and node.father in self.tree
            has_mother = node.mother and node.mother in self.tree
            
            father_dna = self.tree[node.father].computed_ethnicities if has_father else {"Unknown": 100.0}
            mother_dna = self.tree[node.mother].computed_ethnicities if has_mother else {"Unknown": 100.0}
            
            is_single_parent = (node.father and not node.mother) or (node.mother and not node.father)
            applied_exception = False
            
            if is_single_parent:
                parent_dna = father_dna if has_father else mother_dna
                for eth, pct in parent_dna.items():
                    if abs(pct - 100.0) < 1e-5:
                        node.computed_ethnicities = {eth: 100.0}
                        applied_exception = True
                        break
            
            if not applied_exception:
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

    def _count_leaves(self, name, memo):
        if name not in self.tree:
            return 1
        if name in memo:
            return memo[name]
            
        node = self.tree[name]
        if not node.father and not node.mother:
            return 1
            
        f_leaves = self._count_leaves(node.father, memo) if node.father else 0
        m_leaves = self._count_leaves(node.mother, memo) if node.mother else 0
        
        memo[name] = max(1, f_leaves + m_leaves)
        return memo[name]

    def _get_max_depth(self, name, visited):
        if name in visited or name not in self.tree:
            return 0
        visited.add(name)
        node = self.tree[name]
        f_depth = self._get_max_depth(node.father, visited) if node.father else 0
        m_depth = self._get_max_depth(node.mother, visited) if node.mother else 0
        return 1 + max(f_depth, m_depth)

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
            
        leaf_memo = {}
        scale_factor = 140.0 
        vertical_generation_gap = 500.0

        def assign_coords(node_name, x_center, y, allocated_width):
            if node_name not in self.tree or node_name in positions:
                return
            positions[node_name] = (x_center, y)
            
            node = self.tree[node_name]
            if node.father and node.mother:
                f_w = self._count_leaves(node.father, leaf_memo)
                m_w = self._count_leaves(node.mother, leaf_memo)
                total_w = f_w + m_w
                
                f_share = (f_w / total_w) * allocated_width
                m_share = (m_w / total_w) * allocated_width
                
                f_x = x_center - (allocated_width / 2.0) + (f_share / 2.0)
                m_x = x_center + (allocated_width / 2.0) - (m_share / 2.0)
                
                assign_coords(node.father, f_x, y - vertical_generation_gap, f_share)
                assign_coords(node.mother, m_x, y - vertical_generation_gap, m_share)
            elif node.father:
                assign_coords(node.father, x_center, y - vertical_generation_gap, allocated_width)
            elif node.mother:
                assign_coords(node.mother, x_center, y - vertical_generation_gap, allocated_width)

        max_depth = 1
        for root in roots:
            max_depth = max(max_depth, self._get_max_depth(root, set()))
        
        current_x_offset = 200.0
        base_y = max(600.0, max_depth * vertical_generation_gap + 100.0)
        
        for root in roots:
            leaves = self._count_leaves(root, leaf_memo)
            root_width = leaves * scale_factor
            root_center = current_x_offset + (root_width / 2.0)
            
            assign_coords(root, root_center, base_y, allocated_width=root_width)
            current_x_offset += root_width + 150.0 
            
        return positions

    def reset_view_to_root(self):
        self.root.update_idletasks()
        self.calculate_inheritance()
        self.positions = self.calculate_positions()
        
        if not self.positions:
            return
            
        children_names = set()
        for node in self.tree.values():
            if node.father: children_names.add(node.father)
            if node.mother: children_names.add(node.mother)
            
        roots = [name for name in self.tree if name not in children_names]
        if not roots:  
            roots = list(self.tree.keys())
            
        if roots and roots[0] in self.positions:
            rx, ry = self.positions[roots[0]]
            c_width = self.canvas.winfo_width()
            c_height = self.canvas.winfo_height()
            
            if c_width <= 1: c_width = 950
            if c_height <= 1: c_height = 800
            
            self.canvas_scale = 1.0
            self.pan_x = (c_width / 2.0) - rx
            self.pan_y = (c_height / 2.0) - ry
            
        self.refresh_plot()

    def draw_pie_chart(self, x, y, radius, ethnicities):
        active_eth = {k: v for k, v in ethnicities.items() if v > 0}
        
        if not active_eth:
            self.canvas.create_oval(x - radius, y - radius, x + radius, y + radius, fill="#e2e8f0", outline="#cbd5e1", width=1)
            return

        sorted_eth = sorted(active_eth.items(), key=lambda item: item[1], reverse=True)
        largest_eth, largest_val = sorted_eth[0]
        base_color = '#e2e8f0' if largest_eth == "Unknown" else self.ethnicity_colors.get(largest_eth, '#e2e8f0')

        self.canvas.create_oval(x - radius, y - radius, x + radius, y + radius, fill=base_color, outline="#cbd5e1", width=1)
        
        if len(active_eth) == 1:
            return
            
        total = sum(active_eth.values())
        current_angle = 0.0
        
        for eth, value in active_eth.items():
            extent = (value / total) * 360.0
            if eth != largest_eth:
                color = '#e2e8f0' if eth == "Unknown" else self.ethnicity_colors.get(eth, '#e2e8f0')
                
                points = [x, y]
                steps = max(4, int(extent / 3)) 
                for i in range(steps + 1):
                    ang = current_angle + (extent * i / steps)
                    rad = math.radians(ang)
                    px = x + radius * math.cos(rad)
                    py = y - radius * math.sin(rad)
                    points.append(px)
                    points.append(py)
                    
                self.canvas.create_polygon(points, fill=color, outline="#ffffff", width=0.5)
            current_angle += extent

    def get_formatted_split_name(self, name):
        words = name.strip().split()
        if not words:
            return ""
        if len(words) == 1:
            return words[0]
            
        suffixes = {'jr', 'jr.', 'sr', 'sr.', 'iii', 'iv', 'v', 'vi', 'vii', 'viii', 'ix', 'x', '2nd', '3rd', '4th'}
        
        last_name_idx = len(words) - 1
        while last_name_idx >= 0:
            word_clean = words[last_name_idx].lower().strip(',.')
            if word_clean not in suffixes:
                break
            last_name_idx -= 1
            
        if last_name_idx < 0:
            last_name_idx = len(words) - 1
            
        if last_name_idx == 0:
            return f"{words[0]}\n" + " ".join(words[1:])
            
        top_line = " ".join(words[:last_name_idx])
        bottom_line = " ".join(words[last_name_idx:])
        return f"{top_line}\n{bottom_line}"

    def refresh_plot(self):
        if not hasattr(self, 'canvas'): 
            return
            
        self.canvas.delete("all")
        self.calculate_inheritance()  
        self.positions = self.calculate_positions()
        
        if not self.positions:
            return

        for name, node in self.tree.items():
            if name in self.positions:
                x, y = self.positions[name]
                has_father = node.father in self.positions
                has_mother = node.mother in self.positions
                
                if has_father and has_mother:
                    fx, fy = self.positions[node.father]
                    mx, my = self.positions[node.mother]
                    mid_y = y - 250.0  
                    
                    self.canvas.create_line(x, y, x, mid_y, fill='#10b981', width=3)
                    self.canvas.create_line(fx, mid_y, mx, mid_y, fill='#10b981', width=3)
                    self.canvas.create_line(fx, mid_y, fx, fy, fill='#10b981', width=3)
                    self.canvas.create_line(mx, mid_y, mx, my, fill='#10b981', width=3)
                elif has_father:
                    fx, fy = self.positions[node.father]
                    self.canvas.create_line(x, y, fx, fy, fill='#94a3b8', width=2)
                elif has_mother:
                    mx, my = self.positions[node.mother]
                    self.canvas.create_line(x, y, mx, my, fill='#94a3b8', width=2)

        pie_radius = 35.0
        
        for name, (x, y) in self.positions.items():
            node = self.tree[name]
            chart_tag = f"pie_click:{name}"
            
            self.draw_pie_chart(x, y, pie_radius, node.computed_ethnicities)
            self.canvas.create_oval(x - pie_radius, y - pie_radius, x + pie_radius, y + pie_radius, 
                                    fill="", outline="", tags=(chart_tag, "interactive"))
            
            if self.show_decorations:
                formatted_name = self.get_formatted_split_name(name)
                text_y = y + pie_radius + 22.0
                
                lbl = self.canvas.create_text(x, text_y, text=formatted_name, font=("Arial", 13, "bold"), 
                                              fill="#0f172a", justify=tk.CENTER, tags=("node_text",))
                
                bbox = self.canvas.bbox(lbl)
                padding = 5
                bg_rect = self.canvas.create_rectangle(bbox[0]-padding, bbox[1]-padding, bbox[2]+padding, bbox[3]+padding, 
                                                       fill="#ffffff", outline="#cbd5e1", width=1)
                self.canvas.tag_lower(bg_rect, lbl)
                
                plus_tag = f"plus_click:{name}"
                plus_y = y - pie_radius - 15.0
                
                btn_r = 8
                self.canvas.create_rectangle(x - btn_r, plus_y - btn_r, x + btn_r, plus_y + btn_r, 
                                             fill="#10b981", outline="#047857", tags=(plus_tag, "interactive"))
                self.canvas.create_text(x, plus_y, text="+", font=("Arial", 13, "bold"), fill="white", 
                                        tags=(plus_tag, "interactive", "plus_text"))

        self.canvas.scale("all", 0, 0, self.canvas_scale, self.canvas_scale)
        self.canvas.move("all", self.pan_x, self.pan_y)
        
        new_font_size = max(1, int(13 * self.canvas_scale))
        self.canvas.itemconfig("node_text", font=("Arial", new_font_size, "bold"))
        self.canvas.itemconfig("plus_text", font=("Arial", new_font_size, "bold"))

    def on_press(self, event):
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        clicked_items = self.canvas.find_overlapping(canvas_x - 1, canvas_y - 1, canvas_x + 1, canvas_y + 1)
        
        if clicked_items:
            tags = self.canvas.gettags(clicked_items[-1])
            for tag in tags:
                if tag.startswith("plus_click:"):
                    person_name = tag.split("plus_click:")[1]
                    self.open_parent_dialog(person_name)
                    return
                elif tag.startswith("pie_click:"):
                    person_name = tag.split("pie_click:")[1]
                    self.display_ethnic_breakdown(person_name)
                    return
                    
        self.drag_start_x = event.x
        self.drag_start_y = event.y

    def on_drag(self, event):
        dx = event.x - self.drag_start_x
        dy = event.y - self.drag_start_y
        
        self.pan_x += dx
        self.pan_y += dy
        
        self.canvas.move("all", dx, dy)
        self.drag_start_x = event.x
        self.drag_start_y = event.y

    def on_zoom(self, event):
        if event.num == 4 or event.delta > 0:  
            factor = 1.1
        else:                                  
            factor = 0.9
            
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        
        self.pan_x = self.pan_x * factor + cx * (1.0 - factor)
        self.pan_y = self.pan_y * factor + cy * (1.0 - factor)
        self.canvas_scale *= factor
        
        self.canvas.scale("all", cx, cy, factor, factor)
        
        new_font_size = max(1, int(13 * self.canvas_scale))
        self.canvas.itemconfig("node_text", font=("Arial", new_font_size, "bold"))
        self.canvas.itemconfig("plus_text", font=("Arial", new_font_size, "bold"))

    def display_ethnic_breakdown(self, person_name):
        if self.active_breakdown_window is not None:
            try:
                self.active_breakdown_window.destroy()
            except tk.TclError:
                pass 
                
        node = self.tree[person_name]
        self.active_breakdown_window = tk.Toplevel(self.root)
        breakdown_window = self.active_breakdown_window
        
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
        dialog.geometry("560x700")
        dialog.transient(self.root)
        dialog.grab_set()
        
        node = self.tree[person_name]
        
        tk.Label(dialog, text=f"Editing Family Network for:", font=("Arial", 10)).pack(pady=(12,2))
        tk.Label(dialog, text=person_name, font=("Arial", 14, "bold"), fg="#047857").pack(pady=(0,12))
        
        # --- Father Entry Row Layout ---
        f_frame = tk.Frame(dialog)
        f_frame.pack(fill=tk.X, padx=30, pady=(5, 10))
        
        f_name_sub = tk.Frame(f_frame)
        f_name_sub.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(f_name_sub, text="Father's Full Name:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        f_entry = tk.Entry(f_name_sub, font=("Arial", 10), width=30)
        f_entry.insert(0, node.father or "")
        f_entry.pack(anchor=tk.W, pady=(2, 0))
        
        f_eth_sub = tk.Frame(f_frame)
        f_eth_sub.pack(side=tk.RIGHT, padx=(10, 0))
        tk.Label(f_eth_sub, text="Father Ethnicity:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        f_combo = ttk.Combobox(f_eth_sub, values=["None"] + self.ethnicity_options, width=16, state="readonly")
        
        father_node = self.tree.get(node.father) if node.father else None
        init_f_eth = father_node.base_ethnicities[0] if (father_node and father_node.base_ethnicities) else "None"
        if init_f_eth not in self.ethnicity_options: init_f_eth = "None"
        f_combo.set(init_f_eth)
        f_combo.pack(anchor=tk.W, pady=(2, 0))
        
        # --- Mother Entry Row Layout ---
        m_frame = tk.Frame(dialog)
        m_frame.pack(fill=tk.X, padx=30, pady=(5, 15))
        
        m_name_sub = tk.Frame(m_frame)
        m_name_sub.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(m_name_sub, text="Mother's Full Name:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        m_entry = tk.Entry(m_name_sub, font=("Arial", 10), width=30)
        m_entry.insert(0, node.mother or "")
        m_entry.pack(anchor=tk.W, pady=(2, 0))
        
        m_eth_sub = tk.Frame(m_frame)
        m_eth_sub.pack(side=tk.RIGHT, padx=(10, 0))
        tk.Label(m_eth_sub, text="Mother Ethnicity:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        m_combo = ttk.Combobox(m_eth_sub, values=["None"] + self.ethnicity_options, width=16, state="readonly")
        
        mother_node = self.tree.get(node.mother) if node.mother else None
        init_m_eth = mother_node.base_ethnicities[0] if (mother_node and mother_node.base_ethnicities) else "None"
        if init_m_eth not in self.ethnicity_options: init_m_eth = "None"
        m_combo.set(init_m_eth)
        m_combo.pack(anchor=tk.W, pady=(2, 0))
        
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
                
                # Refresh parent dropdown inputs to match custom list additions instantly
                f_combo['values'] = ["None"] + self.ethnicity_options
                m_combo['values'] = ["None"] + self.ethnicity_options
            elif new_eth in self.ethnicity_options:
                messagebox.showwarning("Notice", f"'{new_eth}' is already an option.")

        tk.Button(custom_frame, text="Add & Color", command=add_custom_ethnicity, bg="#cbd5e1", font=("Arial", 9, "bold")).pack(side=tk.LEFT)
        render_checkboxes()

        def save_close():
            old_father = node.father
            old_mother = node.mother
            
            new_father = f_entry.get().strip() or None
            new_mother = m_entry.get().strip() or None
            
            # --- Verification Routine for Duplicate Profiling ---
            if new_father and new_father != old_father and new_father in self.tree:
                confirm = messagebox.askyesno(
                    "Duplicate Profile Detected", 
                    f"A profile named '{new_father}' already exists in the tree.\n\nDo you want to merge/link to this existing profile? Click 'No' to abort and rename."
                )
                if not confirm:
                    messagebox.showinfo("Action Required", "Please change the Father's full name field to a unique description before saving.")
                    return
                    
            if new_mother and new_mother != old_mother and new_mother in self.tree:
                confirm = messagebox.askyesno(
                    "Duplicate Profile Detected", 
                    f"A profile named '{new_mother}' already exists in the tree.\n\nDo you want to merge/link to this existing profile? Click 'No' to abort and rename."
                )
                if not confirm:
                    messagebox.showinfo("Action Required", "Please change the Mother's full name field to a unique description before saving.")
                    return

            selected_ethnicities = [eth for eth, var in vars_dict.items() if var.get()]
            node.base_ethnicities = selected_ethnicities

            # --- Father Link Updates ---
            if old_father != new_father:
                if new_father:
                    if new_father not in self.tree:
                        if old_father and old_father in self.tree:
                            parent_node = self.tree.pop(old_father)
                            parent_node.name = new_father
                            self.tree[new_father] = parent_node
                            for n in self.tree.values():
                                if n.father == old_father: n.father = new_father
                                if n.mother == old_father: n.mother = new_father
                        else:
                            self.tree[new_father] = AncestorNode(new_father)
                node.father = new_father

            # --- Mother Link Updates ---
            if old_mother != new_mother:
                if new_mother:
                    if new_mother not in self.tree:
                        if old_mother and old_mother in self.tree:
                            parent_node = self.tree.pop(old_mother)
                            parent_node.name = new_mother
                            self.tree[new_mother] = parent_node
                            for n in self.tree.values():
                                if n.father == old_mother: n.father = new_mother
                                if n.mother == old_mother: n.mother = new_mother
                        else:
                            self.tree[new_mother] = AncestorNode(new_mother)
                node.mother = new_mother
                
            # --- Apply Custom Dropdown Selection Directly to Profiles ---
            if new_father and new_father in self.tree:
                f_eth = f_combo.get()
                self.tree[new_father].base_ethnicities = [f_eth] if f_eth != "None" else []
                
            if new_mother and new_mother in self.tree:
                m_eth = m_combo.get()
                self.tree[new_mother].base_ethnicities = [m_eth] if m_eth != "None" else []
                
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
        messagebox.showinfo("Saved", "Tree state successfully exported.")

    def load_tree(self, from_welcome=False):
        file_path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if not file_path: 
            return False
            
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
        
        if from_welcome:
            self.welcome_frame.destroy()
            self.setup_ui()
            
        self.reset_view_to_root()
        messagebox.showinfo("Loaded", "Tree configuration imported successfully.")
        return True
        
    def clear_tree(self):
        resp = messagebox.askyesnocancel(
            "Save Changes?", 
            "Would you like to save your current tree database changes before clearing the workspace?"
        )
        
        if resp is True:
            self.save_tree()
        elif resp is None:
            return  
            
        if self.active_breakdown_window:
            self.active_breakdown_window.destroy()
            
        self.tree.clear()
        self.ethnicity_options.clear()
        self.ethnicity_colors.clear()
        
        self.canvas_scale = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        
        for widget in self.root.winfo_children():
            widget.destroy()
            
        self.show_welcome_screen()

if __name__ == "__main__":
    root = tk.Tk()
    app = AncestryApp(root)
    root.mainloop()
