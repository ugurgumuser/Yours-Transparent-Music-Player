import customtkinter as ctk
import tkinter as tk
import pygame
import os
import json
import random
import sys
import time
import textwrap
import re
import threading 
from tkinter import filedialog
from mutagen.mp3 import MP3
import ctypes 

print("Music Player Starting...")

ctk.set_appearance_mode("Dark")

class MusicPlayer(ctk.CTk):
    def __init__(self):
        super().__init__()

        try:
            myappid = 'ghost.musicplayer.standard.release' 
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except: pass

        self.compact_width = 340  
        self.expanded_width = 640 
        self.win_height = 540     
        
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = int((screen_width/2) - (self.compact_width/2))
        y = int((screen_height/2) - (self.win_height/2))
        
        self.geometry(f"{self.compact_width}x{self.win_height}+{x}+{y}")
        
        self.title("Music Player")
        self.resizable(False, False)
        self.overrideredirect(True) 
        
        self.TRANS_KEY = "#000001" 
        self.SOLID_BG = "#080808" 
        
        self.COLOR_PALETTE = [
            "#00FFFF", "#39FF14", "#FF073A", "#FE019A", 
            "#FFD300", "#BC13FE", "#FFFFFF"
        ]
        
        self.current_color_index = 0
        self.ACCENT_COLOR = self.COLOR_PALETTE[0] 
        self.last_folder_path = "" 
        self.transparent_mode = False 
        self.is_playlist_open = False 
        self.current_volume = 0.5 
        self.last_volume = 0.5 
        self.is_muted = False
        
        self.user_name = "Your" 
        self.user_logo = "Y"   
        self.is_first_run = False 

        # --- KRITIK DUZELTME BURADA ---
        self.favorites = [] 
        self.view_mode = "ALL" 
        # ------------------------------

        if getattr(sys, 'frozen', False):
            self.app_dir = os.path.dirname(sys.executable)
        else:
            self.app_dir = os.path.dirname(os.path.abspath(__file__))

        self.settings_file = os.path.join(self.app_dir, "player_settings.json")
        self.load_settings()

        self.configure(fg_color=self.TRANS_KEY)
        tk.Tk.configure(self, bg=self.TRANS_KEY)
        self.attributes("-transparentcolor", self.TRANS_KEY)
        self.attributes('-alpha', 1.0)
        self.attributes('-topmost', False)

        try: 
            pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=4096)
            pygame.mixer.init()
            pygame.mixer.music.set_volume(self.current_volume)
        except: pass
            
        self.playlist = []           
        self.original_playlist = [] 
        self.current_song_index = 0
        self.is_playing = False
        self.shuffle_mode = False 
        self.loop_mode = False
        self.song_length = 0 
        self.time_offset = 0 
        self.is_dragging = False 
        self.progress_loop_id = None
        self.drag_lock_timer = 0 

        self.font_title = ("Segoe UI", 15, "bold")
        self.font_signature = ("Segoe UI Semibold", 13) 
        self.font_icon_symbol = ("Segoe UI Symbol", 28) 
        self.font_main_art = ("Times New Roman", 85, "italic") 
        self.font_icon = ("Arial", 18) 
        self.font_ctrl_icon = ("Arial", 22)
        self.font_play_icon = ("Arial", 45)
        self.font_mini_logo = ("Times New Roman", 20, "italic")
        self.font_info_header = ("Times New Roman", 12, "italic")

        self.setup_ui()
        self.bind_events()
        
        self.apply_theme_color()
        self.apply_transparency()
        
        if self.last_folder_path and os.path.exists(self.last_folder_path):
            self.process_folder_threaded(self.last_folder_path)
            
        self.check_music_progress()

        if self.is_first_run:
            self.after(500, self.open_name_input_dialog)

    def load_settings(self):
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, "r") as f:
                    data = json.load(f)
                    self.last_folder_path = data.get("last_folder", "")
                    saved_index = data.get("color_index", 0)
                    if 0 <= saved_index < len(self.COLOR_PALETTE):
                        self.current_color_index = saved_index
                        self.ACCENT_COLOR = self.COLOR_PALETTE[self.current_color_index]
                    self.transparent_mode = data.get("is_transparent", False)
                    self.favorites = data.get("favorites", [])
                    
                    if "user_name" in data:
                        self.user_name = data["user_name"]
                        if self.user_name:
                            self.user_logo = self.user_name[0].upper()
                    else:
                        self.is_first_run = True 
            else:
                self.is_first_run = True 
        except: 
            self.is_first_run = True

    def save_settings(self):
        try:
            data = {
                "last_folder": self.last_folder_path,
                "color_index": self.current_color_index,
                "is_transparent": self.transparent_mode,
                "favorites": self.favorites,
                "user_name": self.user_name 
            }
            with open(self.settings_file, "w") as f:
                json.dump(data, f)
        except: pass

    def activate_drag_shield(self):
        self.drag_lock_timer = time.time()

    def clean_song_title(self, filename):
        name = os.path.splitext(filename)[0]
        name = re.sub(r"\[.*?\]", "", name)
        return name.strip()

    def setup_ui(self):
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True)

        self.main_frame = ctk.CTkFrame(self.container, width=self.compact_width, height=self.win_height, 
                                       corner_radius=30, fg_color=self.SOLID_BG, bg_color=self.TRANS_KEY)
        self.main_frame.pack(side="left", fill="y")
        self.main_frame.pack_propagate(False)

        self.grip_bar = ctk.CTkFrame(self.main_frame, height=20, fg_color="transparent")
        self.grip_bar.pack(fill="x", padx=40, pady=(15, 0))
        self.grip_indicator = ctk.CTkFrame(self.grip_bar, height=6, width=180, corner_radius=3, fg_color="#333333")
        self.grip_indicator.pack()

        self.navbar = ctk.CTkFrame(self.main_frame, fg_color="transparent", height=35)
        self.navbar.pack(fill="x", padx=10, pady=(10, 0))
        
        btn_style = {"width": 30, "height": 30, "fg_color": "transparent", "hover_color": "#222", "font": self.font_icon, "text_color": self.ACCENT_COLOR}
        
        self.btn_folder = ctk.CTkButton(self.navbar, text="📂", command=lambda: [self.activate_drag_shield(), self.load_folder()], **btn_style)
        self.btn_folder.pack(side="left")
        
        self.btn_opacity = ctk.CTkButton(self.navbar, text="💧", command=lambda: [self.activate_drag_shield(), self.toggle_ghost_mode()], **btn_style)
        self.btn_opacity.pack(side="left", padx=2)
        
        self.btn_theme = ctk.CTkButton(self.navbar, text="🎨", command=lambda: [self.activate_drag_shield(), self.cycle_theme_color()], **btn_style)
        self.btn_theme.pack(side="left", padx=2)
        
        self.btn_logo = ctk.CTkButton(self.navbar, text=self.user_logo, font=self.font_mini_logo,
                                      command=lambda: [self.activate_drag_shield(), self.open_name_input_dialog()], 
                                      width=30, height=30, fg_color="transparent", hover_color="#222", text_color=self.ACCENT_COLOR)
        self.btn_logo.pack(side="left", padx=2)

        self.btn_close = ctk.CTkButton(self.navbar, text="✕", width=30, height=30, fg_color="transparent", hover_color="#c0392b", text_color="#e74c3c", font=self.font_icon, command=self.safe_destroy)
        self.btn_close.pack(side="right")
        self.btn_min = ctk.CTkButton(self.navbar, text="—", command=lambda: [self.activate_drag_shield(), self.minimize_app()], **btn_style)
        self.btn_min.pack(side="right", padx=2)

        self.btn_list = ctk.CTkButton(self.main_frame, text="»", width=30, height=30, 
                                      fg_color="transparent", hover_color="#222", 
                                      font=self.font_icon_symbol, text_color=self.ACCENT_COLOR,
                                      command=lambda: [self.activate_drag_shield(), self.toggle_playlist_view()])
        self.btn_list.place(x=300, y=65) 

        self.btn_fav_main = ctk.CTkButton(self.main_frame, text="♥", width=30, height=30,
                                          font=("Arial", 22), 
                                          fg_color="transparent", hover_color="#222", text_color=self.ACCENT_COLOR,
                                          command=self.toggle_favorite_current)
        self.btn_fav_main.place(x=300, y=115) 
        
        self.volume_bar = ctk.CTkProgressBar(self.main_frame, orientation="vertical", width=11, height=130, fg_color="#333", progress_color=self.ACCENT_COLOR, corner_radius=6) 
        self.volume_bar.set(self.current_volume)
        self.volume_bar.place(x=20, y=115)
        self.volume_bar.bind("<Button-1>", self.update_volume_from_bar)
        self.volume_bar.bind("<B1-Motion>", self.update_volume_from_bar)

        self.btn_mute = ctk.CTkButton(self.main_frame, text="🔊", width=25, height=25,
                                      fg_color="transparent", hover_color="#222",
                                      font=("Segoe UI Symbol", 18), text_color=self.ACCENT_COLOR,
                                      command=self.toggle_mute)
        self.btn_mute.place(x=13, y=250)

        self.art_frame = ctk.CTkFrame(self.main_frame, width=170, height=170, corner_radius=85, fg_color="transparent", border_width=0, border_color=self.ACCENT_COLOR) 
        self.art_frame.pack(pady=(40, 20)) 
        
        self.lbl_art = ctk.CTkLabel(self.art_frame, text=f" {self.user_logo} ", font=self.font_main_art, text_color=self.ACCENT_COLOR)
        self.lbl_art.place(relx=0.5, rely=0.5, anchor="center")

        self.content_group = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.content_group.pack(fill="both", expand=True)
        self.lbl_song = ctk.CTkLabel(self.content_group, text="Müzik Seçilmedi", font=self.font_title, text_color=self.ACCENT_COLOR, wraplength=280)
        self.lbl_song.pack(pady=(0, 5))

        self.progress_frame = ctk.CTkFrame(self.content_group, fg_color="transparent")
        self.progress_frame.pack(fill="x", padx=20, pady=(20, 5))
        self.lbl_current_time = ctk.CTkLabel(self.progress_frame, text="0:00", font=("Arial", 10), text_color=self.ACCENT_COLOR)
        self.lbl_current_time.pack(side="left")
        self.lbl_total_time = ctk.CTkLabel(self.progress_frame, text="0:00", font=("Arial", 10), text_color=self.ACCENT_COLOR)
        self.lbl_total_time.pack(side="right")
        self.slider_progress = ctk.CTkSlider(self.content_group, from_=0, to=100, height=10, fg_color="#333", progress_color=self.ACCENT_COLOR, button_color=self.ACCENT_COLOR, button_hover_color="#555", command=self.on_slider_drag)
        self.slider_progress.set(0)
        self.slider_progress.pack(fill="x", padx=20, pady=(0, 10))
        self.slider_progress.bind("<ButtonRelease-1>", self.on_slider_release)

        self.controls_frame = ctk.CTkFrame(self.content_group, fg_color="transparent")
        self.controls_frame.pack(pady=(10, 5), fill="x", padx=15)
        self.controls_frame.grid_columnconfigure((0,1,2,3,4), weight=1)
        
        ctrl_style = {"fg_color": "transparent", "hover_color": "#222", "text_color": self.ACCENT_COLOR}
        self.btn_shuffle = ctk.CTkButton(self.controls_frame, text="🔀", width=30, font=self.font_ctrl_icon, command=self.toggle_shuffle, **ctrl_style)
        self.btn_shuffle.grid(row=0, column=0)
        self.btn_prev = ctk.CTkButton(self.controls_frame, text="⏮", width=40, font=self.font_ctrl_icon, command=self.prev_song, **ctrl_style)
        self.btn_prev.grid(row=0, column=1)
        self.btn_play = ctk.CTkButton(self.controls_frame, text="▶", width=70, height=70, fg_color="transparent", hover_color="#222", text_color=self.ACCENT_COLOR, font=self.font_play_icon, command=self.play_pause)
        self.btn_play.grid(row=0, column=2)
        self.btn_next = ctk.CTkButton(self.controls_frame, text="⏭", width=40, font=self.font_ctrl_icon, command=self.next_song, **ctrl_style)
        self.btn_next.grid(row=0, column=3)
        self.btn_loop = ctk.CTkButton(self.controls_frame, text="🔁", width=30, font=self.font_ctrl_icon, command=self.toggle_loop, **ctrl_style)
        self.btn_loop.grid(row=0, column=4)

        self.bottom_grip_frame = ctk.CTkFrame(self.main_frame, height=20, fg_color="transparent")
        self.bottom_grip_frame.pack(side="bottom", fill="x", padx=40, pady=(0, 5))
        self.bottom_indicator = ctk.CTkFrame(self.bottom_grip_frame, height=6, width=180, corner_radius=3, fg_color="#333333")
        self.bottom_indicator.pack()
        
        self.lbl_artist = ctk.CTkLabel(self.main_frame, text=f"{self.user_name}'s Music Player", font=self.font_signature, text_color=self.ACCENT_COLOR)
        self.lbl_artist.pack(side="bottom", pady=(0, 5))

        self.playlist_container = ctk.CTkFrame(self.container, corner_radius=20, fg_color=self.SOLID_BG)
        
        self.lbl_info_header = ctk.CTkLabel(self.playlist_container, text="", font=("Arial", 11), text_color="gray")
        self.lbl_info_header.pack(pady=(15, 0)) 

        self.tab_header = ctk.CTkFrame(self.playlist_container, height=40, fg_color="transparent")
        self.tab_header.pack(fill="x", padx=10, pady=(2, 5)) 
        
        self.btn_tab_all = ctk.CTkButton(self.tab_header, text="❖", width=60, height=30, 
                                         font=("Segoe UI Symbol", 24), fg_color="transparent", text_color=self.ACCENT_COLOR, hover_color="#222",
                                         command=lambda: self.switch_view_mode("ALL"))
        self.btn_tab_all.pack(side="left", padx=5, expand=True, fill="x")
        
        self.btn_tab_fav = ctk.CTkButton(self.tab_header, text="★", width=60, height=30, 
                                         font=("Segoe UI Symbol", 24), fg_color="transparent", text_color="gray", hover_color="#222",
                                         command=lambda: self.switch_view_mode("FAV"))
        self.btn_tab_fav.pack(side="left", padx=5, expand=True, fill="x")

        self.search_frame = ctk.CTkFrame(self.playlist_container, height=30, fg_color="#222222", corner_radius=15, border_width=0)
        self.search_frame.pack(fill="x", padx=20, pady=(5, 5))
        
        self.lbl_search_icon = ctk.CTkLabel(self.search_frame, text="🔍", font=("Segoe UI Symbol", 12), text_color="gray")
        self.lbl_search_icon.pack(side="left", padx=(10, 2))
        
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.on_search_change)
        self.entry_search = ctk.CTkEntry(self.search_frame, placeholder_text="Ara...", 
                                         height=28, border_width=0, fg_color="transparent", text_color="white", font=("Segoe UI", 12),
                                         textvariable=self.search_var)
        self.entry_search.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.playlist_scroll = ctk.CTkScrollableFrame(self.playlist_container, fg_color="transparent", 
                                                      scrollbar_button_color="#333", scrollbar_button_hover_color=self.ACCENT_COLOR)
        self.playlist_scroll.pack(fill="both", expand=True, padx=0, pady=(5, 20))

        self.btn_fav_main.lift()

    def open_name_input_dialog(self):
        if hasattr(self, 'name_window') and self.name_window is not None and self.name_window.winfo_exists():
            self.name_window.focus()
            return

        self.name_window = ctk.CTkToplevel(self)
        self.name_window.title("Hoşgeldiniz")
        self.name_window.geometry("320x200")
        self.name_window.resizable(False, False)
        self.name_window.attributes("-topmost", True)
        
        x = self.winfo_x() + (self.winfo_width() // 2) - 160
        y = self.winfo_y() + (self.winfo_height() // 2) - 100
        self.name_window.geometry(f"+{x}+{y}")

        lbl = ctk.CTkLabel(self.name_window, text="Lütfen adınızı girin:", font=("Arial", 14, "bold"))
        lbl.pack(pady=(20, 10))

        self.entry_name = ctk.CTkEntry(self.name_window, width=200, height=40, font=("Arial", 14), justify="center")
        self.entry_name.pack(pady=5)
        
        btn_save = ctk.CTkButton(self.name_window, text="KAYDET VE BAŞLA", fg_color=self.ACCENT_COLOR, text_color="black", hover_color="white",
                                 command=self.save_user_name)
        btn_save.pack(pady=20)
        
        self.name_window.bind('<Return>', lambda e: self.save_user_name())

    def save_user_name(self):
        raw_name = self.entry_name.get().strip()
        if raw_name:
            self.user_name = raw_name.title()
            
            self.user_logo = self.user_name[0].upper()
            
            self.update_identity_visuals()
            self.save_settings()
            self.name_window.destroy()

    def update_identity_visuals(self):
        self.lbl_art.configure(text=f" {self.user_logo} ")
        self.btn_logo.configure(text=self.user_logo)
        self.lbl_artist.configure(text=f"{self.user_name}'s Music Player")
        self.title(f"{self.user_name}'s Music Player")

    def update_info_header(self):
        if self.transparent_mode:
            self.lbl_info_header.configure(
                text="ⓘ Listeyi kaydırmak için şeffaf moddan çıkınız.",
                font=("Arial", 11),
                text_color="gray"
            )
        else:
            total_lib = len(self.original_playlist)
            current_view = len(self.playlist)
            search_text = self.search_var.get().strip()
            
            if search_text:
                self.lbl_info_header.configure(
                    text=f"Sonuç: {current_view} / {total_lib}",
                    font=self.font_info_header,
                    text_color=self.ACCENT_COLOR
                )
            else:
                self.lbl_info_header.configure(
                    text=f"Toplam: {total_lib} Şarkı",
                    font=self.font_info_header,
                    text_color=self.ACCENT_COLOR
                )

    def toggle_mute(self):
        if self.is_muted:
            self.current_volume = self.last_volume
            self.is_muted = False
            self.btn_mute.configure(text="🔊", text_color=self.ACCENT_COLOR)
        else:
            self.last_volume = self.current_volume
            self.current_volume = 0
            self.is_muted = True
            self.btn_mute.configure(text="🔇", text_color="gray")
        
        self.volume_bar.set(self.current_volume)
        try: pygame.mixer.music.set_volume(self.current_volume)
        except: pass

    def switch_view_mode(self, mode):
        self.view_mode = mode
        if mode == "ALL":
            self.btn_tab_all.configure(text_color=self.ACCENT_COLOR)
            self.btn_tab_fav.configure(text_color="gray")
        else:
            self.btn_tab_all.configure(text_color="gray")
            self.btn_tab_fav.configure(text_color=self.ACCENT_COLOR)
        self.filter_and_show_playlist()

    def on_search_change(self, *args):
        self.filter_and_show_playlist()

    def filter_and_show_playlist(self):
        query = self.search_var.get().lower()
        source_list = self.original_playlist if self.view_mode == "ALL" else [s for s in self.original_playlist if s in self.favorites]
        
        if query:
            self.playlist = [s for s in source_list if query in os.path.basename(s).lower()]
        else:
            self.playlist = source_list
            
        self.populate_playlist_ui()
        self.update_info_header()

    def toggle_favorite_current(self):
        if not self.playlist: return
        try:
            current_path = self.playlist[self.current_song_index]
            if current_path in self.favorites:
                self.favorites.remove(current_path)
            else:
                self.favorites.append(current_path)
            self.save_settings()
            self.update_fav_button_visual()
            if self.view_mode == "FAV": self.filter_and_show_playlist()
        except: pass

    def update_fav_button_visual(self):
        if not self.playlist: return
        try:
            current_path = self.playlist[self.current_song_index]
            if current_path in self.favorites:
                self.btn_fav_main.configure(text_color="red")
            else:
                self.btn_fav_main.configure(text_color=self.ACCENT_COLOR)
        except: pass

    def toggle_playlist_view(self):
        self.is_playlist_open = not self.is_playlist_open
        current_x = self.winfo_x()
        current_y = self.winfo_y()

        if self.is_playlist_open:
            self.geometry(f"{self.expanded_width}x{self.win_height}+{current_x}+{current_y}")
            self.playlist_container.pack(side="right", fill="both", expand=True, padx=(10, 20), pady=20)
            self.btn_list.configure(text="«") 
            self.filter_and_show_playlist() 
            self.apply_transparency()
        else:
            self.playlist_container.pack_forget()
            self.geometry(f"{self.compact_width}x{self.win_height}+{current_x}+{current_y}")
            self.btn_list.configure(text="»") 

    def populate_playlist_ui(self):
        for widget in self.playlist_scroll.winfo_children():
            widget.destroy()

        if not self.playlist:
            lbl = ctk.CTkLabel(self.playlist_scroll, text="Liste Boş" if self.view_mode == "ALL" else "Favori Yok", text_color="gray")
            lbl.pack(pady=20)
            self.update_info_header()
            return

        for i, path in enumerate(self.playlist):
            filename = os.path.basename(path)
            clean_name = self.clean_song_title(filename)
            wrapped_name = textwrap.fill(clean_name, width=25) 
            is_playing_this = (i == self.current_song_index)
            btn_color = self.ACCENT_COLOR if is_playing_this else "white"
            font_weight = "bold" if is_playing_this else "normal"
            fav_mark = " ♥" if path in self.favorites else ""
            
            btn = ctk.CTkButton(self.playlist_scroll, text=f"{i+1}. {wrapped_name}{fav_mark}", 
                                anchor="center", fg_color="transparent", height=40,
                                text_color=btn_color,
                                hover_color="#222",
                                font=("Segoe UI", 12, font_weight),
                                command=lambda idx=i: self.play_from_playlist(idx))
            btn.pack(fill="x", padx=0, pady=0)
        
        self.update_info_header()

    def play_from_playlist(self, index):
        self.current_song_index = index
        self.load_song(auto_play=True)
        self.populate_playlist_ui()

    def cycle_theme_color(self):
        self.current_color_index = (self.current_color_index + 1) % len(self.COLOR_PALETTE)
        self.ACCENT_COLOR = self.COLOR_PALETTE[self.current_color_index]
        self.apply_theme_color()
        self.save_settings()

    def apply_theme_color(self):
        c = self.ACCENT_COLOR
        icon_color = c
        
        self.btn_folder.configure(text_color=icon_color)
        self.btn_opacity.configure(text_color=icon_color)
        self.btn_theme.configure(text_color=icon_color)
        self.btn_min.configure(text_color=icon_color)
        self.btn_list.configure(text_color=icon_color)
        self.btn_logo.configure(text_color=icon_color)
        self.lbl_art.configure(text_color=icon_color)
        self.lbl_song.configure(text_color=icon_color)
        self.lbl_artist.configure(text_color=icon_color)
        self.lbl_current_time.configure(text_color=icon_color)
        self.lbl_total_time.configure(text_color=icon_color)
        self.slider_progress.configure(progress_color=icon_color, button_color=icon_color)
        self.volume_bar.configure(progress_color=icon_color)
        self.btn_prev.configure(text_color=icon_color)
        self.btn_next.configure(text_color=icon_color)
        self.btn_play.configure(text_color=icon_color)
        self.btn_shuffle.configure(text_color=icon_color if self.shuffle_mode else "white")
        self.btn_loop.configure(text_color=icon_color if self.loop_mode else "white")
        self.playlist_scroll.configure(scrollbar_button_hover_color=icon_color)
        
        self.playlist_container.configure(border_color=icon_color)
        self.art_frame.configure(border_color=icon_color)

        if not self.is_muted:
            self.btn_mute.configure(text_color=icon_color)
        
        self.update_fav_button_visual()
        if self.view_mode == "ALL":
            self.btn_tab_all.configure(text_color=icon_color)
        else:
            self.btn_tab_fav.configure(text_color=icon_color)
        if self.is_playlist_open: self.populate_playlist_ui()
        
        self.update_info_header()

    def toggle_ghost_mode(self):
        self.transparent_mode = not self.transparent_mode
        self.apply_transparency()
        self.save_settings()

    def apply_transparency(self):
        list_bg = self.TRANS_KEY if self.transparent_mode else self.SOLID_BG
        
        self.update_info_header()

        if self.transparent_mode:
            self.main_frame.configure(fg_color=self.TRANS_KEY)
            self.playlist_container.configure(fg_color=list_bg)
            self.playlist_scroll.configure(fg_color="transparent")
            self.grip_indicator.configure(fg_color="#333")
            self.bottom_indicator.configure(fg_color="#333")
            self.slider_progress.configure(fg_color=self.TRANS_KEY, bg_color=self.TRANS_KEY)
            self.volume_bar.configure(fg_color="#333", bg_color=self.TRANS_KEY)
        else:
            self.main_frame.configure(fg_color=self.SOLID_BG)
            self.playlist_container.configure(fg_color=self.SOLID_BG)
            self.playlist_scroll.configure(fg_color="transparent")
            self.grip_indicator.configure(fg_color="#333333")
            self.bottom_indicator.configure(fg_color="#333333")
            self.slider_progress.configure(fg_color="#333", bg_color=self.SOLID_BG)
            self.volume_bar.configure(fg_color="#333", bg_color=self.SOLID_BG)
            
            self.search_frame.configure(fg_color="#222222")

    def start_move(self, event):
        if time.time() - self.drag_lock_timer < 0.3: return
        self.start_x = self.winfo_pointerx()
        self.start_y = self.winfo_pointery()
        self.win_x = self.winfo_x()
        self.win_y = self.winfo_y()

    def do_move(self, event):
        if time.time() - self.drag_lock_timer < 0.3: return
        x = self.win_x + (self.winfo_pointerx() - self.start_x)
        y = self.win_y + (self.winfo_pointery() - self.start_y)
        self.geometry(f"+{x}+{y}")

    def on_slider_drag(self, value):
        self.is_dragging = True
        mins, secs = divmod(int(value), 60)
        self.lbl_current_time.configure(text=f"{mins}:{secs:02d}")

    def on_slider_release(self, event):
        self.seek_song(self.slider_progress.get())
        self.after(200, lambda: setattr(self, 'is_dragging', False))

    def seek_song(self, value):
        if self.playlist and self.song_length > 0:
            try:
                pygame.mixer.music.play(start=value)
                self.time_offset = value
                self.is_playing = True
                self.btn_play.configure(text="⏸")
            except: pass

    def check_music_progress(self):
        if not self.winfo_exists(): return
        if self.is_playing and not self.is_dragging:
            if not pygame.mixer.music.get_busy():
                self.next_song()
            else:
                try:
                    if pygame.mixer.get_init():
                        real_pos = self.time_offset + (pygame.mixer.music.get_pos() / 1000)
                        if real_pos <= self.song_length + 1:
                            self.slider_progress.set(real_pos)
                            mins, secs = divmod(int(real_pos), 60)
                            self.lbl_current_time.configure(text=f"{mins}:{secs:02d}")
                except: pass
        self.progress_loop_id = self.after(500, self.check_music_progress)

    def load_song(self, auto_play=True):
        if not self.playlist: return
        try:
            path = self.playlist[self.current_song_index]
            filename = os.path.basename(path)
            clean_name = self.clean_song_title(filename)
            self.lbl_song.configure(text=clean_name)
            self.lbl_art.configure(text=f" {self.user_logo} ", text_color=self.ACCENT_COLOR) 
            self.update_fav_button_visual()
            self.time_offset = 0
            self.slider_progress.set(0)
            self.lbl_current_time.configure(text="0:00")
            try:
                audio = MP3(path)
                self.song_length = audio.info.length
                mins, secs = divmod(int(self.song_length), 60)
                self.lbl_total_time.configure(text=f"{mins}:{secs:02d}")
                self.slider_progress.configure(to=self.song_length)
            except:
                self.song_length = 0
                self.lbl_total_time.configure(text="--:--")
            pygame.mixer.music.load(path)
            if auto_play: self.play_music()
            else:
                self.is_playing = False
                self.btn_play.configure(text="▶")
            if self.is_playlist_open: self.populate_playlist_ui()
        except:
            self.lbl_song.configure(text="Hatalı Dosya!")
            self.is_playing = False

    def play_music(self):
        try:
            pygame.mixer.music.play()
            self.time_offset = 0
            self.is_playing = True
            self.btn_play.configure(text="⏸")
        except: pass

    def play_pause(self):
        if not self.playlist: return
        try:
            if self.is_playing:
                pygame.mixer.music.pause()
                self.is_playing = False
                self.btn_play.configure(text="▶")
            else:
                pygame.mixer.music.unpause()
                self.is_playing = True
                self.btn_play.configure(text="⏸")
                if not pygame.mixer.music.get_busy(): self.play_music()
        except: pass

    def next_song(self):
        if not self.playlist: return
        if self.loop_mode: 
            self.load_song(auto_play=True)
            return
        self.current_song_index = (self.current_song_index + 1) % len(self.playlist)
        self.load_song(auto_play=True)

    def prev_song(self):
        if not self.playlist: return
        self.current_song_index = (self.current_song_index - 1) % len(self.playlist)
        self.load_song(auto_play=True)

    def update_volume_from_bar(self, event):
        widget_height = self.volume_bar.winfo_height()
        click_y = event.y
        new_volume = 1.0 - (click_y / widget_height)
        new_volume = max(0.0, min(1.0, new_volume))
        self.current_volume = new_volume
        self.volume_bar.set(self.current_volume)
        try: pygame.mixer.music.set_volume(self.current_volume)
        except: pass
        if self.is_muted:
            self.is_muted = False
            self.btn_mute.configure(text="🔊", text_color=self.ACCENT_COLOR)

    def change_volume_scroll(self, event):
        if event.delta > 0: self.increase_volume()
        else: self.decrease_volume()

    def increase_volume(self, event=None):
        self.current_volume = min(1.0, self.current_volume + 0.05)
        self.volume_bar.set(self.current_volume)
        try: pygame.mixer.music.set_volume(self.current_volume)
        except: pass
        if self.is_muted:
            self.is_muted = False
            self.btn_mute.configure(text="🔊", text_color=self.ACCENT_COLOR)

    def decrease_volume(self, event=None):
        self.current_volume = max(0.0, self.current_volume - 0.05)
        self.volume_bar.set(self.current_volume)
        try: pygame.mixer.music.set_volume(self.current_volume)
        except: pass
        if self.is_muted:
            self.is_muted = False
            self.btn_mute.configure(text="🔊", text_color=self.ACCENT_COLOR)

    def toggle_shuffle(self):
        self.shuffle_mode = True 
        self.btn_shuffle.configure(text_color=self.ACCENT_COLOR)
        
        if not self.playlist: return

        for _ in range(5):
            random.shuffle(self.playlist)
        
        self.current_song_index = 0
        self.load_song(auto_play=False)
        
        if self.is_playlist_open: self.populate_playlist_ui()

    def toggle_loop(self):
        self.loop_mode = not self.loop_mode
        self.btn_loop.configure(text_color=self.ACCENT_COLOR if self.loop_mode else "white")

    def load_folder(self):
        try:
            folder = filedialog.askdirectory()
            if folder:
                self.last_folder_path = folder
                self.save_settings()
                self.process_folder_threaded(folder)
        except: pass

    def process_folder_threaded(self, folder):
        self.lbl_song.configure(text="Klasör Taranıyor...")
        self.btn_play.configure(text="...")
        threading.Thread(target=self._scan_files_thread, args=(folder,), daemon=True).start()

    def _scan_files_thread(self, folder):
        try:
            files = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith('.mp3')]
            if files:
                self.after(0, lambda: self._finish_loading_folder(files))
            else:
                self.after(0, lambda: self.lbl_song.configure(text="MP3 Bulunamadı"))
        except: pass

    def _finish_loading_folder(self, files):
        mixed_list = list(files)
        random.shuffle(mixed_list)
        
        self.original_playlist = list(mixed_list) 
        self.playlist = list(mixed_list)
        
        self.shuffle_mode = True
        self.btn_shuffle.configure(text_color=self.ACCENT_COLOR)
        
        self.current_song_index = 0
        self.load_song(auto_play=False) 
        
        if self.is_playlist_open: self.filter_and_show_playlist()

    def bind_events(self):
        self.bind('<space>', lambda e: self.play_pause())
        self.bind('<Right>', lambda e: self.next_song())
        self.bind('<Left>', lambda e: self.prev_song())
        self.bind('<Up>', self.increase_volume)
        self.bind('<Down>', self.decrease_volume)
        safe_widgets = [self.main_frame, self.grip_bar, self.grip_indicator, self.navbar, self.lbl_art, self.art_frame, self.volume_bar, self.bottom_grip_frame, self.bottom_indicator, self.btn_list, self.btn_fav_main, self.lbl_artist]
        for widget in safe_widgets:
            try:
                widget.bind("<ButtonPress-1>", self.start_move)
                widget.bind("<B1-Motion>", self.do_move)
                widget.bind('<MouseWheel>', self.change_volume_scroll)
            except: pass
        self.protocol("WM_DELETE_WINDOW", self.safe_destroy)

    def safe_destroy(self):
        try:
            self.save_settings()
            if self.progress_loop_id: self.after_cancel(self.progress_loop_id)
            pygame.mixer.music.stop()
            pygame.mixer.quit()
        except: pass
        self.quit()

    def minimize_app(self):
        self.overrideredirect(False)
        self.iconify()
        self.bind("<Map>", self.restore_frame)
    
    def restore_frame(self, e):
        if self.state() == "normal":
            self.overrideredirect(True)
            self.unbind("<Map>")

if __name__ == "__main__":
    app = MusicPlayer()
    app.mainloop()
