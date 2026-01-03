import os
import zipfile
import re
import threading
import io
from PIL import Image
import customtkinter as ctk
from tkinter import filedialog, messagebox

# --- CONFIGURATION ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")


class ChapterAccordion(ctk.CTkFrame):
    """
    A dropdown for a SINGLE chapter.
    Contains rows of Page Buttons.
    """

    def __init__(self, parent, chapter_filename, zip_path, image_list):
        super().__init__(parent, fg_color="transparent")

        self.is_expanded = False
        self.has_loaded_content = False
        self.chapter_name = chapter_filename
        self.zip_path = zip_path
        self.image_list = image_list

        # Track active images to toggle them {page_name: widget}
        self.open_image_widgets = {}

        # 1. Header Button
        self.toggle_btn = ctk.CTkButton(
            self,
            text=f"▶  {self.chapter_name}",
            command=self.toggle,
            fg_color="#2B2B2B",
            hover_color="#3A3A3A",
            anchor="w",
            height=30,
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.toggle_btn.pack(fill="x", pady=(0, 2))

        # 2. Content Frame (Hidden initially)
        self.content_frame = ctk.CTkFrame(self, fg_color="#1e1e1e")

    def toggle(self):
        if self.is_expanded:
            self.content_frame.pack_forget()
            self.toggle_btn.configure(text=f"▶  {self.chapter_name}")
        else:
            self.content_frame.pack(fill="x", padx=10)
            self.toggle_btn.configure(text=f"▼  {self.chapter_name}")

            if not self.has_loaded_content:
                self.load_page_buttons()
                self.has_loaded_content = True

        self.is_expanded = not self.is_expanded

    def load_page_buttons(self):
        if not self.image_list:
            ctk.CTkLabel(
                self.content_frame, text="(No images found)", text_color="gray"
            ).pack(pady=5)
            return

        # Create a "Row Frame" for each page
        # This allows us to pack the image INSIDE this row, directly below the button
        for img_name in self.image_list:
            row_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
            row_frame.pack(fill="x", pady=1)

            btn = ctk.CTkButton(
                row_frame,
                text=f"📄 {os.path.basename(img_name)}",
                # Pass the row_frame so we know where to put the image
                command=lambda r=row_frame, i=img_name: self.toggle_image_inline(r, i),
                fg_color="transparent",
                hover_color="#333333",
                anchor="w",
                height=24,
                font=ctk.CTkFont(family="Consolas", size=11),
            )
            btn.pack(fill="x", padx=5)

    def toggle_image_inline(self, row_frame, img_path):
        # 1. Check if image is already open for this path
        if img_path in self.open_image_widgets:
            # CLOSE IT
            widget = self.open_image_widgets[img_path]
            widget.destroy()
            del self.open_image_widgets[img_path]
            return

        # 2. OPEN IT
        try:
            # Read image from zip
            with zipfile.ZipFile(self.zip_path, "r") as z:
                img_data = z.read(img_path)

            pil_image = Image.open(io.BytesIO(img_data))

            # Resize for preview (Max width 450 to fit nicely)
            w, h = pil_image.size
            aspect = w / h
            target_w = 450
            target_h = int(target_w / aspect)

            ctk_img = ctk.CTkImage(
                light_image=pil_image, dark_image=pil_image, size=(target_w, target_h)
            )

            # Create the Label containing the image
            # We pack it into 'row_frame' so it appears right under the button we clicked
            img_label = ctk.CTkLabel(row_frame, text="", image=ctk_img)
            img_label.pack(pady=5)

            # Track it so we can close it later
            self.open_image_widgets[img_path] = img_label

        except Exception as e:
            err_label = ctk.CTkLabel(row_frame, text=f"Error: {e}", text_color="red")
            err_label.pack()
            self.open_image_widgets[img_path] = err_label


class ModernMangaMerger(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window Setup
        self.title("Manga Volume Merger")
        self.geometry("1200x800")
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(3, weight=1)

        self.volume_entries = []
        self.active_accordions = []

        self.create_ui()

    def create_ui(self):
        # --- HEADER ---
        self.header_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.header_frame.grid(
            row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=(20, 10)
        )

        title = ctk.CTkLabel(
            self.header_frame,
            text="Manga Volume Merger",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        title.pack(side="left")

        # --- SETTINGS SECTION ---
        self.settings_frame = ctk.CTkFrame(self)
        self.settings_frame.grid(
            row=1, column=0, columnspan=2, sticky="ew", padx=20, pady=10
        )
        self.settings_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.settings_frame, text="Source Folder:").grid(
            row=0, column=0, padx=15, pady=15, sticky="w"
        )
        self.source_entry = ctk.CTkEntry(
            self.settings_frame,
            placeholder_text="Path to folder containing .zip/.cbz files",
        )
        self.source_entry.grid(row=0, column=1, padx=(0, 10), pady=15, sticky="ew")

        btn_browse = ctk.CTkButton(
            self.settings_frame, text="Browse", width=100, command=self.browse_folder
        )
        btn_browse.grid(row=0, column=2, padx=15, pady=15)

        ctk.CTkLabel(self.settings_frame, text="Output Prefix:").grid(
            row=1, column=0, padx=15, pady=(0, 15), sticky="w"
        )
        self.prefix_entry = ctk.CTkEntry(
            self.settings_frame, placeholder_text="e.g. MangaName_"
        )
        self.prefix_entry.grid(row=1, column=1, padx=(0, 10), pady=(0, 15), sticky="ew")

        # --- AUTO GENERATE & CONTROLS ---
        self.controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.controls_frame.grid(
            row=2, column=0, columnspan=2, sticky="ew", padx=20, pady=5
        )

        self.gen_frame = ctk.CTkFrame(self.controls_frame)
        self.gen_frame.pack(side="top", fill="x", pady=(0, 10))

        ctk.CTkLabel(
            self.gen_frame, text="Auto-Generator:", font=ctk.CTkFont(weight="bold")
        ).pack(side="left", padx=15, pady=10)

        self.start_vol = ctk.CTkEntry(
            self.gen_frame, width=80, placeholder_text="Start Vol"
        )
        self.start_vol.pack(side="left", padx=5)

        self.end_vol = ctk.CTkEntry(
            self.gen_frame, width=80, placeholder_text="End Vol"
        )
        self.end_vol.pack(side="left", padx=5)

        self.start_ch = ctk.CTkEntry(
            self.gen_frame, width=80, placeholder_text="Start Ch"
        )
        self.start_ch.pack(side="left", padx=5)

        self.stop_ch = ctk.CTkEntry(
            self.gen_frame, width=80, placeholder_text="Stop Ch (0)"
        )
        self.stop_ch.pack(side="left", padx=5)
        self.stop_ch.insert(0, "0")

        btn_gen = ctk.CTkButton(
            self.gen_frame,
            text="Generate List",
            command=self.auto_generate,
            fg_color="#2CC985",
            hover_color="#229A65",
        )
        btn_gen.pack(side="left", padx=15)

        # --- SPLIT CONTENT AREA ---
        self.content_area = ctk.CTkFrame(self, fg_color="transparent")
        self.content_area.grid(
            row=3, column=0, columnspan=2, sticky="nsew", padx=20, pady=10
        )
        self.content_area.grid_columnconfigure(0, weight=4)
        self.content_area.grid_columnconfigure(1, weight=6)
        self.content_area.grid_rowconfigure(0, weight=1)

        # LEFT: Volume List
        self.list_frame = ctk.CTkScrollableFrame(
            self.content_area, label_text="Volume Definitions"
        )
        self.list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # RIGHT: Preview Panel
        self.preview_frame = ctk.CTkFrame(self.content_area)
        self.preview_frame.grid(row=0, column=1, sticky="nsew")
        self.preview_frame.grid_rowconfigure(1, weight=1)
        self.preview_frame.grid_columnconfigure(0, weight=1)

        # Preview Header
        preview_header_bar = ctk.CTkFrame(
            self.preview_frame, fg_color="#2b2b2b", corner_radius=6
        )
        preview_header_bar.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

        self.lbl_prev_title = ctk.CTkLabel(
            preview_header_bar,
            text=" SELECT A VOLUME ",
            font=ctk.CTkFont(weight="bold"),
        )
        self.lbl_prev_title.pack(side="left", padx=10, pady=5)

        # Preview Container
        self.preview_container = ctk.CTkScrollableFrame(
            self.preview_frame, fg_color="transparent"
        )
        self.preview_container.grid(
            row=1, column=0, sticky="nsew", padx=10, pady=(0, 10)
        )

        self.lbl_instruction = ctk.CTkLabel(
            self.preview_container,
            text="Click the '👁' button on a row\nto load chapters and preview pages.",
            text_color="gray",
        )
        self.lbl_instruction.pack(pady=20)

        # --- FOOTER ---
        self.footer = ctk.CTkFrame(self, height=60, fg_color="transparent")
        self.footer.grid(row=4, column=0, columnspan=2, sticky="ew", padx=20, pady=20)

        btn_add = ctk.CTkButton(
            self.footer, text="+ Add Row", command=self.add_row, width=120
        )
        btn_add.pack(side="left")

        btn_clear = ctk.CTkButton(
            self.footer,
            text="Clear List",
            command=self.clear_list,
            width=120,
            fg_color="#C0392B",
            hover_color="#922B21",
        )
        btn_clear.pack(side="left", padx=10)

        self.btn_run = ctk.CTkButton(
            self.footer,
            text="▶ RUN MERGER",
            command=self.start_process_thread,
            height=40,
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        self.btn_run.pack(side="right", fill="x", expand=True, padx=(20, 0))

    # --- LOGIC ---
    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.source_entry.delete(0, "end")
            self.source_entry.insert(0, folder)

    def add_row(self, vol="", ch=""):
        row = ctk.CTkFrame(self.list_frame)
        row.pack(fill="x", pady=2)

        ctk.CTkLabel(row, text="Vol:").pack(side="left", padx=(5, 2))
        e_vol = ctk.CTkEntry(row, width=50)
        e_vol.pack(side="left", pady=5)
        if vol:
            e_vol.insert(0, str(vol))

        ctk.CTkLabel(row, text="Start:").pack(side="left", padx=(10, 2))
        e_ch = ctk.CTkEntry(row, width=50)
        e_ch.pack(side="left", pady=5)
        if ch:
            e_ch.insert(0, str(ch))

        btn_del = ctk.CTkButton(
            row,
            text="×",
            width=30,
            height=25,
            fg_color="#C0392B",
            hover_color="#922B21",
            command=lambda: self.delete_row(row),
        )
        btn_del.pack(side="right", padx=5)

        btn_prev = ctk.CTkButton(
            row,
            text="👁",
            width=30,
            height=25,
            fg_color="#3498DB",
            hover_color="#2980B9",
            command=lambda: self.load_preview(e_vol.get(), e_ch.get()),
        )
        btn_prev.pack(side="right", padx=5)

        self.volume_entries.append((row, e_vol, e_ch))

    def delete_row(self, row_widget):
        self.volume_entries = [
            entry for entry in self.volume_entries if entry[0] != row_widget
        ]
        row_widget.destroy()

    def clear_list(self):
        for entry in self.volume_entries:
            entry[0].destroy()
        self.volume_entries = []

    def auto_generate(self):
        try:
            sv = int(self.start_vol.get())
            ev = int(self.end_vol.get())
            sc = int(self.start_ch.get())
            count = ev - sv + 1
            if count <= 0:
                raise ValueError
            self.clear_list()
            for i in range(count):
                self.add_row(sv + i, sc + (i * 4))
        except ValueError:
            messagebox.showerror("Error", "Please enter valid integers.")

    # --- PREVIEW LOGIC ---
    def clear_previews(self):
        for widget in self.preview_container.winfo_children():
            widget.destroy()
        self.active_accordions.clear()

    def load_preview(self, vol_str, start_ch_str):
        self.lbl_prev_title.configure(text=f" LOADING VOLUME {vol_str}... ")
        self.clear_previews()
        threading.Thread(
            target=self._scan_and_build_preview,
            args=(vol_str, start_ch_str),
            daemon=True,
        ).start()

    def _scan_and_build_preview(self, vol_str, start_ch_str):
        source = self.source_entry.get()
        prefix = self.prefix_entry.get()

        if not source or not os.path.exists(source):
            return

        try:
            target_vol = int(vol_str)
            target_start = int(start_ch_str)
        except ValueError:
            return

        # 1. Determine Limits
        vol_defs = {}
        for _, e_v, e_c in self.volume_entries:
            try:
                vol_defs[int(e_v.get())] = int(e_c.get())
            except:
                continue

        sorted_vols = sorted(vol_defs.keys())
        try:
            idx = sorted_vols.index(target_vol)
            if idx + 1 < len(sorted_vols):
                limit = vol_defs[sorted_vols[idx + 1]]
            else:
                try:
                    limit = int(self.stop_ch.get())
                except:
                    limit = 0
                if limit == 0:
                    limit = 999999
        except ValueError:
            limit = 999999

        # 2. Find Chapters
        all_files = [
            f for f in os.listdir(source) if f.lower().endswith((".zip", ".cbz"))
        ]
        matching_files = []

        for f in all_files:
            if prefix and f.startswith(prefix):
                continue

            c_num = self.get_chapter_number(f)
            if c_num >= target_start and c_num < limit:
                matching_files.append(f)

        matching_files.sort(key=self.get_chapter_number)

        # 3. Read structure
        preview_data = []
        if not matching_files:
            self.after(0, lambda: self._show_no_files_msg(target_vol))
            return

        for cbz in matching_files:
            full_path = os.path.join(source, cbz)
            pages = []
            try:
                with zipfile.ZipFile(full_path, "r") as z:
                    pages = [
                        x
                        for x in z.namelist()
                        if x.lower().endswith((".jpg", ".png", ".jpeg", ".webp"))
                    ]
                    pages.sort()
            except:
                pass

            preview_data.append({"name": cbz, "path": full_path, "pages": pages})

        self.after(0, lambda: self._build_accordions(target_vol, preview_data))

    def _show_no_files_msg(self, vol_num):
        self.lbl_prev_title.configure(text=f" VOLUME {vol_num} - NO FILES FOUND ")
        ctk.CTkLabel(
            self.preview_container, text="No chapters matched your criteria."
        ).pack(pady=20)

    def _build_accordions(self, vol_num, data):
        self.lbl_prev_title.configure(text=f" VOLUME {vol_num} CONTENT ")

        if not data:
            return

        for chap_data in data:
            accordion = ChapterAccordion(
                self.preview_container,
                chapter_filename=chap_data["name"],
                zip_path=chap_data["path"],
                image_list=chap_data["pages"],
            )
            accordion.pack(fill="x", pady=2)
            self.active_accordions.append(accordion)

    # --- MAIN MERGE LOGIC ---
    def start_process_thread(self):
        threading.Thread(target=self.run_merger, daemon=True).start()

    def run_merger(self):
        source = self.source_entry.get()
        prefix = self.prefix_entry.get()

        if not source or not os.path.exists(source):
            messagebox.showerror("Error", "Invalid Source Folder")
            return
        if not self.volume_entries:
            messagebox.showerror("Error", "No volumes defined")
            return

        self.btn_run.configure(state="disabled", text="Processing...")

        try:
            stop_ch_input = self.stop_ch.get()
            stop_limit = int(stop_ch_input) if stop_ch_input else 0
        except:
            stop_limit = 0

        vol_defs = {}
        for _, e_v, e_c in self.volume_entries:
            try:
                vol_defs[int(e_v.get())] = int(e_c.get())
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
                self.create_cbz(source, prefix, vol_num, target_files)

        self.btn_run.configure(state="normal", text="▶ RUN MERGER")
        messagebox.showinfo("Done", "Processing Complete!")

    def get_chapter_number(self, filename):
        clean = re.sub(r"20\d\d", "", filename)
        clean = re.sub(r"[Vv]ol\.?\s?\d+", "", clean)
        match = re.search(r"(?:ch|c|#)\.?\s*(\d+(\.\d+)?)", clean, re.I)
        if match:
            return float(match.group(1))
        nums = re.findall(r"(\d+(\.\d+)?)", clean)
        return float(nums[-1][0]) if nums else 999999.0

    def create_cbz(self, folder, prefix, vol, files):
        out_name = f"{prefix}{vol:02d}.cbz"
        out_path = os.path.join(folder, out_name)

        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_STORED) as z_out:
            files.sort(key=self.get_chapter_number)
            for f in files:
                f_path = os.path.join(folder, f)
                try:
                    with zipfile.ZipFile(f_path, "r") as z_in:
                        imgs = [
                            x
                            for x in z_in.namelist()
                            if x.lower().endswith((".jpg", ".png", ".jpeg", ".webp"))
                        ]
                        imgs.sort()
                        c_num = self.get_chapter_number(f)
                        for img in imgs:
                            data = z_in.read(img)
                            new_name = (
                                f"v{vol:02d}_c{c_num:06.1f}_{os.path.basename(img)}"
                            )
                            z_out.writestr(new_name, data)
                except:
                    pass


if __name__ == "__main__":
    app = ModernMangaMerger()
    app.mainloop()
