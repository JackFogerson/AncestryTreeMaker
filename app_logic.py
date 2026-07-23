# app_logic.py

import tkinter as tk
from tkinter import messagebox, filedialog, colorchooser, ttk
import json
import math
import io
from models import AncestorNode

# Attempt to load requests for reliable web scraping
try:
    import requests

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# Attempt to load geopy for mapping
try:
    from geopy.geocoders import Nominatim

    GEO_AVAILABLE = True
except ImportError:
    GEO_AVAILABLE = False

# Attempt to load Cartopy and Matplotlib for the map
try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature

    MAP_AVAILABLE = True
except ImportError:
    MAP_AVAILABLE = False


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

            node = AncestorNode(name=name, display_name=name)
            node.signifiers = []
            self.tree[name] = node
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

        tk.Label(control_panel, text="File Actions", font=("Arial", 14, "bold"), bg="#f8fafc", fg="#1e293b").pack(
            anchor=tk.W, pady=(0, 15))

        tk.Button(control_panel, text="Save Tree JSON", command=self.save_tree, bg="#2196F3", fg="white",
                  font=("Arial", 10, "bold"), height=2).pack(fill=tk.X, pady=6)
        tk.Button(control_panel, text="Load Tree JSON", command=lambda: self.load_tree(from_welcome=False),
                  bg="#FF9800", fg="white", font=("Arial", 10, "bold"), height=2).pack(fill=tk.X, pady=6)
        tk.Button(control_panel, text="Clear Tree Workspace", command=self.clear_tree, bg="#f44336", fg="white",
                  font=("Arial", 10, "bold"), height=2).pack(fill=tk.X, pady=6)

        tk.Label(control_panel, text="View Actions", font=("Arial", 14, "bold"), bg="#f8fafc", fg="#1e293b").pack(
            anchor=tk.W, pady=(20, 15))
        tk.Button(control_panel, text="Toggle Names/Buttons", command=self.toggle_decorations, bg="#475569", fg="white",
                  font=("Arial", 10, "bold"), height=2).pack(fill=tk.X, pady=6)
        tk.Button(control_panel, text="Return to Main View", command=self.reset_isolation, bg="#8b5cf6", fg="white",
                  font=("Arial", 10, "bold"), height=2).pack(fill=tk.X, pady=6)
        tk.Button(control_panel, text="View Map", command=self.open_map_view, bg="#0ea5e9", fg="white",
                  font=("Arial", 10, "bold"), height=2).pack(fill=tk.X, pady=6)

        self.canvas = tk.Canvas(self.root, bg="white", highlightthickness=0)
        self.canvas.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<MouseWheel>", self.on_zoom)
        self.canvas.bind("<Button-4>", self.on_zoom)
        self.canvas.bind("<Button-5>", self.on_zoom)

    # ---------------------------------------------------------
    # MAP VIEW & ANIMATION LOGIC (CARTOPY)
    # ---------------------------------------------------------
    def open_map_view(self):
        if not MAP_AVAILABLE:
            messagebox.showerror("Missing Dependencies",
                                 "Please install cartopy and matplotlib to use this feature.\nCommand: pip install cartopy matplotlib")
            return

        map_win = tk.Toplevel(self.root)
        map_win.title("Geographic Timeline Map")
        map_win.geometry("1400x850")
        map_win.configure(bg="#0f172a")

        # Animation State
        self.map_playing = False
        self.is_moving = False
        self.move_t = 1.0
        self.timeline_speed = 800
        self.scatter_points = []

        # --- Top Control Panel ---
        ctrl_frame = tk.Frame(map_win, bg="#0f172a")
        ctrl_frame.pack(fill=tk.X, pady=(10, 10))

        tk.Button(ctrl_frame, text="▶ Play Timeline", command=self.play_map, bg="#10b981", fg="white",
                  font=("Arial", 11, "bold"), width=15).pack(side=tk.LEFT, padx=(20, 10))
        tk.Button(ctrl_frame, text="⏸ Pause", command=self.pause_map, bg="#f59e0b", fg="white",
                  font=("Arial", 11, "bold"), width=15).pack(side=tk.LEFT, padx=10)
        tk.Button(ctrl_frame, text="⏪ Restart", command=self.restart_map, bg="#3b82f6", fg="white",
                  font=("Arial", 11, "bold"), width=15).pack(side=tk.LEFT, padx=10)

        tk.Frame(ctrl_frame, width=2, bg="#334155").pack(side=tk.LEFT, fill=tk.Y, padx=15, pady=5)

        tk.Label(ctrl_frame, text="Map Bounds:", bg="#0f172a", fg="white", font=("Arial", 11, "bold")).pack(
            side=tk.LEFT, padx=(0, 5))

        self.view_var = tk.StringVar(value="Global")
        view_drop = ttk.Combobox(ctrl_frame, textvariable=self.view_var,
                                 values=["Global", "North America & Europe", "Custom"], state="readonly", width=22)
        view_drop.pack(side=tk.LEFT, padx=5)

        self.bounds_frame = tk.Frame(ctrl_frame, bg="#0f172a")

        tk.Label(self.bounds_frame, text="Lon(Min/Max):", bg="#0f172a", fg="#cbd5e1").pack(side=tk.LEFT)
        self.lon_min_ent = tk.Entry(self.bounds_frame, width=5)
        self.lon_min_ent.pack(side=tk.LEFT, padx=2)
        self.lon_min_ent.insert(0, "-140")

        self.lon_max_ent = tk.Entry(self.bounds_frame, width=5)
        self.lon_max_ent.pack(side=tk.LEFT, padx=2)
        self.lon_max_ent.insert(0, "45")

        tk.Label(self.bounds_frame, text=" Lat(Min/Max):", bg="#0f172a", fg="#cbd5e1").pack(side=tk.LEFT)
        self.lat_min_ent = tk.Entry(self.bounds_frame, width=5)
        self.lat_min_ent.pack(side=tk.LEFT, padx=2)
        self.lat_min_ent.insert(0, "20")

        self.lat_max_ent = tk.Entry(self.bounds_frame, width=5)
        self.lat_max_ent.pack(side=tk.LEFT, padx=2)
        self.lat_max_ent.insert(0, "90")

        def apply_custom():
            try:
                lon_m = float(self.lon_min_ent.get())
                lon_x = float(self.lon_max_ent.get())
                lat_m = float(self.lat_min_ent.get())
                lat_x = float(self.lat_max_ent.get())
                self.map_ax.set_extent([lon_m, lon_x, lat_m, lat_x], crs=ccrs.PlateCarree())
                self.canvas_widget.draw_idle()
            except ValueError:
                messagebox.showerror("Invalid Input", "Please enter valid numeric boundaries.")

        tk.Button(self.bounds_frame, text="Apply", command=apply_custom, bg="#64748b", fg="white").pack(side=tk.LEFT,
                                                                                                        padx=5)

        def on_view_change(event):
            val = self.view_var.get()
            if val == "Global":
                self.bounds_frame.pack_forget()
                self.map_ax.set_global()
                self.canvas_widget.draw_idle()
            elif val == "North America & Europe":
                self.bounds_frame.pack_forget()
                self.map_ax.set_extent([-140, 45, 20, 90], crs=ccrs.PlateCarree())
                self.canvas_widget.draw_idle()
            elif val == "Custom":
                self.bounds_frame.pack(side=tk.LEFT, padx=5)

        view_drop.bind("<<ComboboxSelected>>", on_view_change)

        # --- Right Info Panel ---
        info_frame = tk.Frame(map_win, bg="#1e293b", width=250)
        info_frame.pack(side=tk.RIGHT, fill=tk.Y)
        info_frame.pack_propagate(False)

        tk.Label(info_frame, text="Current Year", font=("Arial", 12, "bold"), bg="#1e293b", fg="#94a3b8").pack(
            pady=(20, 0))
        self.map_year_label = tk.Label(info_frame, text="----", font=("Arial", 32, "bold"), bg="#1e293b", fg="white")
        self.map_year_label.pack(pady=(0, 20))

        tk.Label(info_frame, text="Living Ancestors", font=("Arial", 12, "bold", "underline"), bg="#1e293b",
                 fg="#94a3b8").pack(pady=(10, 5))

        self.map_names_label = tk.Label(info_frame, text="", font=("Arial", 11), bg="#1e293b", fg="#cbd5e1",
                                        justify=tk.CENTER)
        self.map_names_label.pack(pady=5)

        # --- Matplotlib Canvas Setup (Full Space & Margins Removed) ---
        self.map_fig = plt.Figure(figsize=(12, 8), dpi=100, facecolor='#0f172a')
        self.map_fig.subplots_adjust(left=0.0, right=1.0, bottom=0.0, top=1.0)
        self.map_ax = self.map_fig.add_subplot(1, 1, 1, projection=ccrs.Robinson())
        self.map_ax.set_facecolor('#0f172a')

        self.map_ax.add_feature(cfeature.OCEAN, facecolor='#0f172a')
        self.map_ax.add_feature(cfeature.LAND, facecolor='#334155', edgecolor='#475569')
        self.map_ax.add_feature(cfeature.BORDERS, linestyle=':', edgecolor='#64748b')
        self.map_ax.set_global()

        self.map_annot = self.map_ax.annotate("", xy=(0, 0), xytext=(10, 10), textcoords="offset points",
                                              bbox=dict(boxstyle="round,pad=0.4", fc="#f8fafc", ec="#94a3b8", lw=1),
                                              color="#0f172a", fontsize=10, weight="bold", zorder=10)
        self.map_annot.set_visible(False)

        self.canvas_widget = FigureCanvasTkAgg(self.map_fig, master=map_win)
        self.canvas_widget.get_tk_widget().pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas_widget.mpl_connect("motion_notify_event", self.on_map_hover)

        # Scroll Wheel Zoom Support for Map
        def on_map_scroll(event):
            if event.inaxes != self.map_ax:
                return
            extent = self.map_ax.get_extent(crs=ccrs.PlateCarree())
            lon_min, lon_max, lat_min, lat_max = extent
            factor = 0.9 if (event.num == 4 or event.delta > 0) else 1.1
            lon_center = (lon_min + lon_max) / 2
            lat_center = (lat_min + lat_max) / 2
            lon_span = (lon_max - lon_min) * factor
            lat_span = (lat_max - lat_min) * factor
            new_extent = [
                lon_center - lon_span / 2,
                lon_center + lon_span / 2,
                lat_center - lat_span / 2,
                lat_center + lat_span / 2
            ]
            try:
                self.map_ax.set_extent(new_extent, crs=ccrs.PlateCarree())
                self.canvas_widget.draw_idle()
            except Exception:
                pass

        self.canvas_widget.mpl_connect("scroll_event", on_map_scroll)

        self.drawn_artists = []

        all_years = []
        for node in self.tree.values():
            for loc in node.locations:
                all_years.append(loc['year'])
            if node.birth_year and node.birth_year.isdigit():
                all_years.append(int(node.birth_year))
            if node.death_year and node.death_year.isdigit():
                all_years.append(int(node.death_year))

        if not all_years:
            self.map_year_label.config(text="----")
            self.min_year = 0
            self.max_year = 0
            self.current_map_year = 0
        else:
            self.min_year = min(all_years)
            self.max_year = max(all_years)
            self.current_map_year = self.min_year
            self.map_year_label.config(text=f"{self.current_map_year}")

        self.update_map_visuals()

        def on_closing():
            self.map_playing = False
            plt.close(self.map_fig)
            map_win.destroy()

        map_win.protocol("WM_DELETE_WINDOW", on_closing)

    def on_map_hover(self, event):
        if event.inaxes != self.map_ax:
            if self.map_annot.get_visible():
                self.map_annot.set_visible(False)
                self.canvas_widget.draw_idle()
            return

        point_groups = {}
        for lon, lat, name, is_active in self.scatter_points:
            if not is_active:
                continue  # Only include living/active people in hover names
            r_pt = ccrs.Robinson().transform_point(lon, lat, ccrs.Geodetic())
            xy = self.map_ax.transData.transform(r_pt)
            dist = (xy[0] - event.x) ** 2 + (xy[1] - event.y) ** 2
            if dist < 400:
                key = (round(lon, 4), round(lat, 4))
                if key not in point_groups:
                    point_groups[key] = {'names': [], 'r_pt': r_pt, 'min_dist': dist}
                if name not in point_groups[key]['names']:
                    point_groups[key]['names'].append(name)
                if dist < point_groups[key]['min_dist']:
                    point_groups[key]['min_dist'] = dist

        best_group = None
        lowest_dist = float('inf')
        for key, group in point_groups.items():
            if group['min_dist'] < lowest_dist:
                lowest_dist = group['min_dist']
                best_group = group

        if best_group:
            names_str = "\n".join(best_group['names'])
            r_pt = best_group['r_pt']
            if not self.map_annot.get_visible() or self.map_annot.get_text() != names_str:
                self.map_annot.xy = (r_pt[0], r_pt[1])
                self.map_annot.set_text(names_str)
                self.map_annot.set_visible(True)
                self.canvas_widget.draw_idle()
        else:
            if self.map_annot.get_visible():
                self.map_annot.set_visible(False)
                self.canvas_widget.draw_idle()

    def update_map_visuals(self, t=1.0):
        if self.max_year > 0:
            self.map_year_label.config(text=f"{self.current_map_year}")

        for artist in self.drawn_artists:
            try:
                artist.remove()
            except ValueError:
                pass
        self.drawn_artists.clear()
        self.scatter_points.clear()

        active_names = []

        for name, node in self.tree.items():
            node_years = [loc['year'] for loc in node.locations]
            if node.birth_year and node.birth_year.isdigit():
                node_years.append(int(node.birth_year))
            if node.death_year and node.death_year.isdigit():
                node_years.append(int(node.death_year))

            if not node_years:
                continue

            first_year = min(node_years)
            if node.is_living:
                last_year = max(self.max_year, first_year)
            elif node.death_year and node.death_year.isdigit():
                last_year = int(node.death_year)
            elif node.locations:
                last_year = sorted(node.locations, key=lambda x: x['year'])[-1]['year']
            elif node.birth_year and node.birth_year.isdigit():
                last_year = int(node.birth_year) + 80
            else:
                last_year = first_year

            if first_year <= self.current_map_year <= last_year:
                active_names.append(node.display_name)

            valid_locs = [loc for loc in sorted(node.locations, key=lambda x: x['year']) if loc.get('lat') is not None and loc.get('lon') is not None and loc['year'] <= self.current_map_year]
            if not valid_locs:
                continue

            is_active = self.current_map_year <= last_year
            is_moving_now = (self.current_map_year == valid_locs[-1]['year']) and (len(valid_locs) > 1) and (t < 1.0)

            if is_moving_now:
                prev_loc = valid_locs[-2]
                target_loc = valid_locs[-1]

                curr_lat = prev_loc['lat'] + (target_loc['lat'] - prev_loc['lat']) * t
                curr_lon = prev_loc['lon'] + (target_loc['lon'] - prev_loc['lon']) * t

                past_lats = [loc['lat'] for loc in valid_locs[:-1]]
                past_lons = [loc['lon'] for loc in valid_locs[:-1]]
                moving_lats = [prev_loc['lat'], curr_lat]
                moving_lons = [prev_loc['lon'], curr_lon]
            else:
                curr_lat = valid_locs[-1]['lat']
                curr_lon = valid_locs[-1]['lon']

                past_lats = [loc['lat'] for loc in valid_locs]
                past_lons = [loc['lon'] for loc in valid_locs]
                moving_lats = []
                moving_lons = []

            # Visited past location dots are faded like dead people
            if len(valid_locs) > 1:
                visited_lats = [loc['lat'] for loc in valid_locs[:-1]]
                visited_lons = [loc['lon'] for loc in valid_locs[:-1]]
                if visited_lats:
                    faded_dots = self.map_ax.scatter(visited_lons, visited_lats, color='#475569',
                                                     edgecolor='#94a3b8', s=30, transform=ccrs.Geodetic(),
                                                     zorder=3, alpha=0.6)
                    self.drawn_artists.append(faded_dots)

            # Historical trail lines (faded)
            if len(past_lats) > 1:
                trail, = self.map_ax.plot(past_lons, past_lats, color='#475569', linewidth=1.5,
                                          linestyle='--', transform=ccrs.Geodetic(), alpha=0.4)
                self.drawn_artists.append(trail)

            # Active moving line that follows as they move to that place, fading once move occurs
            if is_moving_now and len(moving_lats) > 1:
                moving_line, = self.map_ax.plot(moving_lons, moving_lats, color='#10b981', linewidth=2.5,
                                                linestyle='-', transform=ccrs.Geodetic(), alpha=0.9, zorder=5)
                self.drawn_artists.append(moving_line)

            dot_color = '#10b981' if is_active else '#475569'
            dot_edge = '#ffffff' if is_active else '#94a3b8'
            dot_alpha = 1.0 if is_active else 0.6
            dot_size = 60 if is_active else 40

            main_dot = self.map_ax.scatter([curr_lon], [curr_lat], color=dot_color,
                                           edgecolor=dot_edge, s=dot_size, transform=ccrs.Geodetic(),
                                           zorder=4, alpha=dot_alpha)

            self.scatter_points.append((curr_lon, curr_lat, node.display_name, is_active))
            self.drawn_artists.append(main_dot)

        self.canvas_widget.draw_idle()

        names_text = "\n".join(active_names[:25])
        if len(active_names) > 25:
            names_text += f"\n... and {len(active_names) - 25} more"

        self.map_names_label.config(text=names_text)

    def play_map(self):
        if not self.tree or self.max_year == 0: return
        if not self.map_playing:
            self.map_playing = True
            if self.is_moving:
                self._movement_loop()
            else:
                self._map_loop()

    def pause_map(self):
        self.map_playing = False

    def restart_map(self):
        self.map_playing = False
        self.is_moving = False
        self.move_t = 1.0
        self.current_map_year = self.min_year
        self.update_map_visuals()

    def _map_loop(self):
        if not self.map_playing: return

        self.current_map_year += 1

        if self.current_map_year > self.max_year:
            self.map_playing = False
            self.update_map_visuals()
            return

        needs_movement = False
        for node in self.tree.values():
            if not node.locations: continue

            sorted_locs = sorted(node.locations, key=lambda x: x['year'])
            valid_locs = [loc for loc in sorted_locs if loc.get('lat') is not None and loc.get('lon') is not None and loc['year'] <= self.current_map_year]

            if valid_locs and valid_locs[-1]['year'] == self.current_map_year and len(valid_locs) > 1:
                needs_movement = True
                break

        if needs_movement:
            self.is_moving = True
            self.move_t = 0.0
            self._movement_loop()
        else:
            self.update_map_visuals(t=1.0)
            self.root.after(self.timeline_speed, self._map_loop)

    def _movement_loop(self):
        if not self.map_playing: return

        self.move_t += 0.05

        if self.move_t >= 1.0:
            self.move_t = 1.0
            self.update_map_visuals(t=1.0)
            self.is_moving = False
            self.root.after(self.timeline_speed, self._map_loop)
        else:
            self.update_map_visuals(t=self.move_t)
            self.root.after(int(self.timeline_speed / 20), self._movement_loop)

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
        if name in visited or name not in self.tree: return
        visited.add(name)

        node = self.tree[name]

        if node.father or node.mother:
            if node.father: self._compute_node_heritage(node.father, visited)
            if node.mother: self._compute_node_heritage(node.mother, visited)

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
        if name not in self.tree: return 1
        if name in memo: return memo[name]
        node = self.tree[name]
        if not node.father and not node.mother: return 1
        f_leaves = self._count_leaves(node.father, memo) if node.father else 0
        m_leaves = self._count_leaves(node.mother, memo) if node.mother else 0
        memo[name] = max(1, f_leaves + m_leaves)
        return memo[name]

    def _get_max_depth(self, name, visited):
        if name in visited or name not in self.tree: return 0
        visited.add(name)
        node = self.tree[name]
        f_depth = self._get_max_depth(node.father, visited) if node.father else 0
        m_depth = self._get_max_depth(node.mother, visited) if node.mother else 0
        return 1 + max(f_depth, m_depth)

    def calculate_positions(self):
        positions = {}
        if not self.tree: return positions

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

        if not self.positions: return

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
            self.canvas.create_oval(x - radius, y - radius, x + radius, y + radius, fill="#e2e8f0", outline="#cbd5e1",
                                    width=1)
            return

        sorted_eth = sorted(active_eth.items(), key=lambda item: item[1], reverse=True)
        largest_eth, largest_val = sorted_eth[0]
        base_color = '#e2e8f0' if largest_eth == "Unknown" else self.ethnicity_colors.get(largest_eth, '#e2e8f0')

        self.canvas.create_oval(x - radius, y - radius, x + radius, y + radius, fill=base_color, outline="#cbd5e1",
                                width=1)

        if len(active_eth) == 1: return

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
            self.canvas.create_oval(x - pie_radius, y - pie_radius, x + pie_radius, y + pie_radius, fill="", outline="",
                                    tags=(chart_tag, "interactive", "pie"))

            if self.show_decorations:
                text_y = y + pie_radius + 14.0
                node_items = []

                # Line 1: Name (Bold)
                formatted_name = self.get_formatted_split_name(node.display_name)
                lbl_name = self.canvas.create_text(x, text_y, text=formatted_name, font=("Arial", 13, "bold"),
                                                   fill="#0f172a", justify=tk.CENTER, tags=("node_name",))
                node_items.append(lbl_name)

                bbox_name = self.canvas.bbox(lbl_name)
                current_y = bbox_name[3] + 4 if bbox_name else text_y + 20

                # Line 2: Signifiers (Italic, comma separated)
                signifiers_list = getattr(node, 'signifiers', [])
                if signifiers_list:
                    sig_text = ", ".join(signifiers_list)
                    lbl_sig = self.canvas.create_text(x, current_y, text=sig_text, font=("Arial", 11, "italic"),
                                                      fill="#475569", justify=tk.CENTER, tags=("node_sig",))
                    node_items.append(lbl_sig)
                    bbox_sig = self.canvas.bbox(lbl_sig)
                    current_y = bbox_sig[3] + 4 if bbox_sig else current_y + 16

                # Line 3: Dates / Status
                if node.birth_year or node.death_year or node.is_living:
                    b_str = node.birth_year if node.birth_year else "?"
                    d_str = "Present" if node.is_living else (node.death_year if node.death_year else "?")
                    years_text = f"({b_str} - {d_str})"
                    lbl_years = self.canvas.create_text(x, current_y, text=years_text, font=("Arial", 10),
                                                        fill="#64748b", justify=tk.CENTER, tags=("node_years",))
                    node_items.append(lbl_years)

                # Background card bounding box
                if node_items:
                    x1, y1, x2, y2 = self.canvas.bbox(node_items[0])
                    for item in node_items[1:]:
                        bx1, by1, bx2, by2 = self.canvas.bbox(item)
                        x1 = min(x1, bx1)
                        y1 = min(y1, by1)
                        x2 = max(x2, bx2)
                        y2 = max(y2, by2)
                    bg_rect = self.canvas.create_rectangle(x1 - 6, y1 - 4, x2 + 6, y2 + 4, fill="#ffffff",
                                                           outline="#cbd5e1", width=1)
                    self.canvas.tag_lower(bg_rect, node_items[0])

                plus_tag = f"plus_click:{name}"
                plus_y = y - pie_radius - 15.0

                self.canvas.create_rectangle(x - 8, plus_y - 8, x + 8, plus_y + 8, fill="#10b981", outline="#047857",
                                             tags=(plus_tag, "interactive", "plus"))
                self.canvas.create_text(x, plus_y, text="+", font=("Arial", 13, "bold"), fill="white",
                                        tags=(plus_tag, "interactive", "plus_text"))

        self.canvas.scale("all", 0, 0, self.canvas_scale, self.canvas_scale)
        self.canvas.move("all", self.pan_x, self.pan_y)

        name_size = max(1, int(13 * self.canvas_scale))
        sig_size = max(1, int(11 * self.canvas_scale))
        years_size = max(1, int(10 * self.canvas_scale))
        plus_size = max(1, int(13 * self.canvas_scale))

        self.canvas.itemconfig("node_name", font=("Arial", name_size, "bold"))
        self.canvas.itemconfig("node_sig", font=("Arial", sig_size, "italic"))
        self.canvas.itemconfig("node_years", font=("Arial", years_size, ""))
        self.canvas.itemconfig("plus_text", font=("Arial", plus_size, "bold"))

    def on_press(self, event):
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        clicked_items = self.canvas.find_overlapping(canvas_x - 1, canvas_y - 1, canvas_x + 1, canvas_y + 1)

        if clicked_items:
            tags = self.canvas.gettags(clicked_items[-1])
            for tag in tags:
                if tag.startswith("plus_click:"):
                    self.open_parent_dialog(tag.split(":")[1])
                    return
                elif tag.startswith("pie_click:"):
                    self.open_profile_dialog(tag.split(":")[1])
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

        name_size = max(1, int(13 * self.canvas_scale))
        sig_size = max(1, int(11 * self.canvas_scale))
        years_size = max(1, int(10 * self.canvas_scale))
        plus_size = max(1, int(13 * self.canvas_scale))

        self.canvas.itemconfig("node_name", font=("Arial", name_size, "bold"))
        self.canvas.itemconfig("node_sig", font=("Arial", sig_size, "italic"))
        self.canvas.itemconfig("node_years", font=("Arial", years_size, ""))
        self.canvas.itemconfig("plus_text", font=("Arial", plus_size, "bold"))

    # ---------------------------------------------------------
    # PARENT & PROFILE DIALOGS
    # ---------------------------------------------------------
    def open_parent_dialog(self, person_name):
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Link Parents: {person_name}")
        dialog.geometry("450x350")
        dialog.transient(self.root)
        dialog.grab_set()

        node = self.tree[person_name]

        tk.Label(dialog, text="Link Family Network For:", font=("Arial", 10)).pack(pady=(12, 2))
        tk.Label(dialog, text=node.display_name, font=("Arial", 14, "bold"), fg="#047857").pack(pady=(0, 12))

        def create_parent_block(title_str, node_attr):
            group = tk.LabelFrame(dialog, text=title_str, font=("Arial", 10, "bold"), padx=10, pady=10)
            group.pack(fill=tk.X, padx=20, pady=10)

            tk.Label(group, text="Full Name:", font=("Arial", 9, "bold")).pack(side=tk.LEFT)
            name_entry = tk.Entry(group, font=("Arial", 10), width=28)
            name_entry.pack(side=tk.LEFT, padx=10)

            parent_n = self.tree.get(node_attr) if node_attr else None
            if parent_n:
                name_entry.insert(0, parent_n.display_name)
            else:
                name_entry.insert(0, node_attr or "")

            return name_entry

        f_entry = create_parent_block(" Father ", node.father)
        m_entry = create_parent_block(" Mother ", node.mother)

        def save_parents():
            old_f, old_m = node.father, node.mother
            new_f, new_m = f_entry.get().strip(), m_entry.get().strip()

            def process_parent(old_id, new_id, is_father):
                if not new_id:
                    if is_father:
                        node.father = None
                    else:
                        node.mother = None
                    return
                if old_id != new_id:
                    if new_id not in self.tree:
                        new_node = AncestorNode(name=new_id, display_name=new_id)
                        new_node.signifiers = []
                        self.tree[new_id] = new_node
                    if is_father:
                        node.father = new_id
                    else:
                        node.mother = new_id

            process_parent(old_f, new_f, True)
            process_parent(old_m, new_m, False)
            dialog.destroy()
            self.refresh_plot()

        tk.Button(dialog, text="Link Ancestors", command=save_parents, bg="#3b82f6", fg="white",
                  font=("Arial", 10, "bold")).pack(pady=15)

    def open_profile_dialog(self, person_name):
        self.calculate_inheritance()
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Manage Profile: {person_name}")
        dialog.geometry("750x780")
        dialog.transient(self.root)
        dialog.grab_set()

        node = self.tree[person_name]
        if not hasattr(node, 'signifiers') or node.signifiers is None:
            node.signifiers = []

        header_text = node.display_name
        if node.signifiers:
            header_text += f" ({', '.join(node.signifiers)})"

        tk.Label(dialog, text=header_text, font=("Arial", 16, "bold"), fg="#047857", bg="#f8fafc").pack(fill=tk.X,
                                                                                                        pady=(15, 10))

        notebook = ttk.Notebook(dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        tab_bio = tk.Frame(notebook, bg="#f8fafc")
        tab_genetics = tk.Frame(notebook, bg="#f8fafc")
        tab_timeline = tk.Frame(notebook, bg="#f8fafc")

        notebook.add(tab_bio, text="Identity & Bio")
        notebook.add(tab_genetics, text="Genetics Base & Breakdown")
        notebook.add(tab_timeline, text="Timeline Map Data")

        # --- TAB 1: IDENTITY & BIO ---
        bio_grid = tk.Frame(tab_bio, bg="#f8fafc")
        bio_grid.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        form_frame = tk.Frame(bio_grid, bg="#f8fafc")
        form_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(form_frame, text="Full Name:", font=("Arial", 10, "bold"), bg="#f8fafc").grid(row=0, column=0,
                                                                                               sticky=tk.W, pady=6)
        bio_name = tk.Entry(form_frame, width=28, font=("Arial", 10))
        bio_name.grid(row=0, column=1, sticky=tk.W, pady=6)
        bio_name.insert(0, node.display_name)

        tk.Label(form_frame, text="Birth Year:", font=("Arial", 10, "bold"), bg="#f8fafc").grid(row=1, column=0,
                                                                                                sticky=tk.W, pady=6)
        bio_b_year = tk.Entry(form_frame, width=15, font=("Arial", 10))
        bio_b_year.grid(row=1, column=1, sticky=tk.W, pady=6)
        bio_b_year.insert(0, node.birth_year)

        tk.Label(form_frame, text="Birth Location:", font=("Arial", 10, "bold"), bg="#f8fafc").grid(row=2, column=0,
                                                                                                    sticky=tk.W, pady=6)
        bio_b_loc = tk.Entry(form_frame, width=28, font=("Arial", 10))
        bio_b_loc.grid(row=2, column=1, sticky=tk.W, pady=6)
        bio_b_loc.insert(0, getattr(node, 'birth_location', ''))

        tk.Label(form_frame, text="Death Year:", font=("Arial", 10, "bold"), bg="#f8fafc").grid(row=3, column=0,
                                                                                                sticky=tk.W, pady=6)
        d_frame = tk.Frame(form_frame, bg="#f8fafc")
        d_frame.grid(row=3, column=1, sticky=tk.W, pady=6)

        bio_d_year = tk.Entry(d_frame, width=12, font=("Arial", 10))
        bio_d_year.pack(side=tk.LEFT)
        bio_d_year.insert(0, node.death_year)

        bio_living = tk.BooleanVar(value=node.is_living)

        def toggle_d_year():
            if bio_living.get():
                bio_d_year.delete(0, tk.END)
                bio_d_year.config(state=tk.DISABLED)
            else:
                bio_d_year.config(state=tk.NORMAL)

        tk.Checkbutton(d_frame, text="Living", variable=bio_living, command=toggle_d_year, bg="#f8fafc").pack(
            side=tk.LEFT, padx=5)
        toggle_d_year()

        tk.Label(form_frame, text="Death Location:", font=("Arial", 10, "bold"), bg="#f8fafc").grid(row=4, column=0,
                                                                                                    sticky=tk.W, pady=6)
        bio_d_loc = tk.Entry(form_frame, width=28, font=("Arial", 10))
        bio_d_loc.grid(row=4, column=1, sticky=tk.W, pady=6)
        bio_d_loc.insert(0, getattr(node, 'death_location', ''))

        # Signifiers Panel (1 word max each)
        sig_frame = tk.LabelFrame(bio_grid, text=" Signifiers (1 word max) ", font=("Arial", 10, "bold"), padx=10,
                                  pady=10, bg="#f8fafc")
        sig_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(15, 0))

        sig_listbox = tk.Listbox(sig_frame, font=("Arial", 10), height=7)
        sig_listbox.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

        def refresh_sig_list():
            sig_listbox.delete(0, tk.END)
            for s in node.signifiers:
                sig_listbox.insert(tk.END, s)

        refresh_sig_list()

        sig_input_frame = tk.Frame(sig_frame, bg="#f8fafc")
        sig_input_frame.pack(fill=tk.X, pady=(0, 5))

        sig_entry = tk.Entry(sig_input_frame, font=("Arial", 10), width=16)
        sig_entry.pack(side=tk.LEFT, padx=(0, 5))

        def add_signifier():
            val = sig_entry.get().strip()
            if not val:
                return
            if len(val.split()) > 1:
                messagebox.showwarning("Validation Error", "A signifier can be at most one word.")
                return
            if val not in node.signifiers:
                node.signifiers.append(val)
                refresh_sig_list()
                sig_entry.delete(0, tk.END)

        tk.Button(sig_input_frame, text="Add", command=add_signifier, bg="#3b82f6", fg="white",
                  font=("Arial", 9, "bold")).pack(side=tk.LEFT)

        def remove_signifier():
            sel = sig_listbox.curselection()
            if sel:
                del node.signifiers[sel[0]]
                refresh_sig_list()

        tk.Button(sig_frame, text="Remove Selected", command=remove_signifier, bg="#ef4444", fg="white",
                  font=("Arial", 9)).pack(anchor=tk.E)

        # --- TAB 2: GENETICS & BREAKDOWN ---
        genetics_main = tk.Frame(tab_genetics, bg="#f8fafc")
        genetics_main.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        computed_frame = tk.LabelFrame(genetics_main, text=" Computed Inherited Percentages ", font=("Arial", 10, "bold"), padx=10, pady=10, bg="#f8fafc")
        computed_frame.pack(fill=tk.X, pady=(0, 15))

        computed_list_frame = tk.Frame(computed_frame, bg="#f8fafc")
        computed_list_frame.pack(fill=tk.X, expand=True)

        def refresh_computed_breakdown():
            for widget in computed_list_frame.winfo_children():
                widget.destroy()

            active_eth = {k: v for k, v in node.computed_ethnicities.items() if v > 0}
            if not active_eth:
                tk.Label(computed_list_frame, text="No computed ethnicity data available.", font=("Arial", 9, "italic"), bg="#f8fafc", fg="#64748b").pack(anchor=tk.W)
                return

            sorted_eth = sorted(active_eth.items(), key=lambda item: item[1], reverse=True)
            for eth, pct in sorted_eth:
                row = tk.Frame(computed_list_frame, bg="#f8fafc")
                row.pack(fill=tk.X, pady=2)

                clr = self.ethnicity_colors.get(eth, "#cbd5e1") if eth != "Unknown" else "#cbd5e1"
                tk.Label(row, bg=clr, width=2, height=1, relief=tk.SOLID, bd=1).pack(side=tk.LEFT, padx=(0, 8))
                tk.Label(row, text=f"{eth}:", font=("Arial", 9, "bold"), bg="#f8fafc", fg="#1e293b", width=15, anchor=tk.W).pack(side=tk.LEFT)
                tk.Label(row, text=f"{pct:.1f}%", font=("Arial", 9), bg="#f8fafc", fg="#475569").pack(side=tk.LEFT)

        refresh_computed_breakdown()

        base_frame = tk.LabelFrame(genetics_main, text=" Base Origins (Root Ancestor Settings) ", font=("Arial", 10, "bold"), padx=10, pady=10, bg="#f8fafc")
        base_frame.pack(fill=tk.BOTH, expand=True)

        c_frame = tk.Frame(base_frame, bg="#f8fafc")
        c_frame.pack(fill=tk.X, pady=(0, 10))
        tk.Label(c_frame, text="Add New Ethnicity:", font=("Arial", 9, "bold"), bg="#f8fafc").pack(side=tk.LEFT)
        new_eth_entry = tk.Entry(c_frame, width=15, font=("Arial", 10))
        new_eth_entry.pack(side=tk.LEFT, padx=5)

        cb_container = tk.Frame(base_frame, bg="#f8fafc")
        cb_container.pack(fill=tk.BOTH, expand=True)

        vars_dict = {}

        def pick_edit_color(ethnicity):
            clr = colorchooser.askcolor(initialcolor=self.ethnicity_colors.get(ethnicity, "#cbd5e1"))
            if clr[1]:
                self.ethnicity_colors[ethnicity] = clr[1]
                render_checkboxes()
                refresh_computed_breakdown()

        def update_computed_preview():
            node.base_ethnicities = [eth for eth, var in vars_dict.items() if var.get()]
            self.calculate_inheritance()
            refresh_computed_breakdown()

        def render_checkboxes():
            for widget in cb_container.winfo_children(): widget.destroy()
            vars_dict.clear()
            for idx, eth in enumerate(self.ethnicity_options):
                var = tk.BooleanVar(value=(eth in node.base_ethnicities))
                vars_dict[eth] = var
                r, c = idx // 2, (idx % 2) * 2
                tk.Checkbutton(cb_container, text=eth, variable=var, font=("Arial", 9), bg="#f8fafc", command=update_computed_preview).grid(row=r, column=c, sticky=tk.W, padx=(5, 2), pady=3)
                lbl = tk.Label(cb_container, bg=self.ethnicity_colors.get(eth, "#cbd5e1"), width=3, relief=tk.RAISED, cursor="hand2")
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
                update_computed_preview()

        tk.Button(c_frame, text="Add", command=add_eth, bg="#cbd5e1", font=("Arial", 9, "bold")).pack(side=tk.LEFT)
        render_checkboxes()

        # --- TAB 3: TIMELINE MAP DATA ---
        loc_top = tk.Frame(tab_timeline, bg="#f8fafc")
        loc_top.pack(fill=tk.X, padx=15, pady=15)

        tk.Label(loc_top, text="Year:", font=("Arial", 9, "bold"), bg="#f8fafc").pack(side=tk.LEFT)
        loc_year_entry = tk.Entry(loc_top, width=8, font=("Arial", 10))
        loc_year_entry.pack(side=tk.LEFT, padx=(5, 15))

        tk.Label(loc_top, text="Location:", font=("Arial", 9, "bold"), bg="#f8fafc").pack(side=tk.LEFT)
        loc_place_entry = tk.Entry(loc_top, width=20, font=("Arial", 10))
        loc_place_entry.pack(side=tk.LEFT, padx=(5, 10))

        loc_list = tk.Listbox(tab_timeline, font=("Arial", 10))
        loc_list.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        def refresh_loc_list():
            loc_list.delete(0, tk.END)
            node.locations.sort(key=lambda x: x['year'])
            for loc in node.locations:
                l_type = f"[{loc.get('type', 'event').upper()}] " if 'type' in loc else ""
                if loc.get('lat') is not None and loc.get('lon') is not None:
                    loc_list.insert(tk.END,
                                    f"{l_type}{loc['year']} - {loc['place']} (Lat: {loc['lat']:.2f}, Lon: {loc['lon']:.2f})")
                else:
                    p_text = loc['place'] if loc['place'] else "(Date only, no location)"
                    loc_list.insert(tk.END, f"{l_type}{loc['year']} - {p_text}")

        refresh_loc_list()

        def add_location():
            try:
                year_val = int(loc_year_entry.get().strip())
            except ValueError:
                messagebox.showwarning("Input Error", "Year must be a valid number.")
                return

            place = loc_place_entry.get().strip()
            if not place:
                node.locations.append({
                    'year': year_val,
                    'place': "",
                    'lat': None,
                    'lon': None,
                    'type': 'date'
                })
                loc_year_entry.delete(0, tk.END)
                loc_place_entry.delete(0, tk.END)
                refresh_loc_list()
                return

            if not GEO_AVAILABLE:
                messagebox.showerror("Dependency Missing", "Please install geopy to use this feature.")
                return

            try:
                location = self.geolocator.geocode(place)
                if location:
                    node.locations.append({
                        'year': year_val,
                        'place': location.address.split(',')[0] + " (" + place + ")",
                        'lat': location.latitude,
                        'lon': location.longitude,
                        'type': 'event'
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
        btn_loc_frame.pack(fill=tk.X, padx=15, pady=(0, 15))
        tk.Button(loc_top, text="Search & Add", command=add_location, bg="#3b82f6", fg="white",
                  font=("Arial", 9, "bold")).pack(side=tk.LEFT)
        tk.Button(btn_loc_frame, text="Remove Selected", command=remove_location, bg="#ef4444", fg="white",
                  font=("Arial", 9)).pack(side=tk.RIGHT)

        # --- SAVE PROFILE ---
        def save_profile():
            node.display_name = bio_name.get().strip()
            new_b_year = bio_b_year.get().strip()
            new_b_loc = bio_b_loc.get().strip()
            new_d_year = bio_d_year.get().strip()
            new_d_loc = bio_d_loc.get().strip()

            if GEO_AVAILABLE and new_b_loc and (
                    new_b_loc != getattr(node, 'birth_location', '') or new_b_year != node.birth_year):
                if new_b_year.isdigit():
                    loc_data = self.geolocator.geocode(new_b_loc)
                    if loc_data:
                        node.locations = [l for l in node.locations if l.get('type') != 'birth']
                        node.locations.append({
                            'year': int(new_b_year),
                            'place': loc_data.address.split(',')[0] + f" ({new_b_loc})",
                            'lat': loc_data.latitude,
                            'lon': loc_data.longitude,
                            'type': 'birth'
                        })

            if GEO_AVAILABLE and new_d_loc and not bio_living.get() and (
                    new_d_loc != getattr(node, 'death_location', '') or new_d_year != node.death_year):
                if new_d_year.isdigit():
                    loc_data = self.geolocator.geocode(new_d_loc)
                    if loc_data:
                        node.locations = [l for l in node.locations if l.get('type') != 'death']
                        node.locations.append({
                            'year': int(new_d_year),
                            'place': loc_data.address.split(',')[0] + f" ({new_d_loc})",
                            'lat': loc_data.latitude,
                            'lon': loc_data.longitude,
                            'type': 'death'
                        })

            node.birth_year = new_b_year
            node.birth_location = new_b_loc
            node.death_year = new_d_year
            node.death_location = new_d_loc
            node.is_living = bio_living.get()

            node.base_ethnicities = [eth for eth, var in vars_dict.items() if var.get()]

            dialog.destroy()
            self.refresh_plot()

        tk.Button(dialog, text="Save & Update Profile", command=save_profile, bg="#10b981", fg="white",
                  font=("Arial", 11, "bold"), height=2).pack(fill=tk.X, padx=20, pady=15)

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
                "father": n.father, "mother": n.mother, "locations": n.locations,
                "signifiers": getattr(n, 'signifiers', []),
                "birth_location": getattr(n, 'birth_location', ''),
                "death_location": getattr(n, 'death_location', '')
            }

        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)
        messagebox.showinfo("Saved", "Tree exported.")

    def load_tree(self, from_welcome=False):
        file_path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if not file_path: return False

        with open(file_path, 'r') as f:
            raw = json.load(f)

        self.tree.clear()
        self.ethnicity_options = raw.get("master_ethnicities", [])
        self.ethnicity_colors = raw.get("ethnicity_colors", {})

        for name, d in raw.get("nodes", {}).items():
            node = AncestorNode(
                name=d["name"], display_name=d.get("display_name", d["name"]),
                birth_year=d.get("birth_year", ""), death_year=d.get("death_year", ""),
                is_living=d.get("is_living", False), base_ethnicities=d.get("base_ethnicities", []),
                father=d.get("father"), mother=d.get("mother"), locations=d.get("locations", [])
            )
            node.signifiers = d.get("signifiers", [])
            node.birth_location = d.get("birth_location", "")
            node.death_location = d.get("death_location", "")
            self.tree[name] = node

        if from_welcome:
            self.welcome_frame.destroy()
            self.setup_ui()

        self.isolated_root = None
        self.reset_view_to_root()
        messagebox.showinfo("Loaded", "Tree imported.")
        return True

    def clear_tree(self):
        resp = messagebox.askyesnocancel("Save Changes?", "Save changes before clearing?")
        if resp is True:
            self.save_tree()
        elif resp is None:
            return

        if self.active_breakdown_window: self.active_breakdown_window.destroy()
        self.tree.clear()
        self.ethnicity_options.clear()
        self.ethnicity_colors.clear()
        self.canvas_scale, self.pan_x, self.pan_y = 1.0, 0.0, 0.0
        self.isolated_root = None

        for w in self.root.winfo_children(): w.destroy()
        self.show_welcome_screen()
