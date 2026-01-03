import os
import zipfile
import re
import threading
import io
import sys
import subprocess
import requests
from PIL import Image, ImageEnhance, ImageTk
import customtkinter as ctk
from tkinter import filedialog, messagebox

# --- CONFIGURATION ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

REPO_OWNER = "VishwasPG12"
REPO_NAME = "Tankobon-Binder"
CURRENT_VERSION = "v2.1.0"

# --- PATH FIX ---
if getattr(sys, "frozen", False):
    application_path = os.path.dirname(sys.executable)
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

os.chdir(application_path)


class ImageUtils:
    @staticmethod
    def load_bg_image(path, width, height, darken_factor=0.3):
        if not os.path.exists(path):
            return None
        try:
            img = Image.open(path)

            # --- INTELLIGENT SCALING ---
            # We resize the image to be at least as big as the screen
            # while maintaining aspect ratio (Cover Mode)
            img_ratio = img.width / img.height
            target_ratio = width / height

            if target_ratio > img_ratio:
                # Screen is wider than image -> fit to width
                new_width = width
                new_height = int(width / img_ratio)
            else:
                # Screen is taller than image -> fit to height
                new_height = height
                new_width = int(height * img_ratio)

            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # --- CENTER CROP ---
            # Cut off the excess edges to fit exactly
            left = (new_width - width) / 2
            top = (new_height - height) / 2
            right = (new_width + width) / 2
            bottom = (new_height + height) / 2
            img = img.crop((left, top, right, bottom))

            # --- DARKEN ---
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(darken_factor)

            return ctk.CTkImage(light_image=img, dark_image=img, size=(width, height))
        except Exception as e:
            print(f"Image Load Error: {e}")
            return None


class ChapterAccordion(ctk.CTkFrame):
    def __init__(self, parent, chapter_filename, zip_path, image_list):
        super().__init__(parent, fg_color="#1e1e1e", corner_radius=6)
        self.is_expanded = False
        self.has_loaded_content = False
        self.chapter_name = chapter_filename
        self.zip_path = zip_path
        self.image_list = image_list
        self.open_image_widgets = {}

        self.toggle_btn = ctk.CTkButton(
            self,
            text=f"▶  {self.chapter_name}",
            command=self.toggle,
            fg_color="transparent",
            hover_color="#333333",
            anchor="w",
            height=30,
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.toggle_btn.pack(fill="x", pady=(0, 2))
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")

    def toggle(self):
        if self.is_expanded:
            self.content_frame.pack_forget()
            self.toggle_btn.configure(text=f"▶  {self.chapter_name}")
        else:
            self.content_frame.pack(fill="x", padx=10, pady=5)
            self.toggle_btn.configure(text=f"▼  {self.chapter_name}")
            if not self.has_loaded_content:
                self.load_page_buttons()
                self.has_loaded_content = True
        self.is_expanded = not self.is_expanded

    def load_page_buttons(self):
        if not self.image_list:
            ctk.CTkLabel(self.content_frame, text="(No images)").pack(pady=5)
            return
        for img_name in self.image_list:
            row_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
            row_frame.pack(fill="x", pady=1)
            btn = ctk.CTkButton(
                row_frame,
                text=f"📄 {os.path.basename(img_name)}",
                command=lambda r=row_frame, i=img_name: self.toggle_image_inline(r, i),
                fg_color="transparent",
                hover_color="#333333",
                anchor="w",
                height=24,
                font=ctk.CTkFont(family="Consolas", size=11),
            )
            btn.pack(fill="x", padx=5)

    def toggle_image_inline(self, row_frame, img_path):
        if img_path in self.open_image_widgets:
            widget = self.open_image_widgets[img_path]
            widget.destroy()
            del self.open_image_widgets[img_path]
            return
        try:
            with zipfile.ZipFile(self.zip_path, "r") as z:
                img_data = z.read(img_path)
            pil_image = Image.open(io.BytesIO(img_data))
            w, h = pil_image.size
            aspect = w / h
            target_w = 450
            target_h = int(target_w / aspect)
            ctk_img = ctk.CTkImage(
                light_image=pil_image, dark_image=pil_image, size=(target_w, target_h)
            )
            img_label = ctk.CTkLabel(row_frame, text="", image=ctk_img)
            img_label.pack(pady=5)
            self.open_image_widgets[img_path] = img_label
        except Exception:
            pass


class ModernMangaMerger(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"Manga Volume Merger ({CURRENT_VERSION})")

        # --- SCREEN SIZE DETECTION ---
        # We get the full screen size to ensure the image covers everything
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        self.geometry(f"{screen_w}x{screen_h}")

        # Force maximized window on startup
        try:
            self.after(0, lambda: self.state("zoomed"))
        except:
            pass  # Fails on Linux/Mac, safe to ignore

        # 1. SETUP WALLPAPER
        self.bg_label = ctk.CTkLabel(self, text="")
        self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)

        # Try automatic load
        bg_path = os.path.join(application_path, "assets", "bg.jpg")

        # Load image at SCREEN SIZE (not window size)
        bg_img = ImageUtils.load_bg_image(
            bg_path, screen_w, screen_h, darken_factor=0.4
        )

        # IF FAIL -> ASK USER
        if not bg_img:
            messagebox.showinfo(
                "Background", "Please select your background image (jpg/png)."
            )
            file_path = filedialog.askopenfilename(
                filetypes=[("Images", "*.jpg;*.png;*.jpeg")]
            )
            if file_path:
                bg_img = ImageUtils.load_bg_image(
                    file_path, screen_w, screen_h, darken_factor=0.4
                )

        if bg_img:
            self.bg_label.configure(image=bg_img)

        # 2. LAYOUT
        self.grid_columnconfigure(0, weight=4)
        self.grid_columnconfigure(1, weight=6)
        self.grid_rowconfigure(3, weight=1)

        self.volume_entries = []
        self.create_ui()
        self.check_for_updates()

    def create_ui(self):
        # HEADER
        title = ctk.CTkLabel(
            self,
            text="MANGA VOLUME MERGER",
            font=ctk.CTkFont(family="Impact", size=32),
            text_color="white",
        )
        title.grid(row=0, column=0, columnspan=2, pady=(20, 10))

        # SETTINGS (Transparent container)
        settings_frame = ctk.CTkFrame(self, fg_color="transparent")
        settings_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=50)
        settings_frame.grid_columnconfigure(1, weight=1)

        self.source_entry = ctk.CTkEntry(
            settings_frame,
            placeholder_text="Select Source Folder...",
            fg_color="#2b2b2b",
        )
        self.source_entry.grid(row=0, column=1, sticky="ew", padx=10)
        ctk.CTkButton(
            settings_frame, text="Browse", width=100, command=self.browse_folder
        ).grid(row=0, column=2)

        self.prefix_entry = ctk.CTkEntry(
            settings_frame,
            placeholder_text="Output Prefix (e.g. OPM_)",
            fg_color="#2b2b2b",
        )
        self.prefix_entry.grid(row=1, column=1, sticky="ew", padx=10, pady=10)

        # CONTROLS
        controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        controls_frame.grid(row=2, column=0, columnspan=2, pady=10)

        ctk.CTkLabel(
            controls_frame,
            text="Auto-Generator:",
            font=ctk.CTkFont(weight="bold"),
            text_color="white",
        ).pack(side="left", padx=10)
        self.start_vol = ctk.CTkEntry(
            controls_frame, width=60, placeholder_text="Start Vol"
        )
        self.start_vol.pack(side="left", padx=2)
        self.end_vol = ctk.CTkEntry(
            controls_frame, width=60, placeholder_text="End Vol"
        )
        self.end_vol.pack(side="left", padx=2)
        self.start_ch = ctk.CTkEntry(
            controls_frame, width=60, placeholder_text="Start Ch"
        )
        self.start_ch.pack(side="left", padx=2)
        self.stop_ch = ctk.CTkEntry(
            controls_frame, width=60, placeholder_text="Stop Ch"
        )
        self.stop_ch.pack(side="left", padx=2)
        self.stop_ch.insert(0, "0")
        ctk.CTkButton(
            controls_frame,
            text="Generate",
            command=self.auto_generate,
            width=80,
            fg_color="#27ae60",
        ).pack(side="left", padx=10)

        # CONTENT (Solid backgrounds required for text readability)
        self.list_frame = ctk.CTkScrollableFrame(
            self, label_text="VOLUMES", fg_color="#1a1a1a"
        )
        self.list_frame.grid(row=3, column=0, sticky="nsew", padx=(50, 10), pady=10)

        self.preview_container = ctk.CTkScrollableFrame(
            self, label_text="PREVIEW", fg_color="#1a1a1a"
        )
        self.preview_container.grid(
            row=3, column=1, sticky="nsew", padx=(10, 50), pady=10
        )
        ctk.CTkLabel(
            self.preview_container, text="Click '👁' to load preview.", text_color="gray"
        ).pack(pady=20)

        # FOOTER
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=4, column=0, columnspan=2, sticky="ew", padx=50, pady=20)
        ctk.CTkButton(footer, text="+ Add Row", command=self.add_row, width=100).pack(
            side="left"
        )
        ctk.CTkButton(
            footer, text="Clear", command=self.clear_list, width=80, fg_color="#c0392b"
        ).pack(side="left", padx=10)
        self.btn_run = ctk.CTkButton(
            footer,
            text="▶ START MERGE",
            command=self.start_process_thread,
            width=200,
            font=ctk.CTkFont(weight="bold"),
        )
        self.btn_run.pack(side="right")

    # --- LOGIC ---
    def browse_folder(self):
        f = filedialog.askdirectory()
        if f:
            self.source_entry.delete(0, "end")
            self.source_entry.insert(0, f)

    def add_row(self, vol="", ch=""):
        row = ctk.CTkFrame(self.list_frame, fg_color="#2b2b2b")
        row.pack(fill="x", pady=2)
        ctk.CTkLabel(row, text="Vol").pack(side="left", padx=2)
        e_vol = ctk.CTkEntry(row, width=40)
        e_vol.pack(side="left", padx=2)
        if vol:
            e_vol.insert(0, str(vol))
        ctk.CTkLabel(row, text="Ch").pack(side="left", padx=2)
        e_ch = ctk.CTkEntry(row, width=40)
        e_ch.pack(side="left", padx=2)
        if ch:
            e_ch.insert(0, str(ch))
        ctk.CTkButton(
            row,
            text="×",
            width=25,
            fg_color="#c0392b",
            command=lambda: self.delete_row(row),
        ).pack(side="right", padx=2)
        ctk.CTkButton(
            row,
            text="👁",
            width=25,
            command=lambda: self.load_preview(e_vol.get(), e_ch.get()),
        ).pack(side="right", padx=2)
        self.volume_entries.append((row, e_vol, e_ch))

    def delete_row(self, w):
        self.volume_entries = [e for e in self.volume_entries if e[0] != w]
        w.destroy()

    def clear_list(self):
        for e in self.volume_entries:
            e[0].destroy()
        self.volume_entries = []

    def auto_generate(self):
        try:
            sv, ev = int(self.start_vol.get()), int(self.end_vol.get())
            sc = int(self.start_ch.get())
            count = ev - sv + 1
            if count <= 0:
                raise ValueError
            self.clear_list()
            for i in range(count):
                self.add_row(sv + i, sc + (i * 4))
        except:
            messagebox.showerror("Error", "Invalid inputs")

    def load_preview(self, v, c):
        for w in self.preview_container.winfo_children():
            w.destroy()
        threading.Thread(target=self._scan, args=(v, c), daemon=True).start()

    def _scan(self, v_str, c_str):
        src = self.source_entry.get()
        if not os.path.exists(src):
            return
        try:
            tv, tc = int(v_str), int(c_str)
        except:
            return

        # Logic to find files
        vol_defs = {}
        for _, ev, ec in self.volume_entries:
            try:
                vol_defs[int(ev.get())] = int(ec.get())
            except:
                continue
        sorted_v = sorted(vol_defs.keys())
        limit = 999999
        if tv in sorted_v:
            idx = sorted_v.index(tv)
            if idx + 1 < len(sorted_v):
                limit = vol_defs[sorted_v[idx + 1]]

        all_f = [f for f in os.listdir(src) if f.lower().endswith((".zip", ".cbz"))]
        matches = []
        for f in all_f:
            if self.prefix_entry.get() and f.startswith(self.prefix_entry.get()):
                continue
            cn = self.get_chapter_number(f)
            if cn >= tc and cn < limit:
                matches.append(f)
        matches.sort(key=self.get_chapter_number)

        self.after(0, lambda: self._show_results(matches, src))

    def _show_results(self, files, src):
        if not files:
            ctk.CTkLabel(self.preview_container, text="No files found").pack(pady=10)
            return
        for f in files:
            p = os.path.join(src, f)
            pg = []
            try:
                with zipfile.ZipFile(p, "r") as z:
                    pg = z.namelist()
            except:
                pass
            ChapterAccordion(self.preview_container, f, p, pg).pack(fill="x", pady=2)

    def get_chapter_number(self, filename):
        clean = re.sub(r"20\d\d", "", filename)
        match = re.search(r"(?:ch|c|#)\.?\s*(\d+(\.\d+)?)", clean, re.I)
        return float(match.group(1)) if match else 999999.0

    def start_process_thread(self):
        threading.Thread(target=self.run_merger, daemon=True).start()

    def run_merger(self):
        # Full merge logic restored here for completeness
        source = self.source_entry.get()
        prefix = self.prefix_entry.get()
        if not os.path.exists(source):
            return

        self.btn_run.configure(state="disabled", text="Processing...")

        try:
            stop_limit = int(self.stop_ch.get())
        except:
            stop_limit = 0

        vol_defs = {}
        for _, ev, ec in self.volume_entries:
            try:
                vol_defs[int(ev.get())] = int(ec.get())
            except:
                continue

        sorted_vols = sorted(vol_defs.keys())
        all_files = [
            f for f in os.listdir(source) if f.lower().endswith((".zip", ".cbz"))
        ]

        for i, vol_num in enumerate(sorted_vols):
            start_c = vol_defs[vol_num]
            if i + 1 < len(sorted_vols):
                end_c = vol_defs[sorted_vols[i + 1]]
            else:
                end_c = stop_limit if stop_limit > 0 else 999999

            target_files = []
            for f in all_files:
                if prefix and f.startswith(prefix):
                    continue
                c_num = self.get_chapter_number(f)
                if stop_limit > 0 and c_num >= stop_limit:
                    continue
                if c_num >= start_c and c_num < end_c:
                    target_files.append(f)

            if target_files:
                out_name = f"{prefix}{vol_num:02d}.cbz"
                out_path = os.path.join(source, out_name)
                with zipfile.ZipFile(out_path, "w", zipfile.ZIP_STORED) as z_out:
                    target_files.sort(key=self.get_chapter_number)
                    for f in target_files:
                        f_path = os.path.join(source, f)
                        try:
                            with zipfile.ZipFile(f_path, "r") as z_in:
                                imgs = [
                                    x
                                    for x in z_in.namelist()
                                    if x.lower().endswith(
                                        (".jpg", ".png", ".jpeg", ".webp")
                                    )
                                ]
                                imgs.sort()
                                c_num_f = self.get_chapter_number(f)
                                for img in imgs:
                                    data = z_in.read(img)
                                    new_name = f"v{vol_num:02d}_c{c_num_f:06.1f}_{os.path.basename(img)}"
                                    z_out.writestr(new_name, data)
                        except:
                            pass

        self.btn_run.configure(state="normal", text="▶ START MERGE")
        messagebox.showinfo("Done", "Processing Complete!")

    def check_for_updates(self):
        url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"

        def _th():
            try:
                r = requests.get(url)
                if r.status_code == 200 and r.json()["tag_name"] > CURRENT_VERSION:
                    self.after(
                        0,
                        lambda: messagebox.showinfo("Update", "New version available!"),
                    )
            except:
                pass

        threading.Thread(target=_th, daemon=True).start()


if __name__ == "__main__":
    app = ModernMangaMerger()
    app.mainloop()
