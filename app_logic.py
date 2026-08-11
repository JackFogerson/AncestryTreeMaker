# app_logic.py

import tkinter as tk
from tkinter import messagebox, filedialog, colorchooser, ttk
from models import AncestorNode
from genetics.inheritance import calculate_inheritance
from storage.json_io import load_tree_file, save_tree_file
from dialogs.parent_dialog import open_parent_dialog as show_parent_dialog
from dialogs.profile_dialog import open_profile_dialog as show_profile_dialog
from tree.renderer import TreeRenderer
from tree.layout import calculate_positions, display_roots
from tree.interactions import handle_drag, handle_press, handle_zoom
from utils.constants import APPLICATION_TITLE, WINDOW_SIZE

# Attempt to load requests for web operations if needed
try:
    import requests

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from utils.geocoder import create_geocoder, is_available as geocoder_available
from mapview.timeline import build_timeline_steps as create_timeline_steps
from mapview.map_window import MapWindowMixin

GEO_AVAILABLE = geocoder_available()

# Attempt to load Cartopy and Matplotlib for map visualization
try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature

    MAP_AVAILABLE = True
except ImportError:
    MAP_AVAILABLE = False


class AncestryApp(MapWindowMixin):
    def __init__(self, root):
        self.root = root
        self.root.title(APPLICATION_TITLE)
        self.root.geometry(WINDOW_SIZE)

        self.ethnicity_options = []
        self.ethnicity_colors = {}

        self.tree = {}
        self.positions = {}
        self.tree_renderer = TreeRenderer()

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
            self.geolocator = create_geocoder()
        else:
            self.geolocator = None

        # Display starting wizard
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
    # MAP VIEW & SEQUENTIAL ANIMATION LOGIC (CARTOPY)
    # ---------------------------------------------------------
    def _legacy_open_map_view(self):
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
        self.timeline_speed = 700
        self.scatter_points = []
        self.timeline_steps = []
        self.timeline_step_idx = 0

        # Panning State
        self.map_panning = False
        self.map_pan_start_x = 0
        self.map_pan_start_y = 0
        self.map_extent_start = []

        # --- Top Control Panel ---
        ctrl_frame = tk.Frame(map_win, bg="#0f172a")
        ctrl_frame.pack(fill=tk.X, pady=(10, 10))

        tk.Button(ctrl_frame, text="▶ Play Timeline", command=self.play_map, bg="#10b981", fg="white",
                  font=("Arial", 11, "bold"), width=14).pack(side=tk.LEFT, padx=(15, 5))
        tk.Button(ctrl_frame, text="⏸ Pause", command=self.pause_map, bg="#f59e0b", fg="white",
                  font=("Arial", 11, "bold"), width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(ctrl_frame, text="⏪ Restart", command=self.restart_map, bg="#3b82f6", fg="white",
                  font=("Arial", 11, "bold"), width=10).pack(side=tk.LEFT, padx=5)

        tk.Frame(ctrl_frame, width=2, bg="#334155").pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=5)

        # Explicit Zoom Controls
        tk.Button(ctrl_frame, text="➕ Zoom In", command=lambda: self.zoom_map(0.75), bg="#475569", fg="white",
                  font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=4)
        tk.Button(ctrl_frame, text="➖ Zoom Out", command=lambda: self.zoom_map(1.33), bg="#475569", fg="white",
                  font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=4)

        tk.Frame(ctrl_frame, width=2, bg="#334155").pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=5)

        tk.Label(ctrl_frame, text="Bounds:", bg="#0f172a", fg="white", font=("Arial", 11, "bold")).pack(
            side=tk.LEFT, padx=(0, 5))

        self.view_var = tk.StringVar(value="Global")
        view_drop = ttk.Combobox(ctrl_frame, textvariable=self.view_var,
                                 values=["Global", "North America & Europe", "Custom"], state="readonly", width=20)
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

        # --- Matplotlib Canvas Setup ---
        self.map_fig = plt.Figure(figsize=(12, 8), dpi=100, facecolor='#0f172a')
        self.map_fig.subplots_adjust(left=0.0, right=1.0, bottom=0.0, top=1.0)

        self.map_ax = self.map_fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
        self.map_ax.set_facecolor('#0f172a')

        self.map_ax.add_feature(cfeature.OCEAN, facecolor='#0f172a', zorder=0)
        self.map_ax.add_feature(cfeature.LAND, facecolor='#334155', edgecolor='#475569', zorder=1)
        self.map_ax.add_feature(cfeature.BORDERS, linestyle=':', edgecolor='#64748b', zorder=1)
        self.map_ax.set_global()

        self.map_annot = self.map_ax.annotate("", xy=(0, 0), xytext=(10, 10), textcoords="offset points",
                                              bbox=dict(boxstyle="round,pad=0.4", fc="#f8fafc", ec="#94a3b8", lw=1),
                                              color="#0f172a", fontsize=10, weight="bold", zorder=20)
        self.map_annot.set_visible(False)

        self.canvas_widget = FigureCanvasTkAgg(self.map_fig, master=map_win)
        self.canvas_widget.get_tk_widget().pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Bind Mouse Interactions
        self.canvas_widget.mpl_connect("button_press_event", self.on_map_press)
        self.canvas_widget.mpl_connect("motion_notify_event", self.on_map_motion)
        self.canvas_widget.mpl_connect("button_release_event", self.on_map_release)

        # Bind Zooming (Mouse Wheel)
        def on_map_scroll(event):
            if event.inaxes != self.map_ax:
                return
            step = getattr(event, 'step', 0)
            delta = getattr(event, 'delta', 0)
            button = getattr(event, 'button', None)
            if button == 'up' or step > 0 or delta > 0:
                self.zoom_map(0.8)
            elif button == 'down' or step < 0 or delta < 0:
                self.zoom_map(1.25)

        self.canvas_widget.mpl_connect("scroll_event", on_map_scroll)

        tk_w = self.canvas_widget.get_tk_widget()
        tk_w.bind("<MouseWheel>", lambda e: self.zoom_map(0.8 if e.delta > 0 else 1.25))
        tk_w.bind("<Button-4>", lambda e: self.zoom_map(0.8))
        tk_w.bind("<Button-5>", lambda e: self.zoom_map(1.25))

        self.drawn_artists = []
        self.build_timeline_steps()

        if not self.timeline_steps:
            self.map_year_label.config(text="----")
            self.current_map_year = 0
        else:
            self.timeline_step_idx = 0
            self.current_map_year = self.timeline_steps[0][0]
            self.map_year_label.config(text=f"{self.current_map_year}")

        self.update_map_visuals(t=1.0)

        def on_closing():
            self.map_playing = False
            plt.close(self.map_fig)
            map_win.destroy()

        map_win.protocol("WM_DELETE_WINDOW", on_closing)

    def _legacy_zoom_map(self, factor):
        if not hasattr(self, 'map_ax'): return
        try:
            extent = list(self.map_ax.get_extent(crs=ccrs.PlateCarree()))
            lon_min, lon_max, lat_min, lat_max = extent

            lon_center = (lon_min + lon_max) / 2.0
            lat_center = (lat_min + lat_max) / 2.0

            lon_span = (lon_max - lon_min) * factor
            lat_span = (lat_max - lat_min) * factor

            lon_span = min(360.0, max(0.5, lon_span))
            lat_span = min(180.0, max(0.5, lat_span))

            new_extent = [
                max(-180.0, lon_center - lon_span / 2.0),
                min(180.0, lon_center + lon_span / 2.0),
                max(-89.9, lat_center - lat_span / 2.0),
                min(89.9, lat_center + lat_span / 2.0)
            ]
            self.map_ax.set_extent(new_extent, crs=ccrs.PlateCarree())
            self.canvas_widget.draw_idle()
        except Exception:
            pass

    def _legacy_on_map_press(self, event):
        if event.button == 1 and event.inaxes == self.map_ax:
            self.map_panning = True
            self.map_pan_start_x = event.x
            self.map_pan_start_y = event.y
            self.map_extent_start = self.map_ax.get_extent(crs=ccrs.PlateCarree())

    def _legacy_on_map_release(self, event):
        if event.button == 1:
            self.map_panning = False

    def _legacy_on_map_motion(self, event):
        if self.map_panning and event.inaxes == self.map_ax:
            # Map Panning Logic
            if self.map_annot.get_visible():
                self.map_annot.set_visible(False)

            dx_pixels = event.x - self.map_pan_start_x
            dy_pixels = event.y - self.map_pan_start_y

            extent = self.map_extent_start
            lon_span = extent[1] - extent[0]
            lat_span = extent[3] - extent[2]

            bbox = self.map_ax.bbox
            ax_width = bbox.width
            ax_height = bbox.height

            # Data shifts opposite to mouse movement direction
            dx_data = (dx_pixels / ax_width) * lon_span
            dy_data = (dy_pixels / ax_height) * lat_span

            new_ext = [
                extent[0] - dx_data,
                extent[1] - dx_data,
                extent[2] - dy_data,
                extent[3] - dy_data
            ]

            # Clamp Latitudes to prevent rendering crash
            if new_ext[2] < -89.9:
                shift = -89.9 - new_ext[2]
                new_ext[2] += shift
                new_ext[3] += shift
            if new_ext[3] > 89.9:
                shift = new_ext[3] - 89.9
                new_ext[2] -= shift
                new_ext[3] -= shift

            self.map_ax.set_extent(new_ext, crs=ccrs.PlateCarree())
            self.canvas_widget.draw_idle()
        else:
            # Hover Logic
            if event.inaxes != self.map_ax:
                if self.map_annot.get_visible():
                    self.map_annot.set_visible(False)
                    self.canvas_widget.draw_idle()
                return

            point_groups = {}
            for lon, lat, name, place, is_active in self.scatter_points:
                if not is_active:
                    continue

                r_pt = ccrs.PlateCarree().transform_point(lon, lat, ccrs.Geodetic())
                xy = self.map_ax.transData.transform(r_pt)

                dist = (xy[0] - event.x) ** 2 + (xy[1] - event.y) ** 2
                if dist < 400:
                    # Extract only the first location for display and grouping
                    # (removes everything inside and after parentheses or commas)
                    first_loc = place.split('(')[0].split(',')[0].strip()
                    key = first_loc

                    if key not in point_groups:
                        point_groups[key] = {'items': [], 'r_pt': r_pt, 'min_dist': dist}

                    item_tuple = (name, first_loc)
                    if item_tuple not in point_groups[key]['items']:
                        point_groups[key]['items'].append(item_tuple)

                    # Ensure the tooltip tracks the closest point among grouped locations
                    if dist < point_groups[key]['min_dist']:
                        point_groups[key]['min_dist'] = dist
                        point_groups[key]['r_pt'] = r_pt

            best_group = None
            lowest_dist = float('inf')
            for key, group in point_groups.items():
                if group['min_dist'] < lowest_dist:
                    lowest_dist = group['min_dist']
                    best_group = group

            if best_group:
                place_header = best_group['items'][0][1] if best_group['items'][0][1] else "Unknown Location"
                lines = [f"{place_header}"]

                for name, place_disp in best_group['items']:
                    lines.append(f" • {name}")

                annot_str = "\n".join(lines)
                r_pt = best_group['r_pt']

                if not self.map_annot.get_visible() or self.map_annot.get_text() != annot_str:
                    self.map_annot.xy = (r_pt[0], r_pt[1])
                    self.map_annot.set_text(annot_str)
                    self.map_annot.set_visible(True)
                    self.canvas_widget.draw_idle()
            else:
                if self.map_annot.get_visible():
                    self.map_annot.set_visible(False)
                    self.canvas_widget.draw_idle()

    def _legacy_build_timeline_steps(self):
        self.timeline_steps, self.min_year, self.max_year = create_timeline_steps(self.tree)

    def _legacy_update_map_visuals(self, t=1.0):
        if not self.timeline_steps or self.timeline_step_idx >= len(self.timeline_steps):
            return

        year, k_step = self.timeline_steps[self.timeline_step_idx]
        self.current_map_year = year
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

            is_active = (first_year <= self.current_map_year <= last_year)
            if is_active:
                active_names.append(node.display_name)

            all_v_locs = [loc for loc in sorted(node.locations, key=lambda x: x['year'])
                          if loc.get('lat') is not None and loc.get('lon') is not None]
            if not all_v_locs:
                continue

            reachable_locs = []
            for loc in all_v_locs:
                if loc['year'] < year:
                    reachable_locs.append(loc)
                elif loc['year'] == year:
                    locs_same_year = [l for l in all_v_locs if l['year'] == year]
                    intra_idx = locs_same_year.index(loc) + 1
                    if intra_idx <= k_step:
                        reachable_locs.append(loc)

            if not reachable_locs:
                continue

            curr_target_loc = reachable_locs[-1]
            curr_target_idx = all_v_locs.index(curr_target_loc)

            locs_in_current_year = [l for l in all_v_locs if l['year'] == year]
            is_moving_now = False

            if curr_target_loc['year'] == year and locs_in_current_year:
                intra_idx = locs_in_current_year.index(curr_target_loc) + 1
                if intra_idx == k_step and curr_target_idx > 0 and t < 1.0:
                    is_moving_now = True

            if is_moving_now:
                prev_loc = all_v_locs[curr_target_idx - 1]
                curr_lat = prev_loc['lat'] + (curr_target_loc['lat'] - prev_loc['lat']) * t
                curr_lon = prev_loc['lon'] + (curr_target_loc['lon'] - prev_loc['lon']) * t

                past_locs_for_trail = all_v_locs[:curr_target_idx]
                visited_dots_locs = all_v_locs[:curr_target_idx]
                moving_lats = [prev_loc['lat'], curr_lat]
                moving_lons = [prev_loc['lon'], curr_lon]
            else:
                curr_lat = curr_target_loc['lat']
                curr_lon = curr_target_loc['lon']

                past_locs_for_trail = reachable_locs
                visited_dots_locs = reachable_locs[:-1]
                moving_lats = []
                moving_lons = []

            # 1. Visited past location dots are faded (zorder=3)
            if visited_dots_locs:
                v_lats = [l['lat'] for l in visited_dots_locs]
                v_lons = [l['lon'] for l in visited_dots_locs]
                faded_dots = self.map_ax.scatter(v_lons, v_lats, color='#475569',
                                                 edgecolor='#94a3b8', s=30, transform=ccrs.Geodetic(),
                                                 zorder=3, alpha=0.6)
                self.drawn_artists.append(faded_dots)

            # 2. Historical trail lines drawn as straight lines (zorder=2)
            if len(past_locs_for_trail) > 1:
                p_lats = [l['lat'] for l in past_locs_for_trail]
                p_lons = [l['lon'] for l in past_locs_for_trail]
                trail, = self.map_ax.plot(p_lons, p_lats, color='#475569', linewidth=1.5,
                                          linestyle='--', transform=ccrs.PlateCarree(), alpha=0.4, zorder=2)
                self.drawn_artists.append(trail)

            # 3. Active moving straight line following as they move (zorder=8)
            if is_moving_now and len(moving_lats) > 1:
                moving_line, = self.map_ax.plot(moving_lons, moving_lats, color='#10b981', linewidth=2.5,
                                                linestyle='-', transform=ccrs.PlateCarree(), alpha=0.9, zorder=8)
                self.drawn_artists.append(moving_line)

            # 4. Alive dots always appear on top (zorder=10 for alive, zorder=4 for dead)
            dot_color = '#10b981' if is_active else '#475569'
            dot_edge = '#ffffff' if is_active else '#94a3b8'
            dot_alpha = 1.0 if is_active else 0.6
            dot_size = 65 if is_active else 40
            dot_zorder = 10 if is_active else 4

            main_dot = self.map_ax.scatter([curr_lon], [curr_lat], color=dot_color,
                                           edgecolor=dot_edge, s=dot_size, transform=ccrs.Geodetic(),
                                           zorder=dot_zorder, alpha=dot_alpha)

            place_name = curr_target_loc.get('place', '')
            self.scatter_points.append((curr_lon, curr_lat, node.display_name, place_name, is_active))
            self.drawn_artists.append(main_dot)

        self.canvas_widget.draw_idle()

        names_text = "\n".join(active_names[:25])
        if len(active_names) > 25:
            names_text += f"\n... and {len(active_names) - 25} more"

        self.map_names_label.config(text=names_text)

    def _legacy_play_map(self):
        if not self.tree or not self.timeline_steps: return
        if not self.map_playing:
            self.map_playing = True
            if self.is_moving:
                self._movement_loop()
            else:
                self._map_loop()

    def _legacy_pause_map(self):
        self.map_playing = False

    def _legacy_restart_map(self):
        self.map_playing = False
        self.is_moving = False
        self.move_t = 1.0
        self.timeline_step_idx = 0
        self.update_map_visuals(t=1.0)

    def _legacy_map_loop(self):
        if not self.map_playing: return

        if self.timeline_step_idx >= len(self.timeline_steps) - 1:
            self.map_playing = False
            self.update_map_visuals(t=1.0)
            return

        self.timeline_step_idx += 1
        year, k_step = self.timeline_steps[self.timeline_step_idx]

        needs_movement = False
        for node in self.tree.values():
            all_v_locs = [loc for loc in sorted(node.locations, key=lambda x: x['year'])
                          if loc.get('lat') is not None and loc.get('lon') is not None]
            locs_in_yr = [l for l in all_v_locs if l['year'] == year]
            if locs_in_yr and len(locs_in_yr) >= k_step:
                loc_k = locs_in_yr[k_step - 1]
                idx = all_v_locs.index(loc_k)
                if idx > 0:
                    needs_movement = True
                    break

        if needs_movement:
            self.is_moving = True
            self.move_t = 0.0
            self._movement_loop()
        else:
            self.update_map_visuals(t=1.0)
            self.root.after(self.timeline_speed, self._map_loop)

    def _legacy_movement_loop(self):
        if not self.map_playing: return

        self.move_t += 0.08

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
        calculate_inheritance(self.tree)

    def calculate_positions(self):
        return calculate_positions(self.tree, self.isolated_root)

    def reset_view_to_root(self):
        self.root.update_idletasks()
        self.calculate_inheritance()
        self.positions = self.calculate_positions()

        if not self.positions: return

        if self.isolated_root and self.isolated_root in self.tree:
            roots = [self.isolated_root]
        else:
            roots = display_roots(self.tree)

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

    def refresh_plot(self):
        if not hasattr(self, 'canvas'):
            return

        self.calculate_inheritance()
        self.positions = self.calculate_positions()
        self.tree_renderer.render(
            canvas=self.canvas,
            tree=self.tree,
            positions=self.positions,
            ethnicity_colors=self.ethnicity_colors,
            show_decorations=self.show_decorations,
            canvas_scale=self.canvas_scale,
            pan_x=self.pan_x,
            pan_y=self.pan_y,
        )

    def on_press(self, event):
        drag_start = handle_press(self.canvas, event, self.open_parent_dialog, self.open_profile_dialog)
        if drag_start:
            self.drag_start_x, self.drag_start_y = drag_start

    def on_drag(self, event):
        self.drag_start_x, self.drag_start_y, dx, dy = handle_drag(
            self.canvas, event, (self.drag_start_x, self.drag_start_y)
        )
        self.pan_x += dx
        self.pan_y += dy

    def on_zoom(self, event):
        self.canvas_scale, self.pan_x, self.pan_y = handle_zoom(
            self.canvas, event, self.canvas_scale, self.pan_x, self.pan_y
        )

    # ---------------------------------------------------------
    # PARENT & PROFILE DIALOGS
    # ---------------------------------------------------------
    def open_parent_dialog(self, person_name):
        show_parent_dialog(self.root, self.tree, person_name, self.refresh_plot)

    def open_profile_dialog(self, person_name):
        show_profile_dialog(self, person_name, GEO_AVAILABLE)
    # ---------------------------------------------------------
    # FILE I/O
    # ---------------------------------------------------------
    def save_tree(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")])
        if not file_path: return

        save_tree_file(file_path, self.tree, self.ethnicity_options, self.ethnicity_colors)
        messagebox.showinfo("Saved", "Tree exported.")

    def load_tree(self, from_welcome=False):
        file_path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if not file_path: return False

        self.tree, self.ethnicity_options, self.ethnicity_colors = load_tree_file(file_path)

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
