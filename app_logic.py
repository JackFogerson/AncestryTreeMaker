# app_logic.py

import tkinter as tk
from tkinter import messagebox, filedialog, colorchooser, ttk
import json
import math
from models import AncestorNode

# Attempt to load geopy for mapping
try:
    from geopy.geocoders import Nominatim
    GEO_AVAILABLE = True
except ImportError:
    GEO_AVAILABLE = False

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
        self.isolated_root = None
        
        # Initialize geolocator
        if GEO_AVAILABLE:
            self.geolocator = Nominatim(user_agent="ancestor_timeline_mapper")
        else:
            self.geolocator = None

        # Display the starting workflow wizard
        self.show_welcome_screen()

    def show_welcome_screen(self):
        self.welcome_frame = tk.Frame(self.root, bg="#f8fafc")
        self.welcome_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            self.welcome_frame, text="Ancestor Tree Creator",
            font=("Arial", 28, "bold"), bg="#f8fafc", fg="#1e293b"
        ).pack(pady=(150, 10))

        tk.Label(
            self.welcome_frame, text="Select an option below to initialize your lineage tree workspace.",
            font=("Arial", 12), bg="#f8fafc", fg="#64748b"
        ).pack(pady=(0, 40))

        btn_frame = tk.Frame(self.welcome_frame, bg="#f8fafc")
        btn_frame.pack()

        tk.Button(
            btn_frame, text="Create New Tree", command=self.setup_new_tree_input,
            bg="#10b981", fg="white", font=("Arial", 12, "bold"),
            width=22, height=2, bd=0, cursor="hand2"
        ).grid(row=0, column=0, padx=15)

        tk.Button(
            btn_frame, text="Load Existing Tree", command=lambda: self.load_tree(from_welcome=True),
            bg="#2196F3", fg="white", font=("Arial", 12, "bold"),
            width=22, height=2, bd=0, cursor="hand2"
        ).grid(row=0, column=1, padx=15)

    def setup_new_tree_input(self):
        for widget in self.welcome_frame.winfo_children():
            widget.destroy()

        tk.Label(
            self.welcome_frame, text="Ancestor Tree Creator",
            font=("Arial", 28, "bold"), bg="#f8fafc", fg="#1e293b"
        ).pack(pady=(150, 10))

        tk.Label(
            self.welcome_frame, text="Enter the full name of the primary root person:",
            font=("Arial", 12), bg="#f8fafc", fg="#64748b"
        ).pack(pady=(0, 20))

        name_entry = tk.Entry(
            self.welcome_frame, font=("Arial", 14), width=32, bd=1,
            relief=tk.SOLID, highlightthickness=4, highlightbackground="#e2e8f0", highlightcolor="#cbd5e1"
        )
        name_entry.pack(pady=10)
        name_entry.focus_set()

        def confirm_name(event=None):
            name = name_entry.get().strip()
            if not name:
                messagebox.showwarning("Naming Error", "Please provide a valid name to create the root profile.")
                return

            self.tree[name] = AncestorNode(name=name, display_name=name)
            self.welcome_frame.destroy()
            self.setup_ui()
            self.reset_view_to_root()

        name_entry.bind("<Return>", confirm_name)

        tk.Button(
            self.welcome_frame, text="Initialize Workspace", command=confirm_name,
            bg="#10b981", fg="white", font=("Arial", 12, "bold"),
            width=22, height=2, bd=0, cursor="hand2"
        ).pack(pady=20)

    def setup_ui(self):
        control_panel = tk.Frame(self.root, width=250, padx=15, pady=15, bg="#f8fafc")
        control_panel.pack(side=tk.LEFT, fill=tk.Y)

        tk.Label(control_panel, text="File Actions", font=("Arial", 14, "bold"), bg="#f8fafc", fg="#1e293b").pack(anchor=tk.W, pady=(0, 15))

        tk.Button(control_panel, text="Save Tree JSON", command=self.save_tree, bg="#2196F3", fg="white", font=("Arial", 10, "bold"), height=2).pack(fill=tk.X, pady=6)
        tk.Button(control_panel, text="Load Tree JSON", command=lambda: self.load_tree(from_welcome=False), bg="#FF9800", fg="white", font=("Arial", 10, "bold"), height=2).pack(fill=tk.X, pady=6)
        tk.Button(control_panel, text="Clear Tree Workspace", command=self.clear_tree, bg="#f44336", fg="white", font=("Arial", 10, "bold"), height=2).pack(fill=tk.X, pady=6)

        tk.Label(control_panel, text="View Actions", font=("Arial", 14, "bold"), bg="#f8fafc", fg="#1e293b").pack(anchor=tk.W, pady=(20, 15))
        tk.Button(control_panel, text="Toggle Names/Buttons", command=self.toggle_decorations, bg="#475569", fg="white", font=("Arial", 10, "bold"), height=2).pack(fill=tk.X, pady=6)
        tk.Button(control_panel, text="Return to Main View", command=self.reset_isolation, bg="#8b5cf6", fg="white", font=("Arial", 10, "bold"), height=2).pack(fill=tk.X, pady=6)
        tk.Button(control_panel, text="View Map", command=self.open_map_view, bg="#0ea5e9", fg="white", font=("Arial", 10, "bold"), height=2).pack(fill=tk.X, pady=6)

        self.canvas = tk.Canvas(self.root, bg="white", highlightthickness=0)
        self.canvas.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<MouseWheel>", self.on_zoom)
        self.canvas.bind("<Button-4>", self.on_zoom)
        self.canvas.bind("<Button-5>", self.on_zoom)

    # ---------------------------------------------------------
    # MAP VIEW & ANIMATION LOGIC
    # ---------------------------------------------------------
    def open_map_view(self):
        map_win = tk.Toplevel(self.root)
        map_win.title("Geographic Timeline Map")
        map_win.geometry("1400x850")
        map_win.configure(bg="#0f172a")

        # Map Canvas
        self.map_canvas = tk.Canvas(map_win, bg="#1e293b", highlightthickness=0)
        self.map_canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Wait for canvas to draw to get dimensions
        map_win.update_idletasks()
        
        # Control Panel
        ctrl_frame = tk.Frame(map_win, bg="#0f172a")
        ctrl_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Button(ctrl_frame, text="▶ Play Timeline", command=self.play_map, bg="#10b981", fg="white", font=("Arial", 12, "bold"), width=15).pack(side=tk.LEFT, padx=(20, 10))
        tk.Button(ctrl_frame, text="⏸ Pause", command=self.pause_map, bg="#f59e0b", fg="white", font=("Arial", 12, "bold"), width=15).pack(side=tk.LEFT, padx=10)
        tk.Button(ctrl_frame, text="⏪ Restart", command=self.restart_map, bg="#3b82f6", fg="white", font=("Arial", 12, "bold"), width=15).pack(side=tk.LEFT, padx=10)
        
        # Labels for Year and Names (Top Right)
        self.map_year_label = tk.Label(map_win, text="Year: ----", font=("Arial", 28, "bold"), bg="#1e293b", fg="white")
        self.map_year_label.place(relx=0.98, rely=0.05, anchor=tk.NE)
        
        self.map_names_label = tk.Label(map_win, text="", font=("Arial", 12), bg="#1e293b", fg="#cbd5e1", justify=tk.RIGHT)
        self.map_names_label.place(relx=0.98, rely=0.12, anchor=tk.NE)

        self.draw_static_map_background()

        # Find timeline range
        all_years = []
        for node in self.tree.values():
            for loc in node.locations:
                all_years.append(loc['year'])
        
        if not all_years:
            self.map_year_label.config(text="No locations added to any profiles.")
            self.min_year = 0
            self.max_year = 0
            self.current_map_year = 0
        else:
            self.min_year = min(all_years)
            self.max_year = max(all_years)
            self.current_map_year = self.min_year
            self.map_year_label.config(text=f"Year: {self.current_map_year}")
            
        self.map_playing = False
        self.update_map_visuals()

    def draw_static_map_background(self):
        w = self.map_canvas.winfo_width()
        h = self.map_canvas.winfo_height()
        
        mid = w / 2
        
        # NA Background styling
        self.map_canvas.create_rectangle(0, 0, mid, h, fill="#0f172a", outline="")
        self.map_canvas.create_text(mid/2, h - 30, text="North America", fill="#334155", font=("Arial", 24, "bold"))
        
        # EU Background styling
        self.map_canvas.create_rectangle(mid, 0, w, h, fill="#0f172a", outline="")
        self.map_canvas.create_text(mid + (mid/2), h - 30, text="Europe", fill="#334155", font=("Arial", 24, "bold"))
        
        # Center split line
        self.map_canvas.create_line(mid, 0, mid, h, fill="#334155", dash=(4, 4))

    def project_coords(self, lat, lon):
        w = self.map_canvas.winfo_width()
        h = self.map_canvas.winfo_height()
        half_w = w / 2

        # Left Side (North America): Approx Longitude -130 to -60, Latitude 15 to 65
        # Right Side (Europe): Approx Longitude -15 to 45, Latitude 35 to 70

        if lon < -35: # Send to NA side
            x_pct = (lon - (-130)) / 70.0
            y_pct = (lat - 15) / 50.0
            x = x_pct * half_w
            y = h - (y_pct * h)
        else: # Send to EU side
            x_pct = (lon - (-15)) / 60.0
            y_pct = (lat - 35) / 35.0
            x = half_w + (x_pct * half_w)
            y = h - (y_pct * h)
            
        return x, y

    def get_ancestor_position(self, node, current_year):
        if not node.locations:
            return None
        
        # Sort locations by year
        sorted_locs = sorted(node.locations, key=lambda x: x['year'])
        
        first_year = sorted_locs[0]['year']
        last_year = sorted_locs[-1]['year']
        
        if current_year < first_year or current_year > last_year:
            return None # Not on map yet, or disappeared
            
        # Find exact or interpolate
        for i in range(len(sorted_locs) - 1):
            loc_a = sorted_locs[i]
            loc_b = sorted_locs[i+1]
            
            if loc_a['year'] <= current_year <= loc_b['year']:
                if loc_b['year'] == loc_a['year']:
                    return loc_a['lat'], loc_a['lon']
                    
                # Interpolate
                t = (current_year - loc_a['year']) / (loc_b['year'] - loc_a['year'])
                lat = loc_a['lat'] + (loc_b['lat'] - loc_a['lat']) * t
                lon = loc_a['lon'] + (loc_b['lon'] - loc_a['lon']) * t
                return lat, lon
                
        # If exactly on last year
        if current_year == last_year:
            return sorted_locs[-1]['lat'], sorted_locs[-1]['lon']
            
        return None

    def update_map_visuals(self):
        self.map_canvas.delete("dot")
        self.map_year_label.config(text=f"Year: {self.current_map_year}")
        
        active_names = []
        
        for name, node in self.tree.items():
            pos = self.get_ancestor_position(node, self.current_map_year)
            if pos:
                lat, lon = pos
                x, y = self.project_coords(lat, lon)
                
                # Draw dot
                r = 6
                self.map_canvas.create_oval(x-r, y-r, x+r, y+r, fill="#10b981", outline="#ffffff", width=2, tags="dot")
                # Draw name next to dot
                self.map_canvas.create_text(x, y-15, text=node.display_name, fill="#e2e8f0", font=("Arial", 10, "bold"), tags="dot")
                
                active_names.append(node.display_name)
                
        # Update names list on the right
        names_text = "\n".join(active_names[:15]) # Limit to 15 to prevent screen overflow
        if len(active_names) > 15:
            names_text += f"\n... and {len(active_names)-15} more"
            
        self.map_names_label.config(text=names_text)

    def play_map(self):
        if not self.tree or self.max_year == 0: return
        self.map_playing = True
        self._map_loop()

    def pause_map(self):
        self.map_playing = False

    def restart_map(self):
        self.map_playing = False
        self.current_map_year = self.min_year
        self.update_map_visuals()

    def _map_loop(self):
        if self.map_playing:
            self.update_map_visuals()
            self.current_map_year += 1
            if self.current_map_year > self.max_year:
                self.map_playing = False
            else:
                self.root.after(100, self._map_loop)


    # ---------------------------------------------------------
    # CORE UI & TREE LOGIC
    # ---------------------------------------------------------
    def toggle_decorations(self):
        self.show_decorations = not self.show_decorations
        self.refresh_plot()
        
    def reset_isolation(self):
        self.isolated_root = None
        self.reset_view_to_root()

    def isolate_tree(self, person_name):
        self.isolated_root = person_name
        if self.active_breakdown_window:
            self.active_breakdown_window.destroy()
        self.reset_view_to_root()

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

        if self.isolated_root and self.isolated_root in self.tree:
            roots = [self.isolated_root]
        else:
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

        if self.isolated_root and self.isolated_root in self.tree:
            roots = [self.isolated_root]
        else:
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
        if not words: return ""
        if len(words) == 1: return words[0]
        suffixes = {'jr', 'jr.', 'sr', 'sr.', 'iii', 'iv', 'v', 'vi', 'vii', 'viii', 'ix', 'x', '2nd', '3rd', '4th'}
        last_name_idx = len(words) - 1
        while last_name_idx >= 0:
            if words[last_name_idx].lower().strip(',.') not in suffixes: break
            last_name_idx -= 1
        if last_name_idx <= 0: last_name_idx = len(words) - 1
        return f"{' '.join(words[:last_name_idx])}\n{' '.join(words[last_name_idx:])}"

    def refresh_plot(self):
        if not hasattr(self, 'canvas'): return
        self.canvas.delete("all")
        self.calculate_inheritance()
        self.positions = self.calculate_positions()

        if not self.positions: return

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
            self.canvas.create_oval(x - pie_radius, y - pie_radius, x + pie_radius, y + pie_radius, fill="", outline="", tags=(chart_tag, "interactive"))

            if self.show_decorations:
                formatted_name = self.get_formatted_split_name(node.display_name)
                
                if node.birth_year or node.death_year or node.is_living:
                    b_str = node.birth_year if node.birth_year else "?"
                    d_str = "Present" if node.is_living else (node.death_year if node.death_year else "?")
                    formatted_name += f"\n({b_str} - {d_str})"

                text_y = y + pie_radius + 22.0
                lbl = self.canvas.create_text(x, text_y, text=formatted_name, font=("Arial", 13, "bold"), fill="#0f172a", justify=tk.CENTER, tags=("node_text",))

                bbox = self.canvas.bbox(lbl)
                bg_rect = self.canvas.create_rectangle(bbox[0] - 5, bbox[1] - 5, bbox[2] + 5, bbox[3] + 5, fill="#ffffff", outline="#cbd5e1", width=1)
                self.canvas.tag_lower(bg_rect, lbl)

                plus_tag = f"plus_click:{name}"
                plus_y = y - pie_radius - 15.0

                self.canvas.create_rectangle(x - 8, plus_y - 8, x + 8, plus_y + 8, fill="#10b981", outline="#047857", tags=(plus_tag, "interactive"))
                self.canvas.create_text(x, plus_y, text="+", font=("Arial", 13, "bold"), fill="white", tags=(plus_tag, "interactive", "plus_text"))

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
                    self.open_parent_dialog(tag.split("plus_click:")[1])
                    return
                elif tag.startswith("pie_click:"):
                    self.display_ethnic_breakdown(tag.split("pie_click:")[1])
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
        factor = 1.1 if (event.num == 4 or event.delta > 0) else 0.9
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
        if self.active_breakdown_window:
            try: self.active_breakdown_window.destroy()
            except tk.TclError: pass

        node = self.tree[person_name]
        self.active_breakdown_window = tk.Toplevel(self.root)
        bw = self.active_breakdown_window
        bw.title(f"Composition Breakdown: {node.display_name}")
        bw.geometry("380x520")
        bw.configure(bg="#f8fafc")
        bw.transient(self.root)

        tk.Label(bw, text=node.display_name, font=("Arial", 16, "bold"), bg="#f8fafc").pack(pady=(20, 5))
        tk.Label(bw, text="Inherited Ancestry Composition", font=("Arial", 10, "italic"), fg="#64748b", bg="#f8fafc").pack(pady=(0, 15))

        frame_list = tk.Frame(bw, bg="white", bd=1, relief=tk.SOLID, padx=15, pady=15)
        frame_list.pack(fill=tk.BOTH, expand=True, padx=25, pady=(0, 15))

        data = node.computed_ethnicities or {"Unknown": 100.0}
        valid_items = [(k, v) for k, v in data.items() if k != "Unknown"]
        valid_items.sort(key=lambda item: item[1], reverse=True)
        if "Unknown" in data: valid_items.append(("Unknown", data["Unknown"]))

        for eth, pct in valid_items:
            if pct <= 0: continue
            row = tk.Frame(frame_list, bg="white", pady=6)
            row.pack(fill=tk.X)
            color_hex = self.ethnicity_colors.get(eth, "#cbd5e1")
            tk.Frame(row, width=14, height=14, bg=color_hex, bd=1, relief=tk.SOLID).pack(side=tk.LEFT, padx=(0, 10))
            tk.Label(row, text=eth, font=("Arial", 11, "bold" if eth!="Unknown" else "normal"), bg="white").pack(side=tk.LEFT)
            tk.Label(row, text=f"{pct:.2f}%", font=("Arial", 11, "bold"), bg="white").pack(side=tk.RIGHT)

        tk.Button(bw, text="Isolate Ancestors", command=lambda: self.isolate_tree(person_name), bg="#8b5cf6", fg="white", font=("Arial", 10, "bold"), height=2).pack(fill=tk.X, padx=25, pady=(0, 20))


    # ---------------------------------------------------------
    # TABS: PARENT DIALOG
    # ---------------------------------------------------------
    def open_parent_dialog(self, person_name):
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Manage Profile: {person_name}")
        dialog.geometry("650x700")
        dialog.transient(self.root)
        dialog.grab_set()

        node = self.tree[person_name]

        tk.Label(dialog, text=f"Editing Family Network for:", font=("Arial", 10)).pack(pady=(12, 2))
        tk.Label(dialog, text=node.display_name, font=("Arial", 14, "bold"), fg="#047857").pack(pady=(0, 12))

        notebook = ttk.Notebook(dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        tab_parents = tk.Frame(notebook, bg="#f8fafc")
        tab_genetics = tk.Frame(notebook, bg="#f8fafc")
        tab_timeline = tk.Frame(notebook, bg="#f8fafc")

        notebook.add(tab_parents, text="Family Links")
        notebook.add(tab_genetics, text="Genetics Base")
        notebook.add(tab_timeline, text="Timeline & Map")

        # --- TAB 1: PARENTS ---
        def create_parent_block(parent_frame, title_str, node_attr, is_father):
            group = tk.LabelFrame(parent_frame, text=title_str, font=("Arial", 10, "bold"), padx=10, pady=10, bg="#f8fafc")
            group.pack(fill=tk.X, padx=15, pady=(15, 10))

            r1 = tk.Frame(group, bg="#f8fafc")
            r1.pack(fill=tk.X)
            tk.Label(r1, text="Full Name:", font=("Arial", 9, "bold"), width=10, anchor=tk.W, bg="#f8fafc").pack(side=tk.LEFT)
            name_entry = tk.Entry(r1, font=("Arial", 10), width=24)
            name_entry.pack(side=tk.LEFT, padx=(0, 15))

            tk.Label(r1, text="Ethnicity:", font=("Arial", 9, "bold"), anchor=tk.W, bg="#f8fafc").pack(side=tk.LEFT, padx=(0, 5))
            combo = ttk.Combobox(r1, values=["None"] + self.ethnicity_options, width=14, state="readonly")
            combo.pack(side=tk.LEFT)

            r2 = tk.Frame(group, bg="#f8fafc")
            r2.pack(fill=tk.X, pady=(10, 0))
            tk.Label(r2, text="Birth Year:", font=("Arial", 9, "bold"), width=10, anchor=tk.W, bg="#f8fafc").pack(side=tk.LEFT)
            birth_entry = tk.Entry(r2, font=("Arial", 10), width=10)
            birth_entry.pack(side=tk.LEFT, padx=(0, 15))

            tk.Label(r2, text="Death Year:", font=("Arial", 9, "bold"), anchor=tk.W, bg="#f8fafc").pack(side=tk.LEFT, padx=(0, 5))
            death_entry = tk.Entry(r2, font=("Arial", 10), width=10)
            death_entry.pack(side=tk.LEFT, padx=(0, 10))

            living_var = tk.BooleanVar()
            def toggle_death():
                if living_var.get():
                    death_entry.delete(0, tk.END)
                    death_entry.config(state=tk.DISABLED)
                else:
                    death_entry.config(state=tk.NORMAL)

            tk.Checkbutton(r2, text="Currently Living", variable=living_var, command=toggle_death, bg="#f8fafc").pack(side=tk.LEFT)

            parent_n = self.tree.get(node_attr) if node_attr else None
            if parent_n:
                name_entry.insert(0, parent_n.display_name)
                birth_entry.insert(0, parent_n.birth_year)
                if parent_n.is_living:
                    living_var.set(True)
                    toggle_death()
                else:
                    death_entry.insert(0, parent_n.death_year)
                init_eth = parent_n.base_ethnicities[0] if parent_n.base_ethnicities else "None"
            else:
                name_entry.insert(0, node_attr or "")
                init_eth = "None"
                
            if init_eth not in self.ethnicity_options: init_eth = "None"
            combo.set(init_eth)
            return name_entry, birth_entry, death_entry, living_var, combo

        f_entries = create_parent_block(tab_parents, " Father's Profile ", node.father, True)
        m_entries = create_parent_block(tab_parents, " Mother's Profile ", node.mother, False)


        # --- TAB 2: GENETICS ---
        c_frame = tk.Frame(tab_genetics, bg="#f8fafc")
        c_frame.pack(fill=tk.X, padx=15, pady=(15, 10))
        tk.Label(c_frame, text="Add New Ethnicity:", font=("Arial", 10, "bold"), bg="#f8fafc").pack(side=tk.LEFT)
        new_eth_entry = tk.Entry(c_frame, width=15, font=("Arial", 10))
        new_eth_entry.pack(side=tk.LEFT, padx=5)

        cb_frame = tk.LabelFrame(tab_genetics, text=" Select Origins (Base Profile) ", padx=10, pady=10, bg="#f8fafc")
        cb_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        vars_dict = {}

        def pick_edit_color(ethnicity):
            clr = colorchooser.askcolor(initialcolor=self.ethnicity_colors.get(ethnicity, "#cbd5e1"))
            if clr[1]:
                self.ethnicity_colors[ethnicity] = clr[1]
                render_checkboxes()

        def render_checkboxes():
            for widget in cb_frame.winfo_children(): widget.destroy()
            vars_dict.clear()
            for idx, eth in enumerate(self.ethnicity_options):
                var = tk.BooleanVar(value=(eth in node.base_ethnicities))
                vars_dict[eth] = var
                r, c = idx // 2, (idx % 2) * 2
                tk.Checkbutton(cb_frame, text=eth, variable=var, font=("Arial", 9), bg="#f8fafc").grid(row=r, column=c, sticky=tk.W, padx=(5, 2), pady=3)
                lbl = tk.Label(cb_frame, bg=self.ethnicity_colors.get(eth, "#cbd5e1"), width=3, relief=tk.RAISED, cursor="hand2")
                lbl.grid(row=r, column=c+1, sticky=tk.W, padx=(0, 15))
                lbl.bind("<Button-1>", lambda e, e_name=eth: pick_edit_color(e_name))

        def add_eth():
            new_eth = new_eth_entry.get().strip().title()
            if new_eth and new_eth not in self.ethnicity_options:
                clr = colorchooser.askcolor()[1] or "#cbd5e1"
                self.ethnicity_options.append(new_eth)
                self.ethnicity_colors[new_eth] = clr
                new_eth_entry.delete(0, tk.END)
                render_checkboxes()
                f_entries[4]['values'] = ["None"] + self.ethnicity_options
                m_entries[4]['values'] = ["None"] + self.ethnicity_options

        tk.Button(c_frame, text="Add", command=add_eth, bg="#cbd5e1", font=("Arial", 9, "bold")).pack(side=tk.LEFT)
        render_checkboxes()

        # --- TAB 3: TIMELINE & LOCATIONS ---
        loc_top = tk.Frame(tab_timeline, bg="#f8fafc")
        loc_top.pack(fill=tk.X, padx=15, pady=15)
        
        tk.Label(loc_top, text="Year:", font=("Arial", 9, "bold"), bg="#f8fafc").pack(side=tk.LEFT)
        loc_year_entry = tk.Entry(loc_top, width=8, font=("Arial", 10))
        loc_year_entry.pack(side=tk.LEFT, padx=(5, 15))
        
        tk.Label(loc_top, text="Location (e.g. Baltimore, MD):", font=("Arial", 9, "bold"), bg="#f8fafc").pack(side=tk.LEFT)
        loc_place_entry = tk.Entry(loc_top, width=20, font=("Arial", 10))
        loc_place_entry.pack(side=tk.LEFT, padx=(5, 10))
        
        loc_list = tk.Listbox(tab_timeline, font=("Arial", 10))
        loc_list.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)
        
        def refresh_loc_list():
            loc_list.delete(0, tk.END)
            node.locations.sort(key=lambda x: x['year'])
            for loc in node.locations:
                loc_list.insert(tk.END, f"{loc['year']} - {loc['place']} (Lat: {loc['lat']:.2f}, Lon: {loc['lon']:.2f})")
                
        refresh_loc_list()

        def add_location():
            if not GEO_AVAILABLE:
                messagebox.showerror("Dependency Missing", "Please install geopy to use this feature.\nCommand: pip install geopy")
                return
            
            try: year_val = int(loc_year_entry.get().strip())
            except ValueError:
                messagebox.showwarning("Input Error", "Year must be a valid number.")
                return
                
            place = loc_place_entry.get().strip()
            if not place: return
            
            try:
                # Geocode the location
                location = self.geolocator.geocode(place)
                if location:
                    node.locations.append({
                        'year': year_val,
                        'place': location.address.split(',')[0] + " (" + place + ")",
                        'lat': location.latitude,
                        'lon': location.longitude
                    })
                    loc_year_entry.delete(0, tk.END)
                    loc_place_entry.delete(0, tk.END)
                    refresh_loc_list()
                else:
                    messagebox.showwarning("Not Found", f"Could not find coordinates for: {place}")
            except Exception as e:
                messagebox.showerror("Network Error", f"Geocoding failed: {str(e)}")

        def remove_location():
            sel = loc_list.curselection()
            if sel:
                del node.locations[sel[0]]
                refresh_loc_list()

        btn_loc_frame = tk.Frame(tab_timeline, bg="#f8fafc")
        btn_loc_frame.pack(fill=tk.X, padx=15, pady=(0,15))
        tk.Button(loc_top, text="Search & Add", command=add_location, bg="#3b82f6", fg="white", font=("Arial", 9, "bold")).pack(side=tk.LEFT)
        tk.Button(btn_loc_frame, text="Remove Selected", command=remove_location, bg="#ef4444", fg="white", font=("Arial", 9)).pack(side=tk.RIGHT)

        # --- SAVE FUNCTION ---
        def save_close():
            old_f, old_m = node.father, node.mother
            f_n, f_b, f_d, f_l, f_c = f_entries[0].get().strip(), f_entries[1].get().strip(), f_entries[2].get().strip(), f_entries[3].get(), f_entries[4].get()
            m_n, m_b, m_d, m_l, m_c = m_entries[0].get().strip(), m_entries[1].get().strip(), m_entries[2].get().strip(), m_entries[3].get(), m_entries[4].get()

            def gen_id(n, b, d, l):
                if not n: return None
                if not b and not d and not l: return n
                b_str = b if b else "?"
                d_str = "Present" if l else (d if d else "?")
                return f"{n} ({b_str} - {d_str})"

            new_f_id = gen_id(f_n, f_b, f_d, f_l)
            new_m_id = gen_id(m_n, m_b, m_d, m_l)

            if new_f_id and new_f_id != old_f and new_f_id in self.tree and not messagebox.askyesno("Duplicate", f"Profile '{new_f_id}' exists. Link to it?"): return
            if new_m_id and new_m_id != old_m and new_m_id in self.tree and not messagebox.askyesno("Duplicate", f"Profile '{new_m_id}' exists. Link to it?"): return

            node.base_ethnicities = [eth for eth, var in vars_dict.items() if var.get()]

            def update_parent(old_id, new_id, p_n, p_b, p_d, p_l, p_c, is_father):
                if old_id != new_id:
                    if new_id and new_id not in self.tree:
                        if old_id and old_id in self.tree:
                            p_node = self.tree.pop(old_id)
                            p_node.name, p_node.display_name, p_node.birth_year, p_node.death_year, p_node.is_living = new_id, p_n, p_b, "" if p_l else p_d, p_l
                            self.tree[new_id] = p_node
                            for n in self.tree.values():
                                if n.father == old_id: n.father = new_id
                                if n.mother == old_id: n.mother = new_id
                        else:
                            self.tree[new_id] = AncestorNode(name=new_id, display_name=p_n, birth_year=p_b, death_year="" if p_l else p_d, is_living=p_l)
                    if is_father: node.father = new_id
                    else: node.mother = new_id
                else:
                    if new_id and new_id in self.tree:
                        p_node = self.tree[new_id]
                        p_node.display_name, p_node.birth_year, p_node.death_year, p_node.is_living = p_n, p_b, "" if p_l else p_d, p_l

                if new_id and new_id in self.tree and p_c != "None":
                    self.tree[new_id].base_ethnicities = [p_c]

            update_parent(old_f, new_f_id, f_n, f_b, f_d, f_l, f_c, True)
            update_parent(old_m, new_m_id, m_n, m_b, m_d, m_l, m_c, False)

            dialog.destroy()
            self.refresh_plot()

        tk.Button(dialog, text="Save & Update Tree", command=save_close, bg="#10b981", fg="white", font=("Arial", 11, "bold"), width=20, height=2).pack(pady=(5,15))


    # ---------------------------------------------------------
    # FILE I/O
    # ---------------------------------------------------------
    def save_tree(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")])
        if not file_path: return

        data = {
            "master_ethnicities": self.ethnicity_options,
            "ethnicity_colors": self.ethnicity_colors,
            "nodes": {}
        }
        for name, n in self.tree.items():
            data["nodes"][name] = {
                "name": n.name, "display_name": n.display_name, "birth_year": n.birth_year,
                "death_year": n.death_year, "is_living": n.is_living, "base_ethnicities": n.base_ethnicities,
                "father": n.father, "mother": n.mother, "locations": n.locations
            }

        with open(file_path, 'w') as f: json.dump(data, f, indent=4)
        messagebox.showinfo("Saved", "Tree exported.")

    def load_tree(self, from_welcome=False):
        file_path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if not file_path: return False

        with open(file_path, 'r') as f: raw = json.load(f)

        self.tree.clear()
        self.ethnicity_options = raw.get("master_ethnicities", [])
        self.ethnicity_colors = raw.get("ethnicity_colors", {})

        for name, d in raw.get("nodes", {}).items():
            self.tree[name] = AncestorNode(
                name=d["name"], display_name=d.get("display_name", d["name"]),
                birth_year=d.get("birth_year", ""), death_year=d.get("death_year", ""),
                is_living=d.get("is_living", False), base_ethnicities=d.get("base_ethnicities", []),
                father=d.get("father"), mother=d.get("mother"), locations=d.get("locations", [])
            )

        if from_welcome:
            self.welcome_frame.destroy()
            self.setup_ui()

        self.isolated_root = None
        self.reset_view_to_root()
        messagebox.showinfo("Loaded", "Tree imported.")
        return True

    def clear_tree(self):
        resp = messagebox.askyesnocancel("Save Changes?", "Save changes before clearing?")
        if resp is True: self.save_tree()
        elif resp is None: return

        if self.active_breakdown_window: self.active_breakdown_window.destroy()
        self.tree.clear()
        self.ethnicity_options.clear()
        self.ethnicity_colors.clear()
        self.canvas_scale, self.pan_x, self.pan_y = 1.0, 0.0, 0.0
        self.isolated_root = None

        for w in self.root.winfo_children(): w.destroy()
        self.show_welcome_screen()
