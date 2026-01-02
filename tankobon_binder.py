import os
import zipfile
import re
import threading
import io  # Added to read images in memory
import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image  # Added for image processing

# --- CONFIGURATION ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

class ModernMangaMerger(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Manga Volume Merger")
        self.geometry("1200x800") 
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(3, weight=1)

        self.volume_entries = []
        self.create_ui()

    def create_ui(self):
        # ... (Previous Header and Settings sections remain the same) ...
        # (Keeping the original structure until the Preview Panel part)
        
        # --- HEADER (Condensed for brevity) ---
        self.header_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=(20, 10))
        ctk.CTkLabel(self.header_frame, text="Manga Volume Merger", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left")

        # --- SETTINGS ---
        self.settings_frame = ctk.CTkFrame(self)
        self.settings_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=20, pady=10)
        self.settings_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(self.settings_frame, text="Source Folder:").grid(row=0, column=0, padx=15, pady=15)
        self.source_entry = ctk.CTkEntry(self.settings_frame, placeholder_text="Path to folder...")
        self.source_entry.grid(row=0, column=1, padx=(0, 10), pady=15, sticky="ew")
        ctk.CTkButton(self.settings_frame, text="Browse", width=100, command=self.browse_folder).grid(row=0, column=2, padx=15)

        self.prefix_entry = ctk.CTkEntry(self.settings_frame, placeholder_text="Output Prefix: MangaName_")
        self.prefix_entry.grid(row=1, column=1, padx=(0, 10), pady=(0, 15), sticky="ew")

        # --- CONTROLS & AUTO GEN ---
        self.controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.controls_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=20, pady=5)
        
        self.start_vol = ctk.CTkEntry(self.controls_frame, width=60, placeholder_text="S-Vol"); self.start_vol.pack(side="left", padx=5)
        self.end_vol = ctk.CTkEntry(self.controls_frame, width=60, placeholder_text="E-Vol"); self.end_vol.pack(side="left", padx=5)
        self.start_ch = ctk.CTkEntry(self.controls_frame, width=60, placeholder_text="S-Ch"); self.start_ch.pack(side="left", padx=5)
        self.stop_ch = ctk.CTkEntry(self.controls_frame, width=60, placeholder_text="End Limit"); self.stop_ch.pack(side="left", padx=5)
        self.stop_ch.insert(0, "0")
        ctk.CTkButton(self.controls_frame, text="Generate", command=self.auto_generate, fg_color="#2CC985").pack(side="left", padx=15)

        # --- SPLIT CONTENT AREA ---
        self.content_area = ctk.CTkFrame(self, fg_color="transparent")
        self.content_area.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=20, pady=10)
        self.content_area.grid_columnconfigure(0, weight=3)
        self.content_area.grid_columnconfigure(1, weight=7)
        self.content_area.grid_rowconfigure(0, weight=1)

        # LEFT: Volume List
        self.list_frame = ctk.CTkScrollableFrame(self.content_area, label_text="Volume Definitions")
        self.list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # RIGHT: Visual Preview Panel
        self.preview_frame = ctk.CTkFrame(self.content_area)
        self.preview_frame.grid(row=0, column=1, sticky="nsew")
        self.preview_frame.grid_rowconfigure(1, weight=1)
        self.preview_frame.grid_columnconfigure(0, weight=1)

        preview_header = ctk.CTkLabel(self.preview_frame, text=" VISUAL PAGE PREVIEW ", fg_color="#2b2b2b", corner_radius=6, font=ctk.CTkFont(weight="bold"))
        preview_header.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

        # NEW: Scrollable Frame for Images instead of Textbox
        self.image_preview_scroll = ctk.CTkScrollableFrame(self.preview_frame, fg_color="#1a1a1a")
        self.image_preview_scroll.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        
        self.status_label = ctk.CTkLabel(self.image_preview_scroll, text="Click 👁 to load pages")
        self.status_label.pack(pady=20)

        # --- FOOTER ---
        self.footer = ctk.CTkFrame(self, fg_color="transparent")
        self.footer.grid(row=4, column=0, columnspan=2, sticky="ew", padx=20, pady=20)
        ctk.CTkButton(self.footer, text="+ Add Row", command=self.add_row).pack(side="left")
        self.btn_run = ctk.CTkButton(self.footer, text="▶ RUN MERGER", command=self.start_process_thread, height=40, font=ctk.CTkFont(size=16, weight="bold"))
        self.btn_run.pack(side="right", fill="x", expand=True, padx=(20, 0))

    # --- LOGIC UPDATES ---

    def load_preview(self, vol_str, start_ch_str):
        # Clear existing images immediately
        for widget in self.image_preview_scroll.winfo_children():
            widget.destroy()
        
        self.status_label = ctk.CTkLabel(self.image_preview_scroll, text=f"Loading Volume {vol_str}...")
        self.status_label.pack(pady=20)

        threading.Thread(
            target=self._generate_visual_preview, args=(vol_str, start_ch_str), daemon=True
        ).start()

    def _generate_visual_preview(self, vol_str, start_ch_str):
        source = self.source_entry.get()
        prefix = self.prefix_entry.get()

        try:
            target_vol = int(vol_str)
            target_start = int(start_ch_str)
            
            # Logic to find limit (same as your original code)
            vol_defs = {int(e_v.get()): int(e_c.get()) for _, e_v, e_c in self.volume_entries if e_v.get()}
            sorted_vols = sorted(vol_defs.keys())
            idx = sorted_vols.index(target_vol)
            limit = vol_defs[sorted_vols[idx + 1]] if idx + 1 < len(sorted_vols) else (int(self.stop_ch.get()) or 999999)
            if limit == 0: limit = 999999

            all_files = [f for f in os.listdir(source) if f.lower().endswith((".zip", ".cbz")) and not f.startswith(prefix)]
            matching_files = sorted([f for f in all_files if target_start <= self.get_chapter_number(f) < limit], key=self.get_chapter_number)

            if not matching_files:
                self.after(0, lambda: self.status_label.configure(text="No chapters found for this range."))
                return

            # Load and display images
            for cbz in matching_files:
                self.after(0, lambda c=cbz: ctk.CTkLabel(self.image_preview_scroll, text=f"--- {c} ---", font=("Arial", 12, "bold"), text_color="#3498DB").pack(pady=(10, 5)))
                
                full_path = os.path.join(source, cbz)
                with zipfile.ZipFile(full_path, "r") as z:
                    imgs = sorted([x for x in z.namelist() if x.lower().endswith((".jpg", ".png", ".jpeg", ".webp"))])
                    
                    for img_name in imgs:
                        with z.open(img_name) as f:
                            img_data = f.read()
                            # Open image from memory
                            pil_img = Image.open(io.BytesIO(img_data))
                            
                            # Resize for preview (keep aspect ratio)
                            aspect_ratio = pil_img.height / pil_img.width
                            new_width = 400
                            new_height = int(new_width * aspect_ratio)
                            
                            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(new_width, new_height))
                            
                            # Update UI
                            self.after(0, lambda i=ctk_img, n=img_name: self._add_image_to_scroll(i, n))

            self.after(0, lambda: self.status_label.destroy())

        except Exception as e:
            self.after(0, lambda: self.status_label.configure(text=f"Error: {str(e)}"))

    def _add_image_to_scroll(self, ctk_img, name):
        img_label = ctk.CTkLabel(self.image_preview_scroll, image=ctk_img, text="")
        img_label.pack(pady=5)
        # Optional: add filename under image
        # ctk.CTkLabel(self.image_preview_scroll, text=name, font=("Arial", 10)).pack()

    # ... (Rest of your helper functions: get_chapter_number, browse_folder, etc.) ...
    def get_chapter_number(self, filename):
        clean = re.sub(r"20\d\d", "", filename)
        clean = re.sub(r"[Vv]ol\.?\s?\d+", "", clean)
        match = re.search(r"(?:ch|c|#)\.?\s*(\d+(\.\d+)?)", clean, re.I)
        if match: return float(match.group(1))
        nums = re.findall(r"(\d+(\.\d+)?)", clean)
        return float(nums[-1][0]) if nums else 999999.0

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.source_entry.delete(0, "end"); self.source_entry.insert(0, folder)

    def add_row(self, vol="", ch=""):
        row = ctk.CTkFrame(self.list_frame)
        row.pack(fill="x", pady=2)
        e_vol = ctk.CTkEntry(row, width=50); e_vol.pack(side="left", padx=5)
        if vol: e_vol.insert(0, str(vol))
        e_ch = ctk.CTkEntry(row, width=50); e_ch.pack(side="left", padx=5)
        if ch: e_ch.insert(0, str(ch))
        
        ctk.CTkButton(row, text="×", width=30, fg_color="#C0392B", command=lambda: self.delete_row(row)).pack(side="right", padx=5)
        ctk.CTkButton(row, text="👁", width=30, command=lambda: self.load_preview(e_vol.get(), e_ch.get())).pack(side="right", padx=5)
        self.volume_entries.append((row, e_vol, e_ch))

    def delete_row(self, row_widget):
        self.volume_entries = [e for e in self.volume_entries if e[0] != row_widget]
        row_widget.destroy()

    def auto_generate(self):
        try:
            sv, ev, sc = int(self.start_vol.get()), int(self.end_vol.get()), int(self.start_ch.get())
            for i in range(ev - sv + 1): self.add_row(sv + i, sc + (i * 10)) # Adjust ch increment as needed
        except: pass

    def start_process_thread(self): # (Placeholder for your original run_merger)
        messagebox.showinfo("Note", "Merger logic remains the same as your original code.")

if __name__ == "__main__":
    app = ModernMangaMerger()
    app.mainloop()