import os
import sys
import json
import time
import math
import shutil
import threading
import subprocess
import ctypes
import webbrowser
import tempfile
from urllib.parse import urlsplit
from datetime import datetime
from tkinter import filedialog, messagebox, ttk
import tkinter as tk

import customtkinter as ctk
import requests
from PIL import Image, ImageDraw, ImageTk

try:
    import pystray
    PYSTRAY_AVAILABLE = True
except Exception:
    PYSTRAY_AVAILABLE = False


APP_TITLE = "VEXPER SISTEMAS"
CONFIG_FILE = "config.json"
MAX_TABLE_ROWS = 300
WINDOWS_APP_ID = "vexper.sistemas.syncagent"
APP_VERSION = "1.0.19"
AUTO_UPDATE_ON_START = True
FIXED_API_BASE_URL = "https://sync-fiscal-hub.base44.app/api/functions"
DEFAULT_UPDATE_MANIFEST_URL = "https://github.com/richardcris/-portal_sync_agent/releases/latest/download/manifest.json"
ENABLE_CONSOLE_LOG = False
ENABLE_SIDEBAR_LOGO_ANIMATION = True
LOGO_ANIMATION_INTERVAL_MS = 60
WINDOW_MOVE_PAUSE_SECONDS = 0.35
APP_CHANGELOG = [
    "Ajustes de interface e estabilidade.",
    "Melhorias no painel de sincronização.",
    "Correções gerais de desempenho.",
]


def resource_path(relative_path: str) -> str:
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def app_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(".")


def normalize_bool(value, default=False):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "sim", "yes", "on")
    return default


def normalize_version(version_text):
    version_text = str(version_text or "").strip()
    if version_text.lower().startswith("v"):
        version_text = version_text[1:]

    parts = []
    for chunk in version_text.split("."):
        number = "".join(ch for ch in chunk if ch.isdigit())
        if number:
            parts.append(int(number))
        else:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def format_cnpj(value):
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    if len(digits) != 14:
        return value or "-"
    return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"


def extract_update_info(payload):
    if isinstance(payload, list) and payload:
        payload = payload[0]

    if not isinstance(payload, dict):
        return "", "", "", ""

    source = payload.get("data") if isinstance(payload.get("data"), dict) else payload

    latest_version = str(
        source.get("latest_version")
        or source.get("version")
        or source.get("tag_name")
        or source.get("app_version")
        or ""
    ).strip()

    download_url = str(
        source.get("download_url")
        or source.get("url")
        or source.get("html_url")
        or source.get("installer_url")
        or ""
    ).strip()

    notes = str(
        source.get("notes")
        or source.get("changelog")
        or source.get("body")
        or ""
    ).strip()

    setup_sha256 = str(
        source.get("setup_sha256")
        or source.get("sha256")
        or source.get("installer_sha256")
        or ""
    ).strip().lower()

    return latest_version, download_url, notes, setup_sha256


def get_runtime_build_id():
    try:
        target = sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__)
        build_timestamp = os.path.getmtime(target)
        return datetime.fromtimestamp(build_timestamp).strftime("%Y%m%d%H%M")
    except Exception:
        return datetime.now().strftime("%Y%m%d%H%M")


def get_user_update_dir():
    base_dir = os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()
    update_dir = os.path.join(base_dir, "VEXPER-SISTEMAS", "updates")
    os.makedirs(update_dir, exist_ok=True)
    return update_dir


def get_user_config_dir():
    base_dir = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()
    config_dir = os.path.join(base_dir, "VEXPER-SISTEMAS")
    os.makedirs(config_dir, exist_ok=True)
    return config_dir


def get_primary_config_path():
    return os.path.join(get_user_config_dir(), CONFIG_FILE)


def get_legacy_config_path():
    return os.path.join(app_dir(), CONFIG_FILE)


def get_config_read_path():
    primary = get_primary_config_path()
    if os.path.exists(primary):
        return primary

    legacy = get_legacy_config_path()
    if os.path.exists(legacy):
        return legacy

    return primary


def show_startup_splash(duration_ms=2900):
    splash = tk.Tk()
    splash.title(APP_TITLE)
    splash.overrideredirect(True)
    splash.configure(bg="#0B0F15")
    splash.attributes("-topmost", True)

    width, height = 520, 320
    screen_w = splash.winfo_screenwidth()
    screen_h = splash.winfo_screenheight()
    x = int((screen_w - width) / 2)
    y = int((screen_h - height) / 2)
    splash.geometry(f"{width}x{height}+{x}+{y}")

    container = tk.Frame(splash, bg="#0B0F15")
    container.pack(expand=True, fill="both", padx=24, pady=24)

    logo_label = tk.Label(container, bg="#0B0F15")
    logo_label.pack(pady=(10, 10))

    logo_candidates = [
        resource_path("logo.png"),
        resource_path("logo.jpg"),
        resource_path("logo.jpeg"),
        resource_path("1.png"),
    ]

    for logo_path in logo_candidates:
        try:
            if os.path.exists(logo_path):
                logo_image = Image.open(logo_path).convert("RGBA")
                logo_image.thumbnail((220, 140), Image.Resampling.LANCZOS)
                splash.logo_photo = ImageTk.PhotoImage(logo_image)
                logo_label.configure(image=splash.logo_photo)
                break
        except Exception:
            pass

    if not getattr(splash, "logo_photo", None):
        logo_label.configure(text="VX", fg="#E6EDF3", bg="#0B0F15", font=("Segoe UI", 44, "bold"))

    title = tk.Label(
        container,
        text="VEXPER SISTEMAS",
        fg="#E6EDF3",
        bg="#0B0F15",
        font=("Segoe UI", 24, "bold")
    )
    title.pack()

    subtitle = tk.Label(
        container,
        text="Carregando Sync Agent...",
        fg="#8B949E",
        bg="#0B0F15",
        font=("Segoe UI", 11)
    )
    subtitle.pack(pady=(4, 16))

    progress = ttk.Progressbar(container, mode="indeterminate", length=340)
    progress.pack(pady=(0, 6))
    progress.start(12)

    splash.after(duration_ms, splash.destroy)
    splash.mainloop()


class SyncAgentApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.runtime_build_id = get_runtime_build_id()
        self.runtime_version_label = f"{APP_VERSION} ({self.runtime_build_id})"
        self.last_seen_build_id = ""
        self.last_applied_setup_sha256 = ""
        self.last_applied_version = ""
        self.auto_update_enabled = AUTO_UPDATE_ON_START
        self.update_progress_window = None
        self.update_progress_label = None
        self.update_progress_bar = None
        self.update_progress_percent = None
        self._ui_motion_suspend_until = 0.0
        self._log_buffer = []
        self._log_flush_scheduled = False
        self._animated_buttons = []
        self._animated_button_frames = {}
        self._animated_button_index = 0
        self._hero_glow_phase = 0.0
        self._hero_glow_strip = None
        self._hero_status_pill = None
        self._hero_status_value = None
        self._button_font = ctk.CTkFont(family="Bahnschrift SemiBold", size=13)
        self._title_font = ctk.CTkFont(family="Bahnschrift SemiBold", size=30)
        self._section_font = ctk.CTkFont(family="Bahnschrift SemiBold", size=18)
        self._micro_font = ctk.CTkFont(family="Consolas", size=11)

        self.try_set_app_user_model_id()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title(APP_TITLE)
        self.geometry("1350x900")
        self.minsize(1120, 760)

        self.running = False
        self.monitor_thread = None
        self.tray_icon = None
        self.tray_thread = None
        self.processed_files = set()
        self.stop_event = threading.Event()

        self.success_count = 0
        self.error_count = 0
        self.total_processed = 0
        self.scan_total = 0
        self.scan_done = 0

        self.bg_main = "#050B14"
        self.bg_panel = "#091322"
        self.bg_card = "#0B1728"
        self.bg_card_2 = "#112238"
        self.bg_card_3 = "#162C46"
        self.accent = "#2DE2E6"
        self.accent_hover = "#1CC6D8"
        self.accent_alt = "#70FFB8"
        self.text_main = "#EAF7FF"
        self.text_soft = "#8BA8C7"
        self.text_dim = "#58738F"
        self.border = "#17324B"
        self.border_soft = "#214A6B"
        self.success_color = "#16C47F"
        self.error_color = "#FF5D73"
        self.warning_color = "#FFC857"
        self.hero_glow = "#123C63"
        self.hero_line = "#1B5D8F"
        self.input_bg = "#08111D"

        self.configure(fg_color=self.bg_main)

        self.try_set_window_icon()

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.create_ui()
        if ENABLE_SIDEBAR_LOGO_ANIMATION:
            self.bind("<Configure>", self._on_window_configure)
        self.after(150, self.try_set_window_icon)
        self.load_config()
        self.update_company_status()
        self.update_stats_labels()
        self.after(350, self.show_startup_update_notice_if_needed)
        self.after(2200, self.check_for_updates_automatically)

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_tech_icon_frames(self, kind, color, size=26, frame_count=12):
        frames = []
        rgba = tuple(int(color.lstrip("#")[idx:idx + 2], 16) for idx in (0, 2, 4))
        canvas_size = size * 3
        center = canvas_size / 2
        radius = size * 0.88

        for frame_idx in range(frame_count):
            img = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            phase = (frame_idx / frame_count) * math.tau

            if kind == "save":
                pulse = 0.45 + 0.55 * math.sin(phase)
                draw.rounded_rectangle(
                    (center - radius * 0.95, center - radius * 0.95, center + radius * 0.95, center + radius * 0.95),
                    radius=int(size * 0.36),
                    outline=rgba + (190,),
                    width=4,
                )
                draw.rounded_rectangle(
                    (center - radius * 0.55, center - radius * 0.7, center + radius * 0.55, center + radius * 0.18),
                    radius=int(size * 0.12),
                    fill=rgba + (int(70 + 70 * pulse),),
                )
                draw.rectangle(
                    (center - radius * 0.4, center + radius * 0.1, center + radius * 0.4, center + radius * 0.56),
                    fill=rgba + (210,),
                )
            elif kind == "network":
                orbit = radius * 0.28
                for offset in (0, math.tau / 3, 2 * math.tau / 3):
                    x = center + math.cos(phase + offset) * orbit
                    y = center + math.sin(phase + offset) * orbit
                    draw.line((center, center, x, y), fill=rgba + (135,), width=3)
                    draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=rgba + (220,))
                draw.ellipse((center - 6, center - 6, center + 6, center + 6), fill=rgba + (255,))
            elif kind == "play":
                glow = 0.45 + 0.55 * math.sin(phase)
                draw.ellipse(
                    (center - radius, center - radius, center + radius, center + radius),
                    outline=rgba + (int(80 + 90 * glow),),
                    width=4,
                )
                draw.polygon(
                    [
                        (center - radius * 0.28, center - radius * 0.42),
                        (center - radius * 0.28, center + radius * 0.42),
                        (center + radius * 0.46, center),
                    ],
                    fill=rgba + (255,),
                )
            elif kind == "stop":
                pulse = 0.5 + 0.5 * math.sin(phase)
                draw.rounded_rectangle(
                    (center - radius, center - radius, center + radius, center + radius),
                    radius=int(size * 0.4),
                    outline=rgba + (int(90 + 70 * pulse),),
                    width=4,
                )
                draw.rounded_rectangle(
                    (center - radius * 0.45, center - radius * 0.45, center + radius * 0.45, center + radius * 0.45),
                    radius=int(size * 0.22),
                    fill=rgba + (230,),
                )
            elif kind == "scan":
                sweep = (frame_idx / frame_count) * radius * 1.6
                draw.rounded_rectangle(
                    (center - radius, center - radius * 0.75, center + radius, center + radius * 0.75),
                    radius=int(size * 0.28),
                    outline=rgba + (180,),
                    width=4,
                )
                draw.rectangle(
                    (center - radius + sweep - 10, center - radius * 0.75, center - radius + sweep + 10, center + radius * 0.75),
                    fill=rgba + (80,),
                )
                draw.line((center - radius * 0.75, center, center + radius * 0.75, center), fill=rgba + (220,), width=3)
            elif kind == "update":
                angle = phase
                draw.arc(
                    (center - radius, center - radius, center + radius, center + radius),
                    start=30,
                    end=280,
                    fill=rgba + (215,),
                    width=4,
                )
                tip_x = center + math.cos(angle - math.pi / 5) * radius
                tip_y = center + math.sin(angle - math.pi / 5) * radius
                draw.polygon(
                    [
                        (tip_x, tip_y),
                        (tip_x - 10, tip_y - 4),
                        (tip_x - 3, tip_y + 8),
                    ],
                    fill=rgba + (255,),
                )

            cropped = img.resize((size, size), Image.Resampling.LANCZOS)
            frames.append(ctk.CTkImage(light_image=cropped, dark_image=cropped, size=(size, size)))
        return frames

    def register_animated_button(self, button, kind, color):
        key = (kind, color)
        if key not in self._animated_button_frames:
            self._animated_button_frames[key] = self.create_tech_icon_frames(kind, color)
        frames = self._animated_button_frames[key]
        button.configure(image=frames[0], compound="left", anchor="w", font=self._button_font)
        self._animated_buttons.append((button, frames))

    def animate_button_icons(self):
        if not self.winfo_exists() or not self._animated_buttons:
            return
        self._animated_button_index = (self._animated_button_index + 1) % 12
        frame_index = self._animated_button_index
        for button, frames in self._animated_buttons:
            try:
                if button.winfo_exists():
                    button.configure(image=frames[frame_index % len(frames)])
            except Exception:
                pass
        self.after(88, self.animate_button_icons)

    def animate_hero_glow(self):
        if not self.winfo_exists() or not self._hero_glow_strip:
            return
        wave = 0.5 + 0.5 * math.sin(self._hero_glow_phase)
        r = int(18 + (52 - 18) * wave)
        g = int(60 + (242 - 60) * wave)
        b = int(99 + (230 - 99) * wave)
        color = f"#{r:02x}{g:02x}{b:02x}"
        try:
            if self._hero_glow_strip.winfo_exists():
                self._hero_glow_strip.configure(fg_color=color)
            if self._hero_status_pill and self._hero_status_pill.winfo_exists():
                self._hero_status_pill.configure(border_color=color)
            if self._hero_status_value and self._hero_status_value.winfo_exists():
                self._hero_status_value.configure(text_color=color)
        except Exception:
            return
        self._hero_glow_phase += 0.08
        self.after(90, self.animate_hero_glow)

    # ---------------------------
    # UI
    # ---------------------------
    def try_set_app_user_model_id(self):
        if os.name != "nt":
            return
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(WINDOWS_APP_ID)
        except Exception:
            pass

    def try_set_window_icon(self):
        ico_candidates = [
            resource_path("icon.ico"),
            resource_path("icon"),
        ]
        icon_set = False
        for ico_path in ico_candidates:
            try:
                if os.path.exists(ico_path):
                    self.iconbitmap(default=ico_path)
                    ico_image = Image.open(ico_path).convert("RGBA")
                    self._window_icon_photo = ImageTk.PhotoImage(ico_image)
                    self.iconphoto(True, self._window_icon_photo)
                    icon_set = True
                    break
            except Exception:
                pass

        if icon_set:
            return

        # Fallback for environments where iconbitmap is ignored.
        png_candidates = [
            resource_path("icon.png"),
            resource_path("logo.png"),
            resource_path("1.png"),
        ]
        for png_path in png_candidates:
            try:
                if os.path.exists(png_path):
                    icon_image = Image.open(png_path).convert("RGBA")
                    self._window_icon_photo = ImageTk.PhotoImage(icon_image)
                    self.iconphoto(True, self._window_icon_photo)
                    return
            except Exception:
                pass

    def create_ui(self):
        self.main_frame = ctk.CTkFrame(self, fg_color=self.bg_main, corner_radius=0)
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=0)
        self.main_frame.grid_columnconfigure(1, weight=1)

        self.create_sidebar()
        self.create_content_area()

    def create_sidebar(self):
        self.sidebar = ctk.CTkFrame(
            self.main_frame,
            width=300,
            fg_color=self.bg_panel,
            corner_radius=0,
            border_width=1,
            border_color=self.border
        )
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.sidebar.grid_propagate(False)

        self.sidebar_scroll = ctk.CTkScrollableFrame(
            self.sidebar,
            fg_color="transparent",
            corner_radius=0,
            width=276
        )
        self.sidebar_scroll.pack(fill="both", expand=True)

        self.logo_wrap = ctk.CTkFrame(
            self.sidebar_scroll,
            fg_color=self.bg_card,
            corner_radius=24,
            border_width=1,
            border_color=self.border_soft,
        )
        self.logo_wrap.pack(fill="x", padx=18, pady=(20, 14))

        self._logo_glow_phase = 0.0
        self._logo_anim_frame = None
        self.logo_label = None
        self.load_logo()

        self.app_name = ctk.CTkLabel(
            self.logo_wrap,
            text="VEXPER SISTEMAS",
            font=ctk.CTkFont(family="Bahnschrift SemiBold", size=25),
            text_color=self.text_main
        )
        self.app_name.pack(anchor="center", pady=(0, 2))

        self.app_subtitle = ctk.CTkLabel(
            self.logo_wrap,
            text="SYNC CORE . FISCAL NODE",
            font=self._micro_font,
            text_color=self.text_soft
        )
        self.app_subtitle.pack(anchor="center")

        self.app_chip = ctk.CTkLabel(
            self.logo_wrap,
            text="LIVE MONITORING INTERFACE",
            font=self._micro_font,
            text_color=self.accent_alt,
            fg_color=self.bg_card_2,
            corner_radius=999,
            padx=12,
            pady=6,
        )
        self.app_chip.pack(anchor="center", pady=(12, 18))

        self.separator1 = ctk.CTkFrame(self.sidebar_scroll, height=1, fg_color=self.border)
        self.separator1.pack(fill="x", padx=18, pady=14)

        self.menu_title = ctk.CTkLabel(
            self.sidebar_scroll,
            text="CENTRO DE CONTROLE",
            font=self._micro_font,
            text_color=self.accent_alt
        )
        self.menu_title.pack(anchor="w", padx=18, pady=(0, 10))

        self.status_card = ctk.CTkFrame(
            self.sidebar_scroll,
            fg_color=self.bg_card,
            corner_radius=22,
            border_width=1,
            border_color=self.border_soft
        )
        self.status_card.pack(fill="x", padx=18, pady=(0, 12))

        self.status_label_title = ctk.CTkLabel(
            self.status_card,
            text="Status do Núcleo",
            font=ctk.CTkFont(family="Bahnschrift SemiBold", size=15),
            text_color=self.text_main
        )
        self.status_label_title.pack(anchor="w", padx=14, pady=(14, 6))

        self.status_label = ctk.CTkLabel(
            self.status_card,
            text="Pronto",
            font=ctk.CTkFont(family="Bahnschrift SemiBold", size=22),
            text_color=self.accent
        )
        self.status_label.pack(anchor="w", padx=14, pady=(0, 6))

        self.company_name_status_label = ctk.CTkLabel(
            self.status_card,
            text="Empresa: -",
            font=ctk.CTkFont(size=12),
            text_color=self.text_soft
        )
        self.company_name_status_label.pack(anchor="w", padx=14, pady=(0, 2))

        self.company_cnpj_status_label = ctk.CTkLabel(
            self.status_card,
            text="CNPJ: -",
            font=ctk.CTkFont(size=12),
            text_color=self.text_soft
        )
        self.company_cnpj_status_label.pack(anchor="w", padx=14, pady=(0, 2))

        self.company_id_status_label = ctk.CTkLabel(
            self.status_card,
            text="Empresa ID: -",
            font=ctk.CTkFont(size=12),
            text_color=self.text_soft
        )
        self.company_id_status_label.pack(anchor="w", padx=14, pady=(0, 14))

        self.stats_card = ctk.CTkFrame(
            self.sidebar,
            fg_color=self.bg_card,
            corner_radius=22,
            border_width=1,
            border_color=self.border_soft
        )
        self.stats_card.pack(fill="x", padx=18, pady=(0, 12))

        self.stats_title = ctk.CTkLabel(
            self.stats_card,
            text="Telemetria",
            font=ctk.CTkFont(family="Bahnschrift SemiBold", size=15),
            text_color=self.text_main
        )
        self.stats_title.pack(anchor="w", padx=14, pady=(14, 8))

        self.total_label = ctk.CTkLabel(self.stats_card, text="Total processados: 0", text_color=self.text_soft)
        self.total_label.pack(anchor="w", padx=14, pady=3)

        self.success_label = ctk.CTkLabel(self.stats_card, text="Sucesso: 0", text_color=self.success_color)
        self.success_label.pack(anchor="w", padx=14, pady=3)

        self.error_label = ctk.CTkLabel(self.stats_card, text="Erros: 0", text_color=self.error_color)
        self.error_label.pack(anchor="w", padx=14, pady=(3, 14))

        self.actions_title = ctk.CTkLabel(
            self.sidebar_scroll,
            text="AÇÕES ORQUESTRADAS",
            font=self._micro_font,
            text_color=self.accent_alt
        )
        self.actions_title.pack(anchor="w", padx=18, pady=(6, 10))

        self.sidebar_save = ctk.CTkButton(
            self.sidebar_scroll, text="Salvar Configuração", command=self.save_config,
            fg_color=self.bg_card_2, hover_color=self.bg_card_3, height=48,
            corner_radius=18, border_width=1, border_color=self.border_soft,
            text_color=self.text_main
        )
        self.sidebar_save.pack(fill="x", padx=18, pady=6)

        self.sidebar_test = ctk.CTkButton(
            self.sidebar_scroll, text="Testar Conexão", command=self.test_upload,
            fg_color=self.bg_card_2, hover_color=self.bg_card_3, height=48,
            corner_radius=18, border_width=1, border_color=self.border_soft,
            text_color=self.text_main
        )
        self.sidebar_test.pack(fill="x", padx=18, pady=6)

        self.sidebar_start = ctk.CTkButton(
            self.sidebar_scroll, text="Iniciar Monitoramento", command=self.start_monitoring,
            fg_color=self.bg_card_2, hover_color=self.bg_card_3, height=48,
            corner_radius=18, border_width=1, border_color=self.border_soft,
            text_color=self.text_main
        )
        self.sidebar_start.pack(fill="x", padx=18, pady=6)

        self.sidebar_stop = ctk.CTkButton(
            self.sidebar_scroll, text="Parar Monitoramento", command=self.stop_monitoring,
            fg_color=self.bg_card_2, hover_color=self.bg_card_3, height=48,
            corner_radius=18, border_width=1, border_color=self.border_soft,
            text_color=self.text_main
        )
        self.sidebar_stop.pack(fill="x", padx=18, pady=6)

        self.sidebar_existing = ctk.CTkButton(
            self.sidebar_scroll, text="Processar Existentes", command=self.process_existing_files,
            fg_color=self.bg_card_2, hover_color=self.bg_card_3, height=48,
            corner_radius=18, border_width=1, border_color=self.border_soft,
            text_color=self.text_main
        )
        self.sidebar_existing.pack(fill="x", padx=18, pady=6)

        self.sidebar_update = ctk.CTkButton(
            self.sidebar_scroll, text="Verificar Atualização", command=self.check_for_updates,
            fg_color=self.bg_card_2, hover_color=self.bg_card_3, height=48,
            corner_radius=18, border_width=1, border_color=self.border_soft,
            text_color=self.text_main
        )
        self.sidebar_update.pack(fill="x", padx=18, pady=6)

        self.register_animated_button(self.sidebar_save, "save", self.accent)
        self.register_animated_button(self.sidebar_test, "network", self.warning_color)
        self.register_animated_button(self.sidebar_start, "play", self.success_color)
        self.register_animated_button(self.sidebar_stop, "stop", self.error_color)
        self.register_animated_button(self.sidebar_existing, "scan", self.accent_alt)
        self.register_animated_button(self.sidebar_update, "update", self.accent)

        self.separator2 = ctk.CTkFrame(self.sidebar_scroll, height=1, fg_color=self.border)
        self.separator2.pack(fill="x", padx=18, pady=14)

        self.footer_label = ctk.CTkLabel(
            self.sidebar_scroll,
            text="VEXPER SYSTEMS . TECH INTERFACE",
            text_color=self.text_dim,
            font=self._micro_font
        )
        self.footer_label.pack(anchor="w", padx=18, pady=(0, 18))

    def create_content_area(self):
        self.content = ctk.CTkFrame(self.main_frame, fg_color=self.bg_main, corner_radius=0)
        self.content.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(0, 0), pady=0)
        self.content.grid_rowconfigure(1, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        self.top_header = ctk.CTkFrame(
            self.content,
            fg_color=self.bg_main,
            corner_radius=0
        )
        self.top_header.grid(row=0, column=0, sticky="ew", padx=24, pady=(18, 12))
        self.top_header.grid_columnconfigure(0, weight=1)

        self.header_title = ctk.CTkLabel(
            self.top_header,
            text="Fiscal Sync Command",
            font=self._title_font,
            text_color=self.text_main
        )
        self.header_title.grid(row=0, column=0, sticky="w")

        self.header_subtitle = ctk.CTkLabel(
            self.top_header,
            text="Uma cabine operacional para varredura XML, upload automático e leitura de telemetria em tempo real.",
            font=ctk.CTkFont(family="Bahnschrift", size=14),
            text_color=self.text_soft
        )
        self.header_subtitle.grid(row=1, column=0, sticky="w", pady=(4, 0))

        self.scroll_frame = ctk.CTkScrollableFrame(
            self.content,
            fg_color="transparent"
        )
        self.scroll_frame.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 18))
        self.scroll_frame.grid_columnconfigure(0, weight=1)

        self.create_hero_card()
        self.create_config_card()
        self.create_progress_card()
        self.create_table_card()
        self.create_log_card()
        self.animate_button_icons()
        self.animate_hero_glow()

    def create_hero_card(self):
        self.hero_card = ctk.CTkFrame(
            self.scroll_frame,
            fg_color=self.bg_card,
            corner_radius=28,
            border_width=1,
            border_color=self.border_soft,
        )
        self.hero_card.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        self.hero_card.grid_columnconfigure(0, weight=1)
        self.hero_card.grid_columnconfigure(1, weight=0)

        hero_left = ctk.CTkFrame(self.hero_card, fg_color="transparent")
        hero_left.grid(row=0, column=0, sticky="nsew", padx=(22, 16), pady=(20, 20))
        hero_left.grid_columnconfigure((0, 1, 2), weight=1)

        self._hero_glow_strip = ctk.CTkFrame(self.hero_card, height=4, fg_color=self.hero_glow, corner_radius=999)
        self._hero_glow_strip.grid(row=0, column=0, columnspan=2, sticky="new", padx=18, pady=(10, 0))

        hero_label = ctk.CTkLabel(
            hero_left,
            text="SYNC GRID // REALTIME OPERATIONS",
            font=self._micro_font,
            text_color=self.accent_alt,
        )
        hero_label.grid(row=0, column=0, columnspan=3, sticky="w")

        hero_title = ctk.CTkLabel(
            hero_left,
            text="Interface de comando desenhada para parecer sistema de bordo, não formulário comum.",
            font=ctk.CTkFont(family="Bahnschrift SemiBold", size=24),
            text_color=self.text_main,
            justify="left",
        )
        hero_title.grid(row=1, column=0, columnspan=3, sticky="w", pady=(8, 8))

        hero_desc = ctk.CTkLabel(
            hero_left,
            text="Use o painel para operar varredura, conexões e atualização com feedback visual mais claro, contraste alto e leitura rápida.",
            font=ctk.CTkFont(family="Bahnschrift", size=14),
            text_color=self.text_soft,
            justify="left",
            wraplength=720,
        )
        hero_desc.grid(row=2, column=0, columnspan=3, sticky="w", pady=(0, 14))

        self._hero_status_pill = ctk.CTkFrame(
            hero_left,
            fg_color=self.bg_card_2,
            corner_radius=999,
            border_width=1,
            border_color=self.hero_line,
        )
        self._hero_status_pill.grid(row=3, column=0, sticky="w", padx=(0, 12), pady=(0, 8))
        ctk.CTkLabel(self._hero_status_pill, text="ENGINE", font=self._micro_font, text_color=self.text_dim).pack(side="left", padx=(12, 8), pady=8)
        self._hero_status_value = ctk.CTkLabel(self._hero_status_pill, text="READY", font=self._micro_font, text_color=self.accent)
        self._hero_status_value.pack(side="left", padx=(0, 12), pady=8)

        self.hero_version_pill = ctk.CTkFrame(hero_left, fg_color=self.bg_card_2, corner_radius=999)
        self.hero_version_pill.grid(row=3, column=1, sticky="w", padx=(0, 12), pady=(0, 8))
        ctk.CTkLabel(self.hero_version_pill, text="VERSION", font=self._micro_font, text_color=self.text_dim).pack(side="left", padx=(12, 8), pady=8)
        self.hero_version_value = ctk.CTkLabel(self.hero_version_pill, text=APP_VERSION, font=self._micro_font, text_color=self.text_main)
        self.hero_version_value.pack(side="left", padx=(0, 12), pady=8)

        self.hero_company_pill = ctk.CTkFrame(hero_left, fg_color=self.bg_card_2, corner_radius=999)
        self.hero_company_pill.grid(row=3, column=2, sticky="w", pady=(0, 8))
        ctk.CTkLabel(self.hero_company_pill, text="COMPANY", font=self._micro_font, text_color=self.text_dim).pack(side="left", padx=(12, 8), pady=8)
        self.hero_company_value = ctk.CTkLabel(self.hero_company_pill, text="AUTO", font=self._micro_font, text_color=self.text_main)
        self.hero_company_value.pack(side="left", padx=(0, 12), pady=8)

        hero_right = ctk.CTkFrame(
            self.hero_card,
            fg_color=self.bg_card_2,
            corner_radius=24,
            border_width=1,
            border_color=self.border_soft,
        )
        hero_right.grid(row=0, column=1, sticky="ns", padx=(0, 22), pady=(20, 20))

        ctk.CTkLabel(hero_right, text="LIVE", font=self._micro_font, text_color=self.accent_alt).pack(anchor="w", padx=16, pady=(16, 8))
        self.hero_metric_primary = ctk.CTkLabel(hero_right, text="0", font=ctk.CTkFont(family="Bahnschrift SemiBold", size=34), text_color=self.text_main)
        self.hero_metric_primary.pack(anchor="w", padx=16)
        ctk.CTkLabel(hero_right, text="arquivos processados", font=ctk.CTkFont(family="Bahnschrift", size=13), text_color=self.text_soft).pack(anchor="w", padx=16)

        self.hero_metric_success = ctk.CTkLabel(hero_right, text="Sucesso 0", font=ctk.CTkFont(family="Bahnschrift SemiBold", size=16), text_color=self.success_color)
        self.hero_metric_success.pack(anchor="w", padx=16, pady=(16, 4))
        self.hero_metric_error = ctk.CTkLabel(hero_right, text="Erros 0", font=ctk.CTkFont(family="Bahnschrift SemiBold", size=16), text_color=self.error_color)
        self.hero_metric_error.pack(anchor="w", padx=16, pady=(0, 16))

    def load_logo(self):
        # Destroy previous widgets if reloaded
        for attr in ("_logo_anim_frame",):
            obj = getattr(self, attr, None)
            if obj:
                try:
                    obj.destroy()
                except Exception:
                    pass
                setattr(self, attr, None)

        # Outer animated badge frame
        self._logo_anim_frame = ctk.CTkFrame(
            self.logo_wrap,
            fg_color=self.bg_card_2,
            corner_radius=18,
            border_width=2,
            border_color=self.accent,
        )
        self._logo_anim_frame.pack(anchor="center", pady=(18, 10))

        self.logo_label = ctk.CTkLabel(self._logo_anim_frame, text="", fg_color="transparent")
        self.logo_label.pack(padx=16, pady=14)

        logo_size = (90, 58)
        logo_candidates = [
            resource_path("logo.png"),
            resource_path("logo.jpg"),
            resource_path("logo.jpeg"),
        ]
        logo_loaded = False
        for logo_path in logo_candidates:
            try:
                if os.path.exists(logo_path):
                    pil_img = Image.open(logo_path)
                    self.logo_image = ctk.CTkImage(
                        light_image=pil_img,
                        dark_image=pil_img,
                        size=logo_size
                    )
                    self.logo_label.configure(image=self.logo_image)
                    logo_loaded = True
                    break
            except Exception:
                pass

        if not logo_loaded:
            self.logo_label.configure(
                text="VX",
                font=ctk.CTkFont(size=32, weight="bold"),
                text_color=self.accent
            )

        if ENABLE_SIDEBAR_LOGO_ANIMATION:
            self._animate_logo_glow()
        else:
            self._logo_anim_frame.configure(border_color="#1F3A39")

    def _animate_logo_glow(self):
        import math
        try:
            if not self.winfo_exists():
                return
            if not self._logo_anim_frame or not self._logo_anim_frame.winfo_exists():
                return
        except Exception:
            return

        # While the window is being moved/resized, pause expensive border redraws.
        if time.time() < self._ui_motion_suspend_until:
            self.after(LOGO_ANIMATION_INTERVAL_MS, self._animate_logo_glow)
            return

        # Pulse border from dim teal to bright teal
        t = 0.5 + 0.5 * math.sin(self._logo_glow_phase)
        tr, tg, tb = 0x0E, 0xA5, 0xA0   # bright teal  #0EA5A0
        dr, dg, db = 0x03, 0x28, 0x27   # dim teal
        r = int(dr + (tr - dr) * t)
        g = int(dg + (tg - dg) * t)
        b = int(db + (tb - db) * t)
        color = f"#{r:02x}{g:02x}{b:02x}"
        self._logo_anim_frame.configure(border_color=color)

        self._logo_glow_phase += 0.03
        self.after(LOGO_ANIMATION_INTERVAL_MS, self._animate_logo_glow)


    def _on_window_configure(self, _event):
        self._ui_motion_suspend_until = time.time() + WINDOW_MOVE_PAUSE_SECONDS



    def load_image_for_notice(self, size=(118, 118)):
        logo_candidates = [
            resource_path("logo.png"),
            resource_path("logo.jpg"),
            resource_path("logo.jpeg"),
            resource_path("1.png"),
        ]
        for logo_path in logo_candidates:
            try:
                if os.path.exists(logo_path):
                    pil_image = Image.open(logo_path)
                    return ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=size)
            except Exception:
                pass
        return None

    def persist_runtime_version_state(self):
        try:
            config_path = get_config_read_path()
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                if not isinstance(config, dict):
                    config = self.get_config()
            else:
                config = self.get_config()

            config["last_seen_build_id"] = self.runtime_build_id
            config["last_seen_version"] = APP_VERSION

            with open(get_primary_config_path(), "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=4)

            self.last_seen_build_id = self.runtime_build_id
        except Exception as e:
            self.log(f"Aviso: não foi possível salvar estado da versão: {e}")

    def show_startup_update_notice_if_needed(self):
        if self.last_seen_build_id == self.runtime_build_id:
            return

        notice = ctk.CTkToplevel(self)
        notice.title("Atualização Aplicada")
        notice.geometry("560x430")
        notice.resizable(False, False)
        notice.transient(self)
        notice.grab_set()
        notice.configure(fg_color=self.bg_card)

        box = ctk.CTkFrame(notice, fg_color=self.bg_card, corner_radius=0)
        box.pack(fill="both", expand=True, padx=20, pady=20)

        logo_label = ctk.CTkLabel(box, text="")
        logo_label.pack(pady=(6, 10))

        notice_logo = self.load_image_for_notice()
        if notice_logo:
            notice.logo_image = notice_logo
            logo_label.configure(image=notice.logo_image)
        else:
            logo_label.configure(text="VX", font=ctk.CTkFont(size=36, weight="bold"))

        title = ctk.CTkLabel(
            box,
            text="Atualização Detectada",
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color=self.text_main,
        )
        title.pack()

        version_info = ctk.CTkLabel(
            box,
            text=(
                f"Versão: {APP_VERSION}\n"
                f"Build atual: {self.runtime_build_id}\n"
                f"Build anterior: {self.last_seen_build_id or 'primeira execução'}"
            ),
            font=ctk.CTkFont(size=13),
            text_color=self.text_soft,
            justify="center",
        )
        version_info.pack(pady=(8, 12))

        notes_text = "\n".join([f"- {item}" for item in APP_CHANGELOG])
        notes = ctk.CTkLabel(
            box,
            text=f"Mudanças desta versão:\n{notes_text}",
            font=ctk.CTkFont(size=13),
            text_color=self.text_main,
            justify="left",
            anchor="w",
        )
        notes.pack(fill="x", padx=12, pady=(0, 16))

        def close_notice():
            self.persist_runtime_version_state()
            notice.destroy()

        ok_button = ctk.CTkButton(
            box,
            text="Continuar",
            command=close_notice,
            fg_color=self.accent,
            hover_color=self.accent_hover,
            width=180,
            height=40,
        )
        ok_button.pack(pady=(4, 0))

        notice.protocol("WM_DELETE_WINDOW", close_notice)

    def check_for_updates_automatically(self):
        if not self.auto_update_enabled:
            return

        threading.Thread(
            target=self.check_for_updates,
            kwargs={"silent": True, "auto_install": True},
            daemon=True,
        ).start()

    def show_update_progress_window(self, message="Baixando atualização..."):
        if self.update_progress_window and self.update_progress_window.winfo_exists():
            self.update_progress_window.lift()
            if self.update_progress_label:
                self.update_progress_label.configure(text=message)
            return

        win = ctk.CTkToplevel(self)
        win.title("Atualizando")
        win.geometry("500x260")
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()
        win.configure(fg_color=self.bg_card)
        win.protocol("WM_DELETE_WINDOW", lambda: None)

        box = ctk.CTkFrame(win, fg_color="transparent")
        box.pack(fill="both", expand=True, padx=20, pady=20)

        logo = ctk.CTkLabel(box, text="")
        logo.pack(pady=(0, 10))

        notice_logo = self.load_image_for_notice(size=(90, 90))
        if notice_logo:
            win.logo_image = notice_logo
            logo.configure(image=win.logo_image)
        else:
            logo.configure(text="VX", font=ctk.CTkFont(size=32, weight="bold"))

        title = ctk.CTkLabel(box, text="Atualizando aplicativo", font=ctk.CTkFont(size=22, weight="bold"))
        title.pack(pady=(0, 8))

        self.update_progress_label = ctk.CTkLabel(box, text=message, text_color=self.text_soft)
        self.update_progress_label.pack(pady=(0, 8))

        self.update_progress_bar = ctk.CTkProgressBar(box, height=20)
        self.update_progress_bar.pack(fill="x", padx=10, pady=(0, 6))
        self.update_progress_bar.set(0)

        self.update_progress_percent = ctk.CTkLabel(box, text="0%", font=ctk.CTkFont(size=13, weight="bold"))
        self.update_progress_percent.pack()

        hint = ctk.CTkLabel(
            box,
            text="Aguarde, a versão antiga será substituída automaticamente.",
            text_color=self.text_soft,
            font=ctk.CTkFont(size=11),
        )
        hint.pack(pady=(10, 0))

        self.update_progress_window = win

    def set_update_progress(self, percent, message):
        if self.update_progress_window is None or not self.update_progress_window.winfo_exists():
            return

        value = max(0.0, min(1.0, float(percent)))
        if self.update_progress_bar:
            self.update_progress_bar.set(value)
        if self.update_progress_percent:
            self.update_progress_percent.configure(text=f"{int(value * 100)}%")
        if self.update_progress_label:
            self.update_progress_label.configure(text=message)

    def close_update_progress_window(self):
        try:
            if self.update_progress_window and self.update_progress_window.winfo_exists():
                self.update_progress_window.destroy()
        except Exception:
            pass
        self.update_progress_window = None
        self.update_progress_label = None
        self.update_progress_bar = None
        self.update_progress_percent = None

    def create_config_card(self):
        self.config_card = ctk.CTkFrame(
            self.scroll_frame,
            fg_color=self.bg_card,
            corner_radius=26,
            border_width=1,
            border_color=self.border_soft
        )
        self.config_card.grid(row=1, column=0, sticky="ew", pady=(0, 14))
        self.config_card.grid_columnconfigure(1, weight=1)

        self.config_title = ctk.CTkLabel(
            self.config_card,
            text="Configuração de Fluxo",
            font=self._section_font,
            text_color=self.text_main
        )
        self.config_title.grid(row=0, column=0, columnspan=3, sticky="w", padx=18, pady=(18, 16))

        self.config_subtitle = ctk.CTkLabel(
            self.config_card,
            text="Pontos de origem, endpoint, identificação e política operacional do agente.",
            font=ctk.CTkFont(family="Bahnschrift", size=13),
            text_color=self.text_soft,
        )
        self.config_subtitle.grid(row=1, column=0, columnspan=3, sticky="w", padx=18, pady=(0, 10))

        self._cfg_row = 2

        self.folder1_entry = self.add_entry_with_button("Pasta 1", lambda: self.select_folder(self.folder1_entry))
        self.folder2_entry = self.add_entry_with_button("Pasta 2", lambda: self.select_folder(self.folder2_entry))
        self.folder3_entry = self.add_entry_with_button("Pasta 3", lambda: self.select_folder(self.folder3_entry))
        self.api_base_entry = self.add_entry("URL base da API")
        self.upload_endpoint_entry = self.add_entry("Endpoint de upload")
        self.api_token_entry = self.add_entry("Token da API", show="*")
        self.company_id_entry = self.add_entry("ID da empresa")
        self.company_name_entry = self.add_entry("Nome da empresa")
        self.company_cnpj_entry = self.add_entry("CNPJ")
        self.sent_folder_entry = self.add_entry("Pasta de enviados")
        self.error_folder_entry = self.add_entry("Pasta de erros")
        self.interval_entry = self.add_entry("Intervalo da varredura (segundos)")
        self.update_manifest_url_entry = self.add_entry("URL de atualização")

        self.company_name_entry.bind("<KeyRelease>", lambda _event: self.update_company_status())
        self.company_cnpj_entry.bind("<KeyRelease>", lambda _event: self.update_company_status())
        self.company_id_entry.bind("<KeyRelease>", lambda _event: self.update_company_status())

        self.options_frame = ctk.CTkFrame(self.config_card, fg_color="transparent")
        self.options_frame.grid(row=self._cfg_row, column=0, columnspan=3, sticky="w", padx=18, pady=(8, 10))

        self.move_sent_var = ctk.BooleanVar(value=True)
        self.monitor_subfolders_var = ctk.BooleanVar(value=True)
        self.verify_ssl_var = ctk.BooleanVar(value=True)
        self.auto_start_windows_var = ctk.BooleanVar(value=False)
        self.minimize_to_tray_var = ctk.BooleanVar(value=True)

        self.move_sent_check = ctk.CTkCheckBox(self.options_frame, text="Mover arquivos enviados", variable=self.move_sent_var)
        self.move_sent_check.grid(row=0, column=0, padx=(0, 14), pady=8)

        self.monitor_subfolders_check = ctk.CTkCheckBox(self.options_frame, text="Monitorar subpastas", variable=self.monitor_subfolders_var)
        self.monitor_subfolders_check.grid(row=0, column=1, padx=(0, 14), pady=8)

        self.verify_ssl_check = ctk.CTkCheckBox(self.options_frame, text="Validar SSL/HTTPS", variable=self.verify_ssl_var)
        self.verify_ssl_check.grid(row=0, column=2, padx=(0, 14), pady=8)

        self.auto_start_check = ctk.CTkCheckBox(
            self.options_frame,
            text="Iniciar com Windows",
            variable=self.auto_start_windows_var,
            command=self.toggle_windows_startup
        )
        self.auto_start_check.grid(row=1, column=0, padx=(0, 14), pady=8, sticky="w")

        self.minimize_to_tray_check = ctk.CTkCheckBox(
            self.options_frame,
            text="Minimizar para bandeja",
            variable=self.minimize_to_tray_var
        )
        self.minimize_to_tray_check.grid(row=1, column=1, padx=(0, 14), pady=8, sticky="w")

        self.buttons_frame = ctk.CTkFrame(self.config_card, fg_color="transparent")
        self.buttons_frame.grid(row=self._cfg_row + 1, column=0, columnspan=3, sticky="w", padx=18, pady=(4, 18))

        self.save_btn = ctk.CTkButton(
            self.buttons_frame, text="Salvar", command=self.save_config,
            fg_color=self.bg_card_2, hover_color=self.bg_card_3, width=156, height=46,
            corner_radius=16, border_width=1, border_color=self.border_soft, text_color=self.text_main
        )
        self.save_btn.grid(row=0, column=0, padx=(0, 10), pady=6)

        self.test_btn = ctk.CTkButton(
            self.buttons_frame, text="Testar Upload", command=self.test_upload,
            fg_color=self.bg_card_2, hover_color=self.bg_card_3, width=156, height=46,
            corner_radius=16, border_width=1, border_color=self.border_soft, text_color=self.text_main
        )
        self.test_btn.grid(row=0, column=1, padx=(0, 10), pady=6)

        self.start_btn = ctk.CTkButton(
            self.buttons_frame, text="Iniciar", command=self.start_monitoring,
            fg_color=self.bg_card_2, hover_color=self.bg_card_3, width=156, height=46,
            corner_radius=16, border_width=1, border_color=self.border_soft, text_color=self.text_main
        )
        self.start_btn.grid(row=0, column=2, padx=(0, 10), pady=6)

        self.stop_btn = ctk.CTkButton(
            self.buttons_frame, text="Parar", command=self.stop_monitoring,
            fg_color=self.bg_card_2, hover_color=self.bg_card_3, width=156, height=46,
            corner_radius=16, border_width=1, border_color=self.border_soft, text_color=self.text_main
        )
        self.stop_btn.grid(row=0, column=3, padx=(0, 10), pady=6)

        self.process_existing_btn = ctk.CTkButton(
            self.buttons_frame, text="Processar Existentes", command=self.process_existing_files,
            fg_color=self.bg_card_2, hover_color=self.bg_card_3, width=200, height=46,
            corner_radius=16, border_width=1, border_color=self.border_soft, text_color=self.text_main
        )
        self.process_existing_btn.grid(row=0, column=4, padx=(0, 10), pady=6)

        self.register_animated_button(self.save_btn, "save", self.accent)
        self.register_animated_button(self.test_btn, "network", self.warning_color)
        self.register_animated_button(self.start_btn, "play", self.success_color)
        self.register_animated_button(self.stop_btn, "stop", self.error_color)
        self.register_animated_button(self.process_existing_btn, "scan", self.accent_alt)

    def create_progress_card(self):
        self.progress_card = ctk.CTkFrame(
            self.scroll_frame,
            fg_color=self.bg_card,
            corner_radius=26,
            border_width=1,
            border_color=self.border_soft
        )
        self.progress_card.grid(row=2, column=0, sticky="ew", pady=(0, 14))
        self.progress_card.grid_columnconfigure(0, weight=1)

        self.progress_title = ctk.CTkLabel(
            self.progress_card,
            text="Radar de Processamento",
            font=self._section_font,
            text_color=self.text_main
        )
        self.progress_title.grid(row=0, column=0, sticky="w", padx=18, pady=(18, 10))

        self.progress_info_label = ctk.CTkLabel(
            self.progress_card,
            text="Aguardando processamento...",
            text_color=self.text_soft
        )
        self.progress_info_label.grid(row=1, column=0, sticky="w", padx=18, pady=(0, 8))

        self.progress_bar = ctk.CTkProgressBar(self.progress_card, height=18)
        self.progress_bar.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 10))
        self.progress_bar.set(0)
        self.progress_bar.configure(progress_color=self.accent, fg_color=self.bg_card_2)

        self.progress_percent_label = ctk.CTkLabel(
            self.progress_card,
            text="0%",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.text_main
        )
        self.progress_percent_label.grid(row=3, column=0, sticky="e", padx=18, pady=(0, 18))

    def create_table_card(self):
        self.table_card = ctk.CTkFrame(
            self.scroll_frame,
            fg_color=self.bg_card,
            corner_radius=26,
            border_width=1,
            border_color=self.border_soft
        )
        self.table_card.grid(row=3, column=0, sticky="ew", pady=(0, 14))
        self.table_card.grid_columnconfigure(0, weight=1)

        self.table_title = ctk.CTkLabel(
            self.table_card,
            text="Fluxo de Arquivos Transmitidos",
            font=self._section_font,
            text_color=self.text_main
        )
        self.table_title.grid(row=0, column=0, sticky="w", padx=18, pady=(18, 12))

        self.table_wrap = ctk.CTkFrame(self.table_card, fg_color="transparent")
        self.table_wrap.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
        self.table_wrap.grid_columnconfigure(0, weight=1)

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(
            "Treeview",
            background=self.input_bg,
            foreground=self.text_main,
            fieldbackground=self.input_bg,
            rowheight=30,
            bordercolor=self.border,
            borderwidth=0
        )
        style.configure(
            "Treeview.Heading",
            background=self.bg_card_2,
            foreground=self.text_main,
            relief="flat"
        )
        style.map("Treeview", background=[("selected", self.hero_line)])

        columns = ("datahora", "arquivo", "empresa", "status", "http", "mensagem")
        self.tree = ttk.Treeview(self.table_wrap, columns=columns, show="headings", height=10)

        self.tree.heading("datahora", text="Data/Hora")
        self.tree.heading("arquivo", text="Arquivo")
        self.tree.heading("empresa", text="Empresa")
        self.tree.heading("status", text="Status")
        self.tree.heading("http", text="HTTP")
        self.tree.heading("mensagem", text="Mensagem")

        self.tree.column("datahora", width=150, anchor="center")
        self.tree.column("arquivo", width=260, anchor="w")
        self.tree.column("empresa", width=100, anchor="center")
        self.tree.column("status", width=100, anchor="center")
        self.tree.column("http", width=70, anchor="center")
        self.tree.column("mensagem", width=360, anchor="w")

        self.tree.grid(row=0, column=0, sticky="nsew")

        self.tree_scroll = ttk.Scrollbar(self.table_wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.tree_scroll.set)
        self.tree_scroll.grid(row=0, column=1, sticky="ns")

    def create_log_card(self):
        self.log_card = ctk.CTkFrame(
            self.scroll_frame,
            fg_color=self.bg_card,
            corner_radius=26,
            border_width=1,
            border_color=self.border_soft
        )
        self.log_card.grid(row=4, column=0, sticky="ew", pady=(0, 10))
        self.log_card.grid_columnconfigure(0, weight=1)

        self.log_title = ctk.CTkLabel(
            self.log_card,
            text="Console Operacional",
            font=self._section_font,
            text_color=self.text_main
        )
        self.log_title.grid(row=0, column=0, sticky="w", padx=18, pady=(18, 12))

        self.log_text = ctk.CTkTextbox(self.log_card, height=220, fg_color=self.input_bg, border_width=1, border_color=self.border_soft, text_color=self.text_main)
        self.log_text.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 18))
        self.log_text.insert("end", "Sistema iniciado.\n")
        self.log_text.configure(state="disabled")

    def add_entry(self, label_text, show=None):
        row = self._cfg_row
        label = ctk.CTkLabel(self.config_card, text=label_text.upper(), width=210, anchor="w", text_color=self.text_soft, font=self._micro_font)
        label.grid(row=row, column=0, sticky="w", padx=(18, 12), pady=8)

        entry = ctk.CTkEntry(
            self.config_card,
            height=44,
            show=show,
            fg_color=self.input_bg,
            border_color=self.border_soft,
            text_color=self.text_main,
            corner_radius=14,
            font=ctk.CTkFont(family="Bahnschrift", size=13)
        )
        entry.grid(row=row, column=1, sticky="ew", padx=(0, 12), pady=8)

        self._cfg_row += 1
        return entry

    def add_entry_with_button(self, label_text, browse_command):
        row = self._cfg_row
        label = ctk.CTkLabel(self.config_card, text=label_text.upper(), width=210, anchor="w", text_color=self.text_soft, font=self._micro_font)
        label.grid(row=row, column=0, sticky="w", padx=(18, 12), pady=8)

        entry = ctk.CTkEntry(
            self.config_card,
            height=44,
            fg_color=self.input_bg,
            border_color=self.border_soft,
            text_color=self.text_main,
            corner_radius=14,
            font=ctk.CTkFont(family="Bahnschrift", size=13)
        )
        entry.grid(row=row, column=1, sticky="ew", padx=(0, 12), pady=8)

        button = ctk.CTkButton(
            self.config_card,
            text="Selecionar",
            width=120,
            command=browse_command,
            fg_color=self.bg_card_2,
            hover_color=self.bg_card_3,
            corner_radius=14,
            height=44,
            border_width=1,
            border_color=self.border_soft,
            text_color=self.text_main,
            font=self._button_font
        )
        button.grid(row=row, column=2, sticky="e", padx=(0, 18), pady=8)

        self.register_animated_button(button, "scan", self.accent)

        self._cfg_row += 1
        return entry

    # ---------------------------
    # Helpers UI thread-safe
    # ---------------------------
    def ui(self, func, *args, **kwargs):
        self.after(0, lambda: func(*args, **kwargs))

    def log(self, message):
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        final_message = f"[{timestamp}] {message}\n"

        self._log_buffer.append(final_message)

        if self._log_flush_scheduled:
            if ENABLE_CONSOLE_LOG:
                print(final_message.strip())
            return

        self._log_flush_scheduled = True

        def append_batched():
            if not self._log_buffer:
                self._log_flush_scheduled = False
                return
            chunk = "".join(self._log_buffer)
            self._log_buffer.clear()
            self.log_text.configure(state="normal")
            self.log_text.insert("end", chunk)
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
            self._log_flush_scheduled = False

        self.after(120, append_batched)

        if ENABLE_CONSOLE_LOG:
            print(final_message.strip())

    def set_status(self, text, color=None):
        def update():
            self.status_label.configure(text=text)
            if color:
                self.status_label.configure(text_color=color)
            if self._hero_status_value and self._hero_status_value.winfo_exists():
                self._hero_status_value.configure(text=str(text).upper())
                if color:
                    self._hero_status_value.configure(text_color=color)
        self.ui(update)

    def update_company_status(self):
        company_name = self.company_name_entry.get().strip() or "-"
        company_cnpj = format_cnpj(self.company_cnpj_entry.get().strip())
        company_id = self.company_id_entry.get().strip() or "-"
        self.company_name_status_label.configure(text=f"Empresa: {company_name}")
        self.company_cnpj_status_label.configure(text=f"CNPJ: {company_cnpj}")
        self.company_id_status_label.configure(text=f"Empresa ID: {company_id}")
        if hasattr(self, "hero_company_value") and self.hero_company_value.winfo_exists():
            self.hero_company_value.configure(text=(company_id if company_id != "-" else "AUTO").upper())

    def update_stats_labels(self):
        self.total_label.configure(text=f"Total processados: {self.total_processed}")
        self.success_label.configure(text=f"Sucesso: {self.success_count}")
        self.error_label.configure(text=f"Erros: {self.error_count}")
        if hasattr(self, "hero_metric_primary") and self.hero_metric_primary.winfo_exists():
            self.hero_metric_primary.configure(text=str(self.total_processed))
        if hasattr(self, "hero_metric_success") and self.hero_metric_success.winfo_exists():
            self.hero_metric_success.configure(text=f"Sucesso {self.success_count}")
        if hasattr(self, "hero_metric_error") and self.hero_metric_error.winfo_exists():
            self.hero_metric_error.configure(text=f"Erros {self.error_count}")

    def update_progress(self, done, total, text=None):
        self.scan_done = done
        self.scan_total = total

        total = max(total, 1)
        percent = done / total

        def _update():
            self.progress_bar.set(percent)
            self.progress_percent_label.configure(text=f"{int(percent * 100)}%")
            if text:
                self.progress_info_label.configure(text=text)

        self.ui(_update)

    def reset_progress(self, text="Aguardando processamento..."):
        def _reset():
            self.progress_bar.set(0)
            self.progress_percent_label.configure(text="0%")
            self.progress_info_label.configure(text=text)
        self.ui(_reset)

    def add_table_row(self, arquivo, empresa, status, http_code, mensagem):
        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        def _insert():
            children = self.tree.get_children()
            if len(children) >= MAX_TABLE_ROWS:
                self.tree.delete(children[-1])

            self.tree.insert(
                "",
                0,
                values=(now, arquivo, empresa, status, http_code, mensagem[:120])
            )

        self.ui(_insert)

    def select_folder(self, entry_widget):
        folder = filedialog.askdirectory()
        if folder:
            entry_widget.delete(0, "end")
            entry_widget.insert(0, folder)

    def set_entry(self, entry, value):
        entry.delete(0, "end")
        entry.insert(0, value)

    # ---------------------------
    # Config
    # ---------------------------
    def get_config(self):
        return {
            "folder_1": self.folder1_entry.get().strip(),
            "folder_2": self.folder2_entry.get().strip(),
            "folder_3": self.folder3_entry.get().strip(),
            "api_base_url": FIXED_API_BASE_URL,
            "upload_endpoint": self.upload_endpoint_entry.get().strip(),
            "api_token": self.api_token_entry.get().strip(),
            "company_id": self.company_id_entry.get().strip(),
            "company_name": self.company_name_entry.get().strip(),
            "company_cnpj": self.company_cnpj_entry.get().strip(),
            "sent_folder": self.sent_folder_entry.get().strip() or "enviados",
            "error_folder": self.error_folder_entry.get().strip() or "erros",
            "scan_interval": self.interval_entry.get().strip() or "15",
            "update_manifest_url": self.update_manifest_url_entry.get().strip(),
            "last_seen_build_id": self.last_seen_build_id,
            "last_applied_setup_sha256": self.last_applied_setup_sha256,
            "last_applied_version": self.last_applied_version,
            "auto_update_enabled": self.auto_update_enabled,
            "move_sent_files": self.move_sent_var.get(),
            "monitor_subfolders": self.monitor_subfolders_var.get(),
            "verify_ssl": self.verify_ssl_var.get(),
            "auto_start_windows": self.auto_start_windows_var.get(),
            "minimize_to_tray": self.minimize_to_tray_var.get()
        }

    def persist_update_hash_state(self):
        try:
            config_path = get_config_read_path()
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                if not isinstance(config, dict):
                    config = self.get_config()
            else:
                config = self.get_config()

            config["last_applied_setup_sha256"] = self.last_applied_setup_sha256
            config["last_applied_version"] = self.last_applied_version

            with open(get_primary_config_path(), "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            self.log(f"Aviso: não foi possível persistir hash da atualização: {e}")

    def save_config(self):
        try:
            config = self.get_config()
            config_path = get_primary_config_path()

            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=4)

            self.update_company_status()
            self.log("Configuração salva com sucesso.")
            self.toggle_windows_startup(silent=True)
            messagebox.showinfo("Sucesso", "Configuração salva com sucesso.")
        except Exception as e:
            self.log(f"Erro ao salvar configuração: {e}")
            messagebox.showerror("Erro", f"Falha ao salvar configuração:\n{e}")

    def load_config(self):
        config_path = get_config_read_path()

        if not os.path.exists(config_path):
            self.log("config.json não encontrado. Usando valores padrão.")
            self.set_default_values()
            return

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            self.set_entry(self.folder1_entry, config.get("folder_1", ""))
            self.set_entry(self.folder2_entry, config.get("folder_2", ""))
            self.set_entry(self.folder3_entry, config.get("folder_3", ""))
            self.set_entry(self.api_base_entry, FIXED_API_BASE_URL)
            self.set_entry(self.upload_endpoint_entry, config.get("upload_endpoint", "/receiveDocument"))
            self.set_entry(self.api_token_entry, config.get("api_token", ""))
            self.set_entry(self.company_id_entry, config.get("company_id", ""))
            self.set_entry(self.company_name_entry, config.get("company_name", ""))
            self.set_entry(self.company_cnpj_entry, config.get("company_cnpj", ""))
            self.set_entry(self.sent_folder_entry, config.get("sent_folder", "enviados"))
            self.set_entry(self.error_folder_entry, config.get("error_folder", "erros"))
            self.set_entry(self.interval_entry, str(config.get("scan_interval", "15")))
            self.set_entry(
                self.update_manifest_url_entry,
                str(config.get("update_manifest_url", "") or "").strip() or DEFAULT_UPDATE_MANIFEST_URL
            )
            self.last_seen_build_id = str(config.get("last_seen_build_id", "")).strip()
            self.last_applied_setup_sha256 = str(config.get("last_applied_setup_sha256", "")).strip().lower()
            self.last_applied_version = str(config.get("last_applied_version", "")).strip()
            self.auto_update_enabled = normalize_bool(config.get("auto_update_enabled", AUTO_UPDATE_ON_START), AUTO_UPDATE_ON_START)

            self.move_sent_var.set(normalize_bool(config.get("move_sent_files", True), True))
            self.monitor_subfolders_var.set(normalize_bool(config.get("monitor_subfolders", True), True))
            self.verify_ssl_var.set(normalize_bool(config.get("verify_ssl", True), True))
            self.auto_start_windows_var.set(normalize_bool(config.get("auto_start_windows", False), False))
            self.minimize_to_tray_var.set(normalize_bool(config.get("minimize_to_tray", True), True))

            self.log("Configuração carregada com sucesso.")
        except Exception as e:
            self.log(f"Erro ao carregar configuração: {e}")
            self.set_default_values()
            self.last_seen_build_id = ""

    def set_default_values(self):
        self.set_entry(self.api_base_entry, FIXED_API_BASE_URL)
        self.set_entry(self.upload_endpoint_entry, "/receiveDocument")
        self.set_entry(self.company_name_entry, "")
        self.set_entry(self.company_cnpj_entry, "")
        self.set_entry(self.sent_folder_entry, "enviados")
        self.set_entry(self.error_folder_entry, "erros")
        self.set_entry(self.interval_entry, "15")
        self.set_entry(self.update_manifest_url_entry, DEFAULT_UPDATE_MANIFEST_URL)
        self.last_applied_setup_sha256 = ""
        self.last_applied_version = ""
        self.auto_update_enabled = AUTO_UPDATE_ON_START
        self.move_sent_var.set(True)
        self.monitor_subfolders_var.set(True)
        self.verify_ssl_var.set(True)
        self.auto_start_windows_var.set(False)
        self.minimize_to_tray_var.set(True)

    def download_and_launch_update_installer(self, download_url, latest_version, silent=False, setup_sha256=""):
        try:
            updates_dir = get_user_update_dir()

            url_path = urlsplit(download_url).path
            file_name = os.path.basename(url_path) or f"VEXPER-SISTEMAS-Setup-{latest_version}.exe"
            if not file_name.lower().endswith(".exe"):
                file_name += ".exe"

            target_path = os.path.join(updates_dir, file_name)
            temp_fd, temp_path = tempfile.mkstemp(prefix="vexper_update_", suffix=".exe")
            os.close(temp_fd)

            self.ui(self.show_update_progress_window, "Baixando atualização...")

            self.log(f"Baixando atualização automática: {download_url}")
            with requests.get(download_url, stream=True, timeout=120) as r:
                r.raise_for_status()
                total_size = int(r.headers.get("content-length", "0") or "0")
                downloaded = 0
                with open(temp_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 256):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                pct = min(0.9, (downloaded / total_size) * 0.9)
                                self.ui(self.set_update_progress, pct, "Baixando atualização...")

            shutil.move(temp_path, target_path)
            self.log(f"Atualização baixada em: {target_path}")

            self.ui(self.set_update_progress, 0.95, "Preparando instalação...")

            pid = os.getpid()
            updater_bat = os.path.join(tempfile.gettempdir(), f"vexper_updater_{pid}.bat")
            with open(updater_bat, "w", encoding="utf-8") as bat:
                bat.write("@echo off\n")
                bat.write(f"set PID={pid}\n")
                bat.write(":waitloop\n")
                bat.write("tasklist /FI \"PID eq %PID%\" | find \"%PID%\" >nul\n")
                bat.write("if not errorlevel 1 (\n")
                bat.write("  timeout /t 1 /nobreak >nul\n")
                bat.write("  goto waitloop\n")
                bat.write(")\n")
                bat.write("timeout /t 1 /nobreak >nul\n")
                bat.write("taskkill /IM \"VEXPER-SISTEMAS.exe\" /F >nul 2>&1\n")
                bat.write("timeout /t 1 /nobreak >nul\n")
                bat.write(
                    f"start \"\" \"{target_path}\" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP- /CLOSEAPPLICATIONS /FORCECLOSEAPPLICATIONS\n"
                )

            subprocess.Popen(["cmd", "/c", updater_bat], creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            self.log("Instalador agendado para iniciar após fechamento do aplicativo.")

            if setup_sha256:
                self.last_applied_setup_sha256 = str(setup_sha256).strip().lower()
            self.last_applied_version = str(latest_version or "").strip()
            self.persist_update_hash_state()

            if not silent:
                messagebox.showinfo(
                    "Atualização",
                    "Atualização iniciada em segundo plano. O aplicativo será fechado para concluir."
                )

            self.ui(self.set_update_progress, 1.0, "Instalando nova versão...")
            self.after(700, self.destroy)
        except Exception as e:
            self.log(f"Erro ao baixar/instalar atualização automática: {e}")
            self.ui(self.close_update_progress_window)
            if not silent:
                messagebox.showerror("Atualização", f"Falha ao aplicar atualização automática:\n{e}")

    def check_for_updates(self, silent=False, auto_install=False):
        update_url = self.update_manifest_url_entry.get().strip()
        if not update_url:
            update_url = DEFAULT_UPDATE_MANIFEST_URL
            self.set_entry(self.update_manifest_url_entry, update_url)
        if not update_url:
            if not silent:
                messagebox.showwarning("Atualização", "Informe a URL de atualização nas configurações.")
            return

        self.log(f"Verificando atualização em: {update_url}")
        try:
            response = requests.get(update_url, timeout=20)
            response.raise_for_status()
            payload = response.json()

            latest_version, download_url, notes, setup_sha256 = extract_update_info(payload)

            if not latest_version:
                if not silent:
                    messagebox.showerror("Atualização", "Resposta inválida: campo de versão não encontrado.")
                return

            current_tuple = normalize_version(APP_VERSION)
            latest_tuple = normalize_version(latest_version)
            known_hash = str(self.last_applied_setup_sha256 or "").strip().lower()
            known_version = str(self.last_applied_version or "").strip()
            known_version_tuple = normalize_version(known_version) if known_version else (0, 0, 0)
            effective_current_tuple = max(current_tuple, known_version_tuple)
            effective_current_label = APP_VERSION
            if known_version and known_version_tuple >= current_tuple:
                effective_current_label = f"{APP_VERSION} (último pacote aplicado: {known_version})"

            # hash_changed só é relevante se já temos um hash anterior gravado
            # (evita re-instalação em primeiro boot onde known_hash é vazio)
            hash_changed = (
                bool(setup_sha256) and bool(known_hash) and setup_sha256 != known_hash
                and latest_tuple == effective_current_tuple
            )
            already_applied_same_package = bool(setup_sha256) and setup_sha256 == known_hash

            if not already_applied_same_package and (
                latest_tuple > effective_current_tuple or hash_changed
            ):
                msg = (
                    f"Nova versão disponível: {latest_version}\n"
                    f"Versão atual: {effective_current_label}\n\n"
                )
                if hash_changed:
                    msg += "Detectamos mudança no pacote da release (SHA atualizado).\n\n"
                if notes:
                    msg += f"Novidades:\n{notes}\n\n"

                if auto_install and download_url and getattr(sys, "frozen", False):
                    self.log(f"Nova versão detectada ({latest_version}). Iniciando atualização automática.")
                    self.download_and_launch_update_installer(download_url, latest_version, silent=True, setup_sha256=setup_sha256)
                    return

                if download_url:
                    msg += "Deseja baixar e instalar automaticamente agora?"
                    if not silent:
                        install_now = messagebox.askyesno("Atualização disponível", msg)
                        if install_now:
                            threading.Thread(
                                target=self.download_and_launch_update_installer,
                                args=(download_url, latest_version),
                                kwargs={"silent": False, "setup_sha256": setup_sha256},
                                daemon=True,
                            ).start()
                    else:
                        self.log("Atualização disponível, mas não foi possível auto-instalar neste modo.")
                else:
                    if not silent:
                        messagebox.showinfo("Atualização disponível", msg + "Link de download não informado.")
                    else:
                        self.log("Atualização disponível, mas o manifesto não possui download_url.")
            else:
                if not silent:
                    messagebox.showinfo(
                        "Atualização",
                        f"Nenhuma atualização disponível.\nVersão atual: {effective_current_label}\nÚltima versão: {latest_version}"
                    )
                else:
                    self.log(f"Sem atualização. Atual={effective_current_label} | Última={latest_version}")
        except Exception as e:
            self.log(f"Erro ao verificar atualização: {e}")
            if not silent:
                messagebox.showerror("Atualização", f"Falha ao verificar atualização:\n{e}")

    # ---------------------------
    # Startup Windows
    # ---------------------------
    def startup_bat_path(self):
        startup_dir = os.path.join(
            os.environ.get("APPDATA", ""),
            r"Microsoft\Windows\Start Menu\Programs\Startup"
        )
        return os.path.join(startup_dir, "VEXPER_SISTEMAS_Agent.bat")

    def toggle_windows_startup(self, silent=False):
        try:
            bat_path = self.startup_bat_path()

            if self.auto_start_windows_var.get():
                target = sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__)
                if getattr(sys, "frozen", False):
                    content = f'@echo off\nstart "" "{target}"\n'
                else:
                    pythonw = os.path.join(sys.exec_prefix, "pythonw.exe")
                    if not os.path.exists(pythonw):
                        pythonw = sys.executable
                    content = f'@echo off\nstart "" "{pythonw}" "{target}"\n'
                with open(bat_path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.log("Inicialização automática com Windows ativada.")
                if not silent:
                    messagebox.showinfo("Windows", "Inicialização automática ativada.")
            else:
                if os.path.exists(bat_path):
                    os.remove(bat_path)
                    self.log("Inicialização automática com Windows desativada.")
                if not silent:
                    messagebox.showinfo("Windows", "Inicialização automática desativada.")
        except Exception as e:
            self.log(f"Erro ao configurar inicialização com Windows: {e}")
            if not silent:
                messagebox.showerror("Erro", f"Falha ao configurar inicialização automática:\n{e}")

    # ---------------------------
    # Upload
    # ---------------------------
    def build_upload_url(self):
        base = self.api_base_entry.get().strip().rstrip("/")
        endpoint = self.upload_endpoint_entry.get().strip()

        if endpoint and not endpoint.startswith("/"):
            endpoint = "/" + endpoint

        return f"{base}{endpoint}"

    def get_headers(self):
        headers = {}
        token = self.api_token_entry.get().strip()
        company_id = self.company_id_entry.get().strip()

        if token:
            headers["Authorization"] = f"Bearer {token}"
        if company_id:
            headers["X-Company-ID"] = company_id

        return headers

    def validate_basic_config(self):
        if not self.api_base_entry.get().strip():
            messagebox.showwarning("Atenção", "Informe a URL base da API.")
            return False

        if not self.upload_endpoint_entry.get().strip():
            messagebox.showwarning("Atenção", "Informe o endpoint de upload.")
            return False

        if not self.folder1_entry.get().strip() and not self.folder2_entry.get().strip():
            messagebox.showwarning("Atenção", "Informe pelo menos uma pasta para monitorar.")
            return False

        return True

    def test_upload(self):
        if not self.api_base_entry.get().strip():
            messagebox.showwarning("Atenção", "Informe a URL base da API.")
            return

        url = self.build_upload_url()
        headers = self.get_headers()
        verify_ssl = self.verify_ssl_var.get()

        self.log(f"Testando conexão com: {url}")

        try:
            response = requests.get(url, headers=headers, timeout=20, verify=verify_ssl)
            self.log(f"Teste concluído. Status HTTP: {response.status_code}")
            messagebox.showinfo("Teste concluído", f"Resposta HTTP: {response.status_code}")
        except Exception as e:
            self.log(f"Erro no teste de conexão: {e}")
            messagebox.showerror("Erro", f"Falha ao testar conexão:\n{e}")

    # ---------------------------
    # Monitoring
    # ---------------------------
    def start_monitoring(self):
        if self.running:
            messagebox.showinfo("Aviso", "O monitoramento já está em execução.")
            return

        if not self.validate_basic_config():
            return

        self.save_config()
        self.running = True
        self.stop_event.clear()
        self.set_status("Monitorando", self.success_color)
        self.update_company_status()
        self.log("Monitoramento iniciado.")

        self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitor_thread.start()

    def stop_monitoring(self):
        self.running = False
        self.stop_event.set()
        self.set_status("Parado", self.error_color)
        self.reset_progress("Monitoramento interrompido.")
        self.log("Monitoramento interrompido.")

    def process_existing_files(self):
        if not self.validate_basic_config():
            return

        self.save_config()
        self.log("Processando arquivos existentes...")
        threading.Thread(target=self.scan_and_send_files, daemon=True).start()

    def monitor_loop(self):
        while self.running:
            try:
                self.scan_and_send_files()
            except Exception as e:
                self.log(f"Erro no monitoramento: {e}")

            try:
                interval = int(self.interval_entry.get().strip())
            except ValueError:
                interval = 15

            for _ in range(interval):
                if not self.running or self.stop_event.is_set():
                    break
                time.sleep(1)

        self.log("Thread de monitoramento finalizada.")

    def collect_files(self):
        folders = []
        folder1 = self.folder1_entry.get().strip()
        folder2 = self.folder2_entry.get().strip()
        folder3 = self.folder3_entry.get().strip()
        monitor_subfolders = self.monitor_subfolders_var.get()

        if folder1:
            folders.append(folder1)
        if folder2:
            folders.append(folder2)
        if folder3:
            folders.append(folder3)

        valid_files = []

        for folder in folders:
            if not os.path.isdir(folder):
                self.log(f"Pasta não encontrada: {folder}")
                continue

            if monitor_subfolders:
                for root, dirs, files in os.walk(folder):
                    dirs[:] = [d for d in dirs if d.lower() not in ("enviados", "erros")]
                    for file_name in files:
                        if file_name.lower().endswith(".xml"):
                            valid_files.append(os.path.join(root, file_name))
            else:
                for file_name in os.listdir(folder):
                    full_path = os.path.join(folder, file_name)
                    if os.path.isfile(full_path) and file_name.lower().endswith(".xml"):
                        valid_files.append(full_path)

        return valid_files

    def scan_and_send_files(self):
        file_list = self.collect_files()

        if not file_list:
            self.reset_progress("Nenhum XML encontrado para processar.")
            return

        total = len(file_list)
        done = 0
        self.update_progress(0, total, f"Preparando processamento de {total} arquivo(s)...")

        for file_path in file_list:
            if self.stop_event.is_set():
                break

            result = self.upload_file(file_path)
            done += 1

            if result:
                self.success_count += 1
            else:
                self.error_count += 1

            self.total_processed += 1
            self.ui(self.update_stats_labels)

            self.update_progress(
                done,
                total,
                f"Processando {done} de {total} arquivo(s)..."
            )

        if not self.stop_event.is_set():
            self.update_progress(total, total, f"Processamento concluído. {total} arquivo(s) verificado(s).")
            self.log("Ciclo de processamento concluído.")

    def upload_file(self, file_path):
        url = self.build_upload_url()
        headers = self.get_headers()
        verify_ssl = self.verify_ssl_var.get()
        company_id = self.company_id_entry.get().strip() or "-"

        self.log(f"Enviando arquivo: {file_path}")

        try:
            with open(file_path, "rb") as f:
                files = {"file": (os.path.basename(file_path), f, "application/xml")}
                data = {"company_id": company_id}

                response = requests.post(
                    url,
                    headers=headers,
                    files=files,
                    data=data,
                    timeout=60,
                    verify=verify_ssl
                )

            status_code = response.status_code
            response_text = (response.text or "").strip().replace("\n", " ")

            if 200 <= status_code < 300:
                self.log(f"Arquivo enviado com sucesso: {os.path.basename(file_path)} | HTTP {status_code}")
                self.add_table_row(
                    os.path.basename(file_path),
                    company_id,
                    "SUCESSO",
                    status_code,
                    "Enviado com sucesso"
                )

                if self.move_sent_var.get():
                    self.move_file_to_subfolder(file_path, self.sent_folder_entry.get().strip() or "enviados")

                return True

            self.log(f"Falha no envio: {os.path.basename(file_path)} | HTTP {status_code} | {response_text[:250]}")
            self.add_table_row(
                os.path.basename(file_path),
                company_id,
                "ERRO",
                status_code,
                response_text[:120] or "Falha no envio"
            )
            self.move_file_to_subfolder(file_path, self.error_folder_entry.get().strip() or "erros")
            return False

        except Exception as e:
            self.log(f"Erro ao enviar {os.path.basename(file_path)}: {e}")
            self.add_table_row(
                os.path.basename(file_path),
                company_id,
                "ERRO",
                "-",
                str(e)[:120]
            )
            self.move_file_to_subfolder(file_path, self.error_folder_entry.get().strip() or "erros")
            return False

    def move_file_to_subfolder(self, file_path, subfolder_name):
        try:
            parent_dir = os.path.dirname(file_path)
            target_dir = os.path.join(parent_dir, subfolder_name)
            os.makedirs(target_dir, exist_ok=True)

            base_name = os.path.basename(file_path)
            target_path = os.path.join(target_dir, base_name)

            if os.path.exists(target_path):
                name, ext = os.path.splitext(base_name)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                target_path = os.path.join(target_dir, f"{name}_{timestamp}{ext}")

            shutil.move(file_path, target_path)
            self.log(f"Arquivo movido para: {target_path}")
        except Exception as e:
            self.log(f"Erro ao mover arquivo '{file_path}' para '{subfolder_name}': {e}")

    # ---------------------------
    # Tray
    # ---------------------------
    def create_default_tray_image(self):
        img = Image.new("RGBA", (64, 64), (15, 17, 20, 255))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((8, 8, 56, 56), radius=12, fill=(31, 111, 235, 255))
        d.text((18, 16), "VX", fill=(255, 255, 255, 255))
        return img

    def tray_icon_image(self):
        try:
            logo_path = resource_path("icon.ico")
            if os.path.exists(logo_path):
                return Image.open(logo_path)
        except Exception:
            pass
        return self.create_default_tray_image()

    def show_window(self, icon=None, item=None):
        self.after(0, self.deiconify)
        self.after(0, self.lift)
        self.after(0, self.focus_force)

    def hide_window_to_tray(self):
        if not PYSTRAY_AVAILABLE:
            self.withdraw()
            return

        self.withdraw()

        if self.tray_icon:
            return

        def setup_tray():
            image = self.tray_icon_image()
            menu = pystray.Menu(
                pystray.MenuItem("Abrir", self.show_window),
                pystray.MenuItem("Iniciar Monitoramento", lambda icon, item: self.after(0, self.start_monitoring)),
                pystray.MenuItem("Parar Monitoramento", lambda icon, item: self.after(0, self.stop_monitoring)),
                pystray.MenuItem("Sair", self.quit_from_tray)
            )
            self.tray_icon = pystray.Icon("vexper_sistemas", image, "VEXPER SISTEMAS", menu)
            self.tray_icon.run()

        self.tray_thread = threading.Thread(target=setup_tray, daemon=True)
        self.tray_thread.start()

    def quit_from_tray(self, icon=None, item=None):
        try:
            if self.tray_icon:
                self.tray_icon.stop()
        except Exception:
            pass
        self.tray_icon = None
        self.after(0, self.destroy)

    def on_close(self):
        if self.minimize_to_tray_var.get():
            self.hide_window_to_tray()
            self.log("Aplicação minimizada para a bandeja do sistema.")
        else:
            self.destroy()


if __name__ == "__main__":
    show_startup_splash()
    app = SyncAgentApp()
    app.mainloop()