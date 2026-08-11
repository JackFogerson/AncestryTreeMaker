"""Profile editing dialog."""

from __future__ import annotations

import tkinter as tk
from tkinter import colorchooser, messagebox, ttk

def open_profile_dialog(app, person_name, geocoder_available: bool):
    app.calculate_inheritance()
    dialog = tk.Toplevel(app.root)
    dialog.title(f"Manage Profile: {person_name}")
    dialog.geometry("750x780")
    dialog.transient(app.root)
    dialog.grab_set()

    node = app.tree[person_name]
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

    # Signifiers Panel
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

    computed_frame = tk.LabelFrame(genetics_main, text=" Computed Inherited Percentages ",
                                   font=("Arial", 10, "bold"), padx=10, pady=10, bg="#f8fafc")
    computed_frame.pack(fill=tk.X, pady=(0, 15))

    computed_list_frame = tk.Frame(computed_frame, bg="#f8fafc")
    computed_list_frame.pack(fill=tk.X, expand=True)

    def refresh_computed_breakdown():
        for widget in computed_list_frame.winfo_children():
            widget.destroy()

        active_eth = {k: v for k, v in node.computed_ethnicities.items() if v > 0}
        if not active_eth:
            tk.Label(computed_list_frame, text="No computed ethnicity data available.", font=("Arial", 9, "italic"),
                     bg="#f8fafc", fg="#64748b").pack(anchor=tk.W)
            return

        sorted_eth = sorted(active_eth.items(), key=lambda item: item[1], reverse=True)
        for eth, pct in sorted_eth:
            row = tk.Frame(computed_list_frame, bg="#f8fafc")
            row.pack(fill=tk.X, pady=2)

            clr = app.ethnicity_colors.get(eth, "#cbd5e1") if eth != "Unknown" else "#cbd5e1"
            tk.Label(row, bg=clr, width=2, height=1, relief=tk.SOLID, bd=1).pack(side=tk.LEFT, padx=(0, 8))
            tk.Label(row, text=f"{eth}:", font=("Arial", 9, "bold"), bg="#f8fafc", fg="#1e293b", width=16,
                     anchor=tk.W).pack(side=tk.LEFT)
            tk.Label(row, text=f"{pct:.1f}%", font=("Arial", 9, "bold"), bg="#f8fafc", fg="#047857").pack(
                side=tk.LEFT)

    refresh_computed_breakdown()

    base_frame = tk.LabelFrame(genetics_main, text=" Base Origins (Root Ancestor Settings) ",
                               font=("Arial", 10, "bold"), padx=10, pady=10, bg="#f8fafc")
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
        clr = colorchooser.askcolor(initialcolor=app.ethnicity_colors.get(ethnicity, "#cbd5e1"))
        if clr[1]:
            app.ethnicity_colors[ethnicity] = clr[1]
            render_checkboxes()
            refresh_computed_breakdown()

    def update_computed_preview():
        node.base_ethnicities = [eth for eth, var in vars_dict.items() if var.get()]
        app.calculate_inheritance()
        refresh_computed_breakdown()

    def render_checkboxes():
        for widget in cb_container.winfo_children(): widget.destroy()
        vars_dict.clear()
        for idx, eth in enumerate(app.ethnicity_options):
            var = tk.BooleanVar(value=(eth in node.base_ethnicities))
            vars_dict[eth] = var
            r, c = idx // 2, (idx % 2) * 2
            tk.Checkbutton(cb_container, text=eth, variable=var, font=("Arial", 9), bg="#f8fafc",
                           command=update_computed_preview).grid(row=r, column=c, sticky=tk.W, padx=(5, 2), pady=3)
            lbl = tk.Label(cb_container, bg=app.ethnicity_colors.get(eth, "#cbd5e1"), width=3, relief=tk.RAISED,
                           cursor="hand2")
            lbl.grid(row=r, column=c + 1, sticky=tk.W, padx=(0, 15))
            lbl.bind("<Button-1>", lambda e, e_name=eth: pick_edit_color(e_name))

    def add_eth():
        new_eth = new_eth_entry.get().strip().title()
        if new_eth and new_eth not in app.ethnicity_options:
            clr = colorchooser.askcolor()[1] or "#cbd5e1"
            app.ethnicity_options.append(new_eth)
            app.ethnicity_colors[new_eth] = clr
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

        if not geocoder_available:
            messagebox.showerror("Dependency Missing", "Please install geopy to use this feature.")
            return

        try:
            location = app.geolocator.geocode(place)
            if location:
                node.locations.append({
                    'year': year_val,
                    'place': location.address.split(',')[0].strip(),
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

        if geocoder_available and new_b_loc and (
                new_b_loc != getattr(node, 'birth_location', '') or new_b_year != node.birth_year):
            if new_b_year.isdigit():
                loc_data = app.geolocator.geocode(new_b_loc)
                if loc_data:
                    node.locations = [l for l in node.locations if l.get('type') != 'birth']
                    node.locations.append({
                        'year': int(new_b_year),
                        'place': loc_data.address.split(',')[0].strip(),
                        'lat': loc_data.latitude,
                        'lon': loc_data.longitude,
                        'type': 'birth'
                    })

        if geocoder_available and new_d_loc and not bio_living.get() and (
                new_d_loc != getattr(node, 'death_location', '') or new_d_year != node.death_year):
            if new_d_year.isdigit():
                loc_data = app.geolocator.geocode(new_d_loc)
                if loc_data:
                    node.locations = [l for l in node.locations if l.get('type') != 'death']
                    node.locations.append({
                        'year': int(new_d_year),
                        'place': loc_data.address.split(',')[0].strip(),
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
        app.refresh_plot()

    tk.Button(dialog, text="Save & Update Profile", command=save_profile, bg="#10b981", fg="white",
              font=("Arial", 11, "bold"), height=2).pack(fill=tk.X, padx=20, pady=15)


