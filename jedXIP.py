# jedXIP.py
# The main application with a Finder-style GUI using Tkinter.

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from jedXIP_logic import XipManager
import os
import threading
import time
from datetime import datetime
import json
import sys
import subprocess
import tempfile
import shutil
from tkinterdnd2 import DND_FILES, TkinterDnD
import queue

class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget; self.text = text; self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)
    def show_tooltip(self, event=None):
        if self.tooltip_window or not self.text: return
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25; y += self.widget.winfo_rooty() + 20
        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True); self.tooltip_window.wm_geometry(f"+{x}+{y}")
        label = ttk.Label(self.tooltip_window, text=self.text, justify=tk.LEFT, background="#2B2B2B", relief=tk.SOLID, borderwidth=1, padding=5, foreground="#FFFFFF")
        label.pack(ipadx=1)
    def hide_tooltip(self, event=None):
        if self.tooltip_window: self.tooltip_window.destroy()
        self.tooltip_window = None
    def update_text(self, new_text): self.text = new_text

class XipApp(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        self.title("jedXIP"); self.geometry("900x600"); self.minsize(700, 500)
        self.colors = {"bg": "#2B2B2B", "bg_light": "#3C3F41", "primary": "#007ACC", "text": "#FFFFFF", "text_dark": "#BBBBBB", "accent": "#4A90E2", "hover": "#555555"}
        self.fonts = {"main": ('Helvetica', 10), "bold": ('Helvetica', 10, 'bold')}
        try:
            self.folder_icon = tk.PhotoImage(file='folder.png'); self.file_icon = tk.PhotoImage(file='file.png')
            self.new_icon = tk.PhotoImage(file='new.png'); self.save_icon = tk.PhotoImage(file='save.png')
            self.open_icon = tk.PhotoImage(file='open.png'); self.extract_icon = tk.PhotoImage(file='extract.png')
            self.extract_selected_icon = tk.PhotoImage(file='extract_selected.png')
            self.help_icon = tk.PhotoImage(file='help.png')
            self.developer_icon = tk.PhotoImage(file='developer.png')
        except tk.TclError as e:
            print(f"Could not load an icon: {e}. Icons will not be displayed.")
            self.folder_icon=self.file_icon=self.new_icon=self.save_icon=self.open_icon=self.extract_icon=self.extract_selected_icon=self.help_icon=self.developer_icon = None
        self.logic = XipManager()
        self.source_type = None; self.source_path = None; self.view_contents = []
        self.staged_paths = []; self.current_nav_path = ""; self.item_path_map = {}
        self.file_types = [("XIP Archive", "*.xip"), ("XAR Archive", "*.xar"), ("All files", "*.*")]
        self.task_in_progress = False; self.temp_dir = tempfile.mkdtemp(prefix="jedxip_preview_"); self.last_hovered_item = None
        self.config_file = 'config.json'; self.recent_files = self._load_recent_files()
        self.progress_queue = queue.Queue()
        self._setup_styles(); self._create_widgets()
        self.drop_target_register(DND_FILES); self.dnd_bind('<<Drop>>', self._handle_drag_drop)
        self.protocol("WM_DELETE_WINDOW", self._on_closing); self._update_new_save_button_state()

    def _setup_styles(self):
        style = ttk.Style(self); style.theme_use('clam'); self.configure(background=self.colors["bg"])
        style.configure('.', background=self.colors["bg"], foreground=self.colors["text"], font=self.fonts["main"])
        style.configure('TFrame', background=self.colors["bg"]); style.configure('TLabel', background=self.colors["bg"], foreground=self.colors["text"])
        style.configure('TPanedWindow', background=self.colors["bg"])
        style.configure('TButton', padding=8, font=self.fonts["bold"], background=self.colors["primary"], foreground=self.colors["text"])
        style.map('TButton', background=[('active', self.colors["accent"]), ('disabled', self.colors["bg_light"])], foreground=[('disabled', self.colors["text_dark"])])
        style.configure('Toolbar.TButton', padding=5, relief=tk.FLAT, background=self.colors["bg"])
        style.map('Toolbar.TButton', background=[('active', self.colors["accent"]), ('hover', self.colors["hover"])])
        style.configure('Breadcrumb.TButton', relief=tk.FLAT, background=self.colors["bg"], foreground=self.colors["accent"])
        style.map('Breadcrumb.TButton', foreground=[('active', self.colors["text"]), ('hover', self.colors["text"])])
        style.configure('Toolbar.TMenubutton', padding=5, relief=tk.FLAT, background=self.colors["bg"])
        style.map('Toolbar.TMenubutton', background=[('active', self.colors["accent"]), ('hover', self.colors["hover"])])
        style.configure("Treeview", rowheight=28, font=self.fonts["main"], background=self.colors["bg_light"], fieldbackground=self.colors["bg_light"], foreground=self.colors["text"])
        style.configure("Treeview.Heading", font=self.fonts["bold"], padding=5)
        style.map('Treeview', background=[('selected', self.colors["primary"])], foreground=[('selected', self.colors["text"])])
        self.tree_hover_tag = 'hover'; style.configure(f'Treeview.{self.tree_hover_tag}', background=self.colors["hover"])
        style.configure("blue.Horizontal.TProgressbar", background=self.colors["accent"])
        style.configure("Link.TLabel", foreground=self.colors["accent"], font=(self.fonts["main"][0], 8))

    def _create_widgets(self):
        self._create_top_toolbar(); self._create_main_layout(); self._create_statusbar()

    def _create_top_toolbar(self):
        toolbar_frame = ttk.Frame(self, padding=5, relief=tk.RAISED, borderwidth=1)
        toolbar_frame.pack(side=tk.TOP, fill=tk.X)
        self.new_save_button = ttk.Button(toolbar_frame, image=self.new_icon, command=self.create_archive, style='Toolbar.TButton')
        self.new_save_button.pack(side=tk.LEFT, padx=2); self.new_save_tooltip = Tooltip(self.new_save_button, "New Archive")
        open_btn = ttk.Button(toolbar_frame, image=self.open_icon, command=self.open_archive, style='Toolbar.TButton')
        open_btn.pack(side=tk.LEFT, padx=2); Tooltip(open_btn, "Open Archive")
        self.recent_menu_button = ttk.Menubutton(toolbar_frame, text="Recent", style='Toolbar.TMenubutton')
        self.recent_menu = tk.Menu(self.recent_menu_button, tearoff=0); self.recent_menu_button["menu"] = self.recent_menu
        self.recent_menu_button.pack(side=tk.LEFT, padx=2); self._populate_recent_files_menu()
        ttk.Separator(toolbar_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=5, pady=2, fill='y')
        extract_btn = ttk.Button(toolbar_frame, image=self.extract_icon, command=self.extract_archive, style='Toolbar.TButton')
        extract_btn.pack(side=tk.LEFT, padx=2); Tooltip(extract_btn, "Extract All")
        extract_sel_btn = ttk.Button(toolbar_frame, image=self.extract_selected_icon, command=self.extract_selected, style='Toolbar.TButton')
        extract_sel_btn.pack(side=tk.LEFT, padx=2); Tooltip(extract_sel_btn, "Extract Selected")
        dev_btn = ttk.Button(toolbar_frame, image=self.developer_icon, command=self._show_developers_window, style='Toolbar.TButton')
        dev_btn.pack(side=tk.RIGHT, padx=2); Tooltip(dev_btn, "Developers")
        about_btn = ttk.Button(toolbar_frame, image=self.help_icon, command=self._show_about_window, style='Toolbar.TButton')
        about_btn.pack(side=tk.RIGHT, padx=2); Tooltip(about_btn, "About jedXIP")

    def _create_main_layout(self):
        main_paned_window = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_paned_window.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 10))
        sidebar_frame = ttk.Frame(main_paned_window, width=200, relief=tk.FLAT)
        sidebar_frame.pack_propagate(False)
        ttk.Label(sidebar_frame, text="jedXIP", font=('Helvetica', 14, 'bold'), padding=(10, 10), foreground=self.colors["accent"]).pack(anchor=tk.NW)
        
        # --- MODIFIED: Branding label updated to jedPlatforms ---
        branding_label = ttk.Label(sidebar_frame, text="© jedPlatforms", style="Link.TLabel")
        branding_label.pack(side=tk.BOTTOM, pady=10)
        
        main_paned_window.add(sidebar_frame, weight=1)
        content_frame = ttk.Frame(main_paned_window)
        self._create_main_panel(content_frame)
        main_paned_window.add(content_frame, weight=4)
        
    def _create_main_panel(self, parent):
        self.breadcrumb_frame = ttk.Frame(parent, padding=(0, 5)); self.breadcrumb_frame.pack(side=tk.TOP, fill=tk.X)
        self._update_breadcrumb_bar()
        main_frame = ttk.Frame(parent); main_frame.pack(fill=tk.BOTH, expand=True)
        columns = ('size', 'modified')
        self.tree = ttk.Treeview(main_frame, columns=columns, show='tree headings')
        self.tree.heading('#0', text='Name'); self.tree.column('#0', width=350, stretch=tk.YES)
        self.tree.heading('size', text='Size'); self.tree.heading('modified', text='Modified')
        self.tree.column('size', width=120, anchor=tk.E); self.tree.column('modified', width=180, anchor=tk.CENTER)
        self.tree.bind('<Button-3>', self._show_context_menu)
        self.tree.bind('<Motion>', self._on_tree_motion); self.tree.bind('<Leave>', self._on_tree_leave)
        self.tree.bind('<<TreeviewSelect>>', self.on_item_select); self.tree.bind('<Double-1>', self._on_item_double_click)
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set); scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _create_statusbar(self):
        self.statusbar_frame = ttk.Frame(self, relief=tk.SOLID, borderwidth=1)
        self.statusbar_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_var = tk.StringVar(value="Ready")
        self.status_label = ttk.Label(self.statusbar_frame, textvariable=self.status_var, anchor=tk.W, padding=5)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.progress_bar = ttk.Progressbar(self.statusbar_frame, orient='horizontal', mode='determinate', style="blue.Horizontal.TProgressbar")

    def _show_about_window(self):
        about_win = tk.Toplevel(self)
        about_win.title("About jedXIP")
        about_win.geometry("400x200")
        about_win.resizable(False, False); about_win.transient(self); about_win.grab_set()
        
        # --- MODIFIED: Branding updated ---
        about_text = ("jedXIP Archive Manager\n\n"
                      "A modern, lightweight tool for creating and managing .xip and .xar archives for Windows. \n\n"
                      "2025 jedPlatforms")
        
        about_frame = ttk.Frame(about_win, padding=20)
        about_frame.pack(expand=True, fill=tk.BOTH)
        about_label = ttk.Label(about_frame, text=about_text, wraplength=360, justify=tk.CENTER)
        about_label.pack(expand=True)

    def _show_developers_window(self):
        dev_win = tk.Toplevel(self)
        dev_win.title("Developers")
        dev_win.geometry("400x200")
        dev_win.resizable(False, False); dev_win.transient(self); dev_win.grab_set()

        developers = [
            ("Kyle L.", "Head of Development"),
            ("Michael S.", "Lead Backend Developer"),
            ("Mark A.", "UI/UX Designer")
        ]
        
        dev_frame = ttk.Frame(dev_win, padding=20)
        dev_frame.pack(expand=True, fill=tk.BOTH)
        
        # --- MODIFIED: Branding updated ---
        title_label = ttk.Label(dev_frame, text="Team behind jedXIP", font=self.fonts["bold"])
        title_label.pack(pady=(0, 15))

        for name, role in developers:
            dev_text = f"{name} - {role}"
            ttk.Label(dev_frame, text=dev_text).pack(pady=2)

    def _show_context_menu(self, event):
        item_id = self.tree.identify_row(event.y)
        if not item_id: return
        context_menu = tk.Menu(self, tearoff=0)
        selection = self.tree.selection()
        if item_id not in selection:
             self.tree.selection_set(item_id)
             selection = (item_id,)
        context_menu.add_command(label="Copy Path", command=self._copy_item_path)
        if self.source_type == 'archive':
            context_menu.add_separator()
            item_path = self.item_path_map.get(selection[0], "")
            if len(selection) == 1 and not item_path.endswith('/'):
                 context_menu.add_command(label="Preview / Open", command=self._context_preview)
            context_menu.add_command(label="Extract To...", command=self.extract_selected)
            context_menu.add_command(label="Extract Here (to Desktop)", command=self._context_extract_here)
            context_menu.add_command(label="Compress Selected to New Archive...", command=self._context_compress_selected)
        context_menu.post(event.x_root, event.y_root)

    # ... (The rest of the file is unchanged, including all logic and other methods) ...
    def _context_preview(self):
        item_id = self.tree.selection()[0]
        item_full_path = self.item_path_map.get(item_id)
        if item_full_path: self._preview_file(item_full_path)

    def _context_extract_here(self):
        if self.task_in_progress or self.source_type != 'archive': return
        desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
        target_path = os.path.join(desktop_path, "jedXIP_Extracted")
        os.makedirs(target_path, exist_ok=True)
        selected_ids = self.tree.selection()
        if not selected_ids: return
        files_to_extract = [self.item_path_map.get(iid) for iid in selected_ids if self.item_path_map.get(iid) != '..']
        if not files_to_extract: return
        self.current_action = f"Extracting to {os.path.basename(target_path)}..."
        def task(q, *args):
            success = self.logic.extract_selected(*args, progress_queue=q)
            self.after(0, self._task_finalizer, success, f"Successfully extracted to {target_path}", "Failed to extract selection.")
        self._run_task(task, self.source_path, files_to_extract, target_path)

    def _context_compress_selected(self):
        if self.task_in_progress or self.source_type != 'archive': return
        selected_ids = self.tree.selection()
        if not selected_ids: return messagebox.showwarning("No Selection", "Please select items to compress.")
        member_list = [self.item_path_map.get(iid) for iid in selected_ids if self.item_path_map.get(iid) != '..']
        if not member_list: return
        new_archive_path = filedialog.asksaveasfilename(title="Save New Archive As", filetypes=self.file_types, defaultextension=".xip")
        if not new_archive_path: return
        self.current_action = "Compressing selection..."
        def task(q, *args):
            success = self.logic.create_archive_from_members(*args, progress_queue=q)
            self.after(0, self._task_finalizer, success, "New archive created from selection!", "Failed to create archive.")
        self._run_task(task, self.source_path, member_list, new_archive_path)

    def _update_breadcrumb_bar(self):
        for widget in self.breadcrumb_frame.winfo_children(): widget.destroy()
        root_btn = ttk.Button(self.breadcrumb_frame, text="Root", style="Breadcrumb.TButton", command=lambda: self._on_breadcrumb_click(""))
        root_btn.pack(side=tk.LEFT)
        path_parts = self.current_nav_path.strip('/').split('/')
        if path_parts == ['']: path_parts = []
        full_path = ""
        for part in path_parts:
            full_path += part + "/"
            ttk.Label(self.breadcrumb_frame, text=" > ").pack(side=tk.LEFT)
            btn = ttk.Button(self.breadcrumb_frame, text=part, style="Breadcrumb.TButton", command=lambda p=full_path: self._on_breadcrumb_click(p))
            btn.pack(side=tk.LEFT)

    def _on_breadcrumb_click(self, path): self._navigate_to(path)
    def _navigate_to(self, new_path):
        self.current_nav_path = new_path; self.populate_view(); self._update_breadcrumb_bar()

    def _on_item_double_click(self, event):
        selection = self.tree.selection()
        if not selection: return
        item_id = selection[0]
        item_full_path = self.item_path_map.get(item_id)
        if item_full_path is None: return
        if item_full_path == "..":
            parent_path = os.path.dirname(self.current_nav_path.strip('/'))
            self._navigate_to(parent_path + '/' if parent_path else "")
            return
        is_folder = item_full_path.endswith('/')
        if is_folder: self._navigate_to(item_full_path)
        elif self.source_type == 'archive': self._preview_file(item_full_path)

    def populate_view(self):
        self.tree.delete(*self.tree.get_children()); self.item_path_map.clear(); self.last_hovered_item = None
        if self.current_nav_path:
            iid = self.tree.insert("", tk.END, text="..", values=("UP", "")); self.item_path_map[iid] = ".."
        direct_children = {}
        for item in self.view_contents:
            path = item['filename']
            if path.startswith(self.current_nav_path):
                relative_path = path[len(self.current_nav_path):]
                if not relative_path or relative_path == '/': continue
                child_name = relative_path.split('/')[0]
                if child_name not in direct_children:
                    is_folder = (len(relative_path.split('/')) > 1 and relative_path.split('/')[1] != '') or path.endswith('/')
                    full_child_path = self.current_nav_path + child_name + ("/" if is_folder else "")
                    direct_children[child_name] = {'filename': full_child_path, 'is_folder': is_folder}
        for name, data in sorted(direct_children.items()):
            is_folder = data['is_folder']
            icon = self.folder_icon if is_folder else self.file_icon
            original_item = next((i for i in self.view_contents if i['filename'] == data['filename']), {})
            formatted_size = self._format_bytes(original_item.get('size', 0))
            modified_time = original_item.get('modified', '')
            iid = self.tree.insert("", tk.END, text=name, image=icon, values=(formatted_size, modified_time))
            self.item_path_map[iid] = data['filename']
            
    def _copy_item_path(self):
        selected_id = self.tree.selection()
        if not selected_id: return
        item_path = self.item_path_map.get(selected_id[0], "")
        self.clipboard_clear(); self.clipboard_append(item_path)
        self._set_status_message(f"Copied to clipboard: {item_path}")

    def _update_new_save_button_state(self):
        if self.source_type == 'staged':
            self.new_save_button.configure(image=self.save_icon)
            self.new_save_tooltip.update_text("Save Archive")
        else:
            self.new_save_button.configure(image=self.new_icon)
            self.new_save_tooltip.update_text("New Archive")

    def _load_recent_files(self):
        try:
            with open(self.config_file, 'r') as f: return json.load(f).get('recent_files', [])
        except (FileNotFoundError, json.JSONDecodeError): return []

    def _update_recent_files(self, filepath):
        if filepath in self.recent_files: self.recent_files.remove(filepath)
        self.recent_files.insert(0, filepath); self.recent_files = self.recent_files[:5]
        with open(self.config_file, 'w') as f: json.dump({'recent_files': self.recent_files}, f)
        self._populate_recent_files_menu()

    def _populate_recent_files_menu(self):
        self.recent_menu.delete(0, tk.END)
        for path in self.recent_files:
            self.recent_menu.add_command(label=os.path.basename(path), command=lambda p=path: self.open_archive(filepath=p))
        if not self.recent_files: self.recent_menu.add_command(label="No recent files", state=tk.DISABLED)

    def _format_bytes(self, size):
        if not isinstance(size, (int, float)) or size == 0: return ""
        power = 1024; n = 0; power_labels = {0: '', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}
        while size > power and n < len(power_labels) - 1: size /= power; n += 1
        return f"{size:.1f} {power_labels[n]}"

    def _set_status_message(self, message):
        self.status_var.set(message); self.update_idletasks()

    def on_item_select(self, event):
        if self.source_type == 'archive': msg = f"{len(self.view_contents)} items in archive"
        else: msg = f"{len(self.staged_paths)} items staged"
        selected_items = self.tree.selection()
        if selected_items: msg = f"{len(selected_items)} of {len(self.tree.get_children(''))} selected"
        self._set_status_message(msg)

    def open_archive(self, filepath=None):
        if self.task_in_progress: return
        if not filepath: filepath = filedialog.askopenfilename(filetypes=[("XIP/XAR Archives", "*.xip *.xar"), ("All files", "*.*")])
        if not filepath: return
        contents = self.logic.list_contents(filepath)
        if contents is not None:
            self.source_type = 'archive'; self.source_path = filepath; self.view_contents = contents
            self.title(f"jedXIP - {os.path.basename(filepath)}")
            self._set_status_message(f"{len(self.view_contents)} items loaded")
            self._navigate_to(""); self._update_recent_files(filepath); self._update_new_save_button_state()
        else:
            messagebox.showerror("Error", "Failed to open archive.")
            self._set_status_message("Error opening file")

    def _handle_drag_drop(self, event):
        if self.task_in_progress: return
        self.source_type = 'staged'; self.source_path = None; self.staged_paths = self.tk.splitlist(event.data)
        temp_contents = []
        for path in self.staged_paths:
            if os.path.isfile(path): temp_contents.append({'filename': os.path.basename(path), 'size': os.path.getsize(path), 'modified': datetime.fromtimestamp(os.path.getmtime(path)).strftime('%Y-%m-%d %H:%M:%S')})
            elif os.path.isdir(path):
                for root, _, files in os.walk(path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        relative_path = os.path.relpath(file_path, os.path.dirname(path))
                        temp_contents.append({'filename': relative_path.replace('\\', '/'), 'size': os.path.getsize(file_path), 'modified': datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S')})
        self.view_contents = temp_contents
        self.title("jedXIP - New Archive"); self._navigate_to(""); self._update_new_save_button_state()

    def _run_task(self, task_func, *args):
        if self.task_in_progress: return messagebox.showwarning("In Progress", "Another operation is already in progress.")
        self.task_in_progress = True; self.status_label.pack_forget() 
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=2)
        thread = threading.Thread(target=task_func, args=(self.progress_queue, *args), daemon=True); thread.start()
        self.after(100, self._poll_progress_queue, thread)

    def _poll_progress_queue(self, thread):
        if not thread.is_alive(): return
        try:
            message = self.progress_queue.get_nowait()
            if isinstance(message, dict) and 'total' in message:
                self.progress_bar['maximum'] = message['total']; self.progress_bar['value'] = 0
                self._set_status_message(self.current_action)
            elif message == 'increment': self.progress_bar.step()
        except queue.Empty: pass
        finally: self.after(100, self._poll_progress_queue, thread)

    def _task_finalizer(self, success, success_msg="", error_msg=""):
        self.progress_bar.pack_forget(); self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        if success and success_msg: messagebox.showinfo("Success", success_msg); self._set_status_message(success_msg)
        elif not success: messagebox.showerror("Error", error_msg); self._set_status_message("An error occurred.")
        self.task_in_progress = False

    def create_archive(self):
        if self.task_in_progress: return
        source_paths = []
        if self.source_type == 'staged': source_paths = self.staged_paths
        else:
            source_type = self._ask_source_type()
            if source_type == "files":
                paths = filedialog.askopenfilenames(title="Select Files to Compress");
                if paths: source_paths = list(paths)
            elif source_type == "folder":
                path = filedialog.askdirectory(title="Select a Folder to Compress")
                if path: source_paths = [path]
            else: return
        if not source_paths: return
        archive_path = filedialog.asksaveasfilename(title="Save Archive As", filetypes=self.file_types, defaultextension=".xip")
        if not archive_path: return
        self.current_action = "Creating Archive..."
        def task(q, *args):
            success = self.logic.create_archive(*args, progress_queue=q)
            if success: self.after(0, self.open_archive, archive_path)
            self.after(0, self._task_finalizer, success, "Archive created successfully!", "Failed to create archive.")
        self._run_task(task, source_paths, archive_path)

    def extract_archive(self):
        if self.task_in_progress or self.source_type != 'archive': return
        dest_path = filedialog.askdirectory(title="Select Destination Folder")
        if not dest_path: return
        self.current_action = "Extracting All..."
        def task(q, *args):
            success = self.logic.extract_archive(*args, progress_queue=q)
            self.after(0, self._task_finalizer, success, "Archive extracted successfully!", "Failed to extract archive.")
        self._run_task(task, self.source_path, dest_path)

    def extract_selected(self):
        if self.task_in_progress or self.source_type != 'archive': return
        selected_ids = self.tree.selection()
        if not selected_ids: return messagebox.showwarning("No Selection", "Please select items to extract.")
        files_to_extract = [self.item_path_map.get(iid) for iid in selected_ids if self.item_path_map.get(iid) != '..']
        if not files_to_extract: return
        dest_path = filedialog.askdirectory(title="Select Destination Folder")
        if not dest_path: return
        self.current_action = "Extracting Selection..."
        def task(q, *args):
            success = self.logic.extract_selected(*args, progress_queue=q)
            self.after(0, self._task_finalizer, success, "Selected items extracted successfully!", "Failed to extract selection.")
        self._run_task(task, self.source_path, files_to_extract, dest_path)

    def _preview_file(self, item_path):
        self._set_status_message(f"Opening: {os.path.basename(item_path)}...")
        success = self.logic.extract_selected(self.source_path, [item_path], self.temp_dir)
        if success:
            temp_file_path = os.path.join(self.temp_dir, item_path)
            try:
                if sys.platform == "win32": os.startfile(temp_file_path)
                elif sys.platform == "darwin": subprocess.call(["open", temp_file_path])
                else: subprocess.call(["xdg-open", temp_file_path])
            except Exception as e: messagebox.showerror("Error", f"Could not open the file.\n{e}")
        else: messagebox.showerror("Error", "Could not extract the file for preview.")
        self._set_status_message("Ready")

    def _on_closing(self):
        try:
            shutil.rmtree(self.temp_dir)
            print(f"Temporary directory {self.temp_dir} cleaned up.")
        except Exception as e: print(f"Error cleaning up temporary directory: {e}")
        finally: self.destroy()

    def _on_tree_motion(self, event):
        item_id = self.tree.identify_row(event.y)
        if self.last_hovered_item and self.last_hovered_item != item_id:
            if self.tree.exists(self.last_hovered_item): self.tree.item(self.last_hovered_item, tags=())
        self.last_hovered_item = item_id
        if item_id:
            if self.tree.exists(item_id): self.tree.item(item_id, tags=(self.tree_hover_tag,))

    def _on_tree_leave(self, event):
        if self.last_hovered_item:
            if self.tree.exists(self.last_hovered_item): self.tree.item(self.last_hovered_item, tags=())
            self.last_hovered_item = None

    def _ask_source_type(self):
        dialog = tk.Toplevel(self); dialog.title("Choose Source"); dialog.geometry("300x120")
        dialog.resizable(False, False); dialog.transient(self); dialog.grab_set()
        result = tk.StringVar()
        def set_choice(choice): result.set(choice); dialog.destroy()
        main_frame = ttk.Frame(dialog, padding=10); main_frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(main_frame, text="What would you like to archive?", font=self.fonts["bold"]).pack(pady=(0, 10))
        btn_frame = ttk.Frame(main_frame); btn_frame.pack(fill=tk.X, expand=True)
        files_btn = ttk.Button(btn_frame, text="Select Files", command=lambda: set_choice("files"))
        files_btn.pack(side=tk.LEFT, expand=True, padx=5)
        folder_btn = ttk.Button(btn_frame, text="Select Folder", command=lambda: set_choice("folder"))
        folder_btn.pack(side=tk.RIGHT, expand=True, padx=5)
        self.wait_window(dialog)
        return result.get()

if __name__ == "__main__":
    app = XipApp()
    if len(sys.argv) > 1:
        filepath_to_open = sys.argv[1]
        if os.path.exists(filepath_to_open):
            app.after(100, lambda: app.open_archive(filepath=filepath_to_open))
    app.mainloop()
