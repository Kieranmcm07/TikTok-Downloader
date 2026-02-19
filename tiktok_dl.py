
"""
Nokky TikTok Downloader (CLI) - WinCleaner-style ANSI UI
Features:
- Video download via yt-dlp (no slideshow)
- Quality selection (Best / 1080p / 720p / 480p / Audio-only)
- Clipboard URL auto-detect (no extra deps; uses tkinter)
- Download history log + viewer
- Auto-open output folder after download + copy save path to clipboard
- Optional yt-dlp updater
- "Stealth mode" theme toggle (grayscale)
- Custom progress line (yt-dlp progress hook)
"""

from __future__ import annotations

import os
import sys
import time
import json
import subprocess
import shutil
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

ESC = "\x1b"
RESET = f"{ESC}[0m"

APP_NAME = "Nokky TikTok Downloader"
APP_VERSION = "1.1.0"

HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "download_history.jsonl")


def enable_windows_ansi() -> None:
    """Enable ANSI escape sequences (24-bit colour) on Windows consoles."""
    if os.name != "nt":
        return
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        h = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(h, ctypes.byref(mode)):
            kernel32.SetConsoleMode(h, mode.value | 0x0004)  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
    except Exception:
        pass


def rgb(r: int, g: int, b: int) -> str:
    return f"{ESC}[38;2;{r};{g};{b}m"


@dataclass
class Theme:
    # Gradient colours
    C_RED: str
    C_51: str
    C_102: str
    C_153: str
    C_204: str
    C_YELLOW: str
    BORDER: str
    BADGE: str
    TEXT: str

    @staticmethod
    def fiery() -> "Theme":
        c_red = rgb(255, 0, 0)
        c_51 = rgb(255, 51, 0)
        c_102 = rgb(255, 102, 0)
        c_153 = rgb(255, 153, 0)
        c_204 = rgb(255, 204, 0)
        c_yellow = rgb(255, 255, 0)
        return Theme(
            C_RED=c_red,
            C_51=c_51,
            C_102=c_102,
            C_153=c_153,
            C_204=c_204,
            C_YELLOW=c_yellow,
            BORDER=c_204,
            BADGE=c_51,
            TEXT=c_102,
        )

    @staticmethod
    def stealth() -> "Theme":
        # Grayscale theme (still 24-bit)
        c1 = rgb(220, 220, 220)
        c2 = rgb(200, 200, 200)
        c3 = rgb(180, 180, 180)
        c4 = rgb(160, 160, 160)
        c5 = rgb(140, 140, 140)
        c6 = rgb(120, 120, 120)
        return Theme(
            C_RED=c1,
            C_51=c2,
            C_102=c3,
            C_153=c4,
            C_204=c5,
            C_YELLOW=c6,
            BORDER=c5,
            BADGE=c4,
            TEXT=c3,
        )


def cls() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def script_dir() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def normalize_path(p: str) -> str:
    """If user types a relative path (like 'Downloads'), resolve it under the script folder."""
    p = p.strip().strip('"')
    if not p:
        return p
    if os.path.isabs(p):
        return os.path.abspath(p)
    return os.path.abspath(os.path.join(script_dir(), p))




def has_ffmpeg() -> bool:
    """Return True if ffmpeg + ffprobe are available on PATH."""
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None

def print_ffmpeg_help(theme: "Theme") -> None:
    print(f"\n{theme.C_RED}  [!] Audio-only requires FFmpeg (ffmpeg + ffprobe).{RESET}")
    print(f"{theme.TEXT}      Install it, then restart the terminal / VS Code.{RESET}\n")
    print(f"{theme.BORDER}      Fastest install (PowerShell):{RESET}")
    print(f"{theme.TEXT}      winget install --id Gyan.FFmpeg{RESET}\n")
    print(f"{theme.BORDER}      Check it works:{RESET}")
    print(f"{theme.TEXT}      ffmpeg -version{RESET}")
    print(f"{theme.TEXT}      ffprobe -version{RESET}\n")

def default_save_dir() -> str:
    base = os.path.join(os.path.expanduser("~"), "TikTok Downloads")
    os.makedirs(base, exist_ok=True)
    return os.path.abspath(base)


def check_deps() -> bool:
    try:
        import yt_dlp  # noqa: F401
        return True
    except Exception:
        return False


def install_deps() -> None:
    print(f"\n  Installing yt-dlp...\n")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-U", "yt-dlp"])
    print("\n  Done.\n")


def update_yt_dlp(theme: Theme) -> None:
    print(f"\n{theme.TEXT}  Updating yt-dlp...{RESET}\n")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-U", "yt-dlp"])
        print(f"\n{theme.C_204}  [+] yt-dlp updated.{RESET}\n")
    except subprocess.CalledProcessError as e:
        print(f"\n{theme.C_RED}  [!] Update failed: {e}{RESET}\n")


def get_clipboard_text() -> Optional[str]:
    """Clipboard read without external deps (tkinter). Returns None on failure."""
    try:
        import tkinter as tk
        r = tk.Tk()
        r.withdraw()
        text = r.clipboard_get()
        r.destroy()
        if isinstance(text, str) and text.strip():
            return text.strip()
    except Exception:
        return None
    return None


def set_clipboard_text(text: str) -> bool:
    """Clipboard write without external deps (tkinter). Returns True on success."""
    try:
        import tkinter as tk
        r = tk.Tk()
        r.withdraw()
        r.clipboard_clear()
        r.clipboard_append(text)
        r.update()
        r.destroy()
        return True
    except Exception:
        return False


def is_tiktok_url(s: str) -> bool:
    s = (s or "").strip().lower()
    return ("tiktok.com" in s) or ("vm.tiktok" in s) or ("vt.tiktok" in s)


def safe_username() -> str:
    return os.environ.get("USERNAME") or os.environ.get("USER") or "User"


def draw_ui(save_dir: str, theme: Theme, status: str, stealth_on: bool) -> None:
    user = safe_username()
    save_dir_abs = os.path.abspath(save_dir)

    cls()
    # Same style as before, with a couple of extra lines + status + stealth indicator
    lines = [
        "",
        # --- ASCII: NOKKY (same as your batch vibe) ---
        f"                                       {theme.C_RED}███╗   ██╗ ██████╗ ██╗  ██╗██╗  ██╗██╗   ██╗{RESET}",
        f"                                       {theme.C_51}████╗  ██║██╔═══██╗██║ ██╔╝██║ ██╔╝╚██╗ ██╔╝{RESET}",
        f"                                       {theme.C_102}██╔██╗ ██║██║   ██║█████╔╝ █████╔╝  ╚████╔╝{RESET}",
        f"                                       {theme.C_153}██║╚██╗██║██║   ██║██╔═██╗ ██╔═██╗   ╚██╔╝{RESET}",
        f"                                       {theme.C_204}██║ ╚████║╚██████╔╝██║  ██╗██║  ██╗   ██║{RESET}",
        f"                                       {theme.C_YELLOW}╚═╝  ╚═══╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝{RESET}",
        "",
        # --- ASCII: TIKTOK DOWNLOADER ---
        f"                                     {theme.C_RED}████████╗██╗██╗  ██╗████████╗ ██████╗ ██╗  ██╗{RESET}",
        f"                                     {theme.C_51}╚══██╔══╝██║██║ ██╔╝╚══██╔══╝██╔═══██╗██║ ██╔╝{RESET}",
        f"                                     {theme.C_102}   ██║   ██║█████╔╝    ██║   ██║   ██║█████╔╝{RESET}",
        f"                                     {theme.C_153}   ██║   ██║██╔═██╗    ██║   ██║   ██║██╔═██╗{RESET}",
        f"                                     {theme.C_204}   ██║   ██║██║  ██╗   ██║   ╚██████╔╝██║  ██╗{RESET}",
        f"                                     {theme.C_YELLOW}   ╚═╝   ╚═╝╚═╝  ╚═╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝{RESET}",
        "",
        f"                 {theme.C_YELLOW}██████╗  ██████╗ ██╗    ██╗███╗   ██╗██╗      ██████╗  █████╗ ██████╗ ███████╗██████╗{RESET}",
        f"                 {theme.C_204}██╔══██╗██╔═══██╗██║    ██║████╗  ██║██║     ██╔═══██╗██╔══██╗██╔══██╗██╔════╝██╔══██╗{RESET}",
        f"                 {theme.C_153}██║  ██║██║   ██║██║ █╗ ██║██╔██╗ ██║██║     ██║   ██║███████║██║  ██║█████╗  ██████╔╝{RESET}",
        f"                 {theme.C_102}██║  ██║██║   ██║██║███╗██║██║╚██╗██║██║     ██║   ██║██╔══██║██║  ██║██╔══╝  ██╔══██╗{RESET}",
        f"                 {theme.C_51}██████╔╝╚██████╔╝╚███╔███╔╝██║ ╚████║███████╗╚██████╔╝██║  ██║██████╔╝███████╗██║  ██║{RESET}",
        f"                 {theme.C_RED}╚═════╝  ╚═════╝  ╚══╝╚══╝ ╚═╝  ╚═══╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚═════╝ ╚══════╝╚═╝  ╚═╝{RESET}",
        "",
        f"                       {theme.BADGE}╔═══════════════════╗    ╔═══════════════════╗    ╔═══════════════════╗{RESET}",
        f"                       {theme.BADGE}║ Created By @Nokky ║    ║ TikTok DL v{APP_VERSION:<6} ║    ║ This Tool Is Free ║{RESET}",
        f"                       {theme.BADGE}╚═══════════════════╝    ╚═══════════════════╝    ╚═══════════════════╝{RESET}",
        "",
        f"                      {theme.TEXT}Welcome to {APP_NAME} {user}!{RESET}",
        f"                      {theme.TEXT}Note: Only download content you have rights to. Educational use only.{RESET}",
        f"                      {theme.TEXT}Status: {status}{RESET}",
        f"                      {theme.TEXT}Theme: {'STEALTH' if stealth_on else 'FIRE'}{RESET}",
        f"                      {theme.BORDER}╔═════════════════════════════════════════════════════════════════════╗{RESET}",
        f"                      {theme.BORDER}║                                                                     ║{RESET}",
        f"                      {theme.BORDER}║                      ╔════════════════════════════════════╗         ║{RESET}",
        f"                      {theme.BORDER}║                      ║ [1] - Download a TikTok video      ║         ║{RESET}",
        f"                      {theme.BORDER}║                      ║ [2] - Change output folder         ║         ║{RESET}",
        f"                      {theme.BORDER}║                      ║ [3] - View download history        ║         ║{RESET}",
        f"                      {theme.BORDER}║                      ║ [4] - Toggle stealth mode          ║         ║{RESET}",
        f"                      {theme.BORDER}║                      ║ [5] - Update yt-dlp                ║         ║{RESET}",
        f"                      {theme.BORDER}║                      ║ [6] - Exit                         ║         ║{RESET}",
        f"                      {theme.BORDER}║                      ╚════════════════════════════════════╝         ║{RESET}",
        f"                      {theme.BORDER}║                                                                     ║{RESET}",
        f"                      {theme.BORDER}╠═════════════════════════════════════════════════════════════════════╝{RESET}",
        f"                      {theme.BORDER}║{RESET}",
        f"                      {theme.BORDER}╠   Output Folder: {save_dir_abs}{RESET}",
        f"                      {theme.BORDER}║{RESET}",
        f"                      {theme.BORDER}╠   Please enter a command: > {RESET}",
    ]
    sys.stdout.write("\n".join(lines))
    sys.stdout.flush()


def choose_quality(theme: Theme) -> str:
    print(f"\n{theme.TEXT}  Choose quality:{RESET}")
    if not has_ffmpeg():
        print(f"{theme.C_RED}  [!] FFmpeg not found — audio-only will fail until you install it.{RESET}")
    print(f"{theme.BORDER}  [1]{RESET} Best (default)")
    print(f"{theme.BORDER}  [2]{RESET} 1080p max")
    print(f"{theme.BORDER}  [3]{RESET} 720p max")
    print(f"{theme.BORDER}  [4]{RESET} 480p max")
    print(f"{theme.BORDER}  [5]{RESET} Audio only (requires FFmpeg)")
    q = input(f"{theme.TEXT}  > {RESET}").strip() or "1"
    return q


def format_for_choice(choice: str) -> str:
    # yt-dlp format selectors
    if choice == "2":
        return "bv*[height<=1080]+ba/b[height<=1080]/best"
    if choice == "3":
        return "bv*[height<=720]+ba/b[height<=720]/best"
    if choice == "4":
        return "bv*[height<=480]+ba/b[height<=480]/best"
    if choice == "5":
        # bestaudio; let yt-dlp pick container. We'll also set postprocessors to extract audio.
        return "bestaudio/best"
    return "bestvideo+bestaudio/best"


def prompt_url(theme: Theme) -> Optional[str]:
    clip = get_clipboard_text()
    if clip and is_tiktok_url(clip):
        print(f"\n{theme.C_204}  Clipboard URL detected:{RESET} {clip}")
        use = input(f"{theme.TEXT}  Use clipboard URL? (Y/n): {RESET}").strip().lower()
        if use in ("", "y", "yes"):
            return clip

    print(f"{theme.TEXT}                      ╠   Paste the TikTok video URL below:{RESET}")
    url = input(f"{theme.TEXT}  > {RESET}").strip()
    if not url:
        return None
    if not is_tiktok_url(url):
        print(f"\n{theme.C_RED}  [!] That doesn't look like a TikTok URL. Try again.{RESET}\n")
        return None
    return url


def log_history(entry: Dict[str, Any]) -> None:
    try:
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def read_history(limit: int = 25) -> List[Dict[str, Any]]:
    if not os.path.exists(HISTORY_FILE):
        return []
    items: List[Dict[str, Any]] = []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    items.append(json.loads(line))
                except Exception:
                    continue
    except Exception:
        return []
    return items[-limit:]


def open_folder(path: str) -> None:
    try:
        if os.name == "nt":
            subprocess.Popen(["explorer", os.path.abspath(path)])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", os.path.abspath(path)])
        else:
            subprocess.Popen(["xdg-open", os.path.abspath(path)])
    except Exception:
        pass


def human_time(ts: float) -> str:
    try:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))
    except Exception:
        return str(ts)


def view_history(theme: Theme) -> None:
    items = read_history(limit=50)
    if not items:
        print(f"\n{theme.TEXT}  No history yet.{RESET}\n")
        return

    print(f"\n{theme.C_204}  Last {len(items)} downloads:{RESET}\n")
    for i, it in enumerate(reversed(items), 1):
        status = it.get("status", "unknown")
        when = human_time(float(it.get("ts", time.time())))
        url = it.get("url", "")
        out = it.get("output", "")
        fmt = it.get("quality", "")
        print(f"{theme.BORDER}  [{i:02d}]{RESET} {when} | {status} | {fmt}")
        print(f"       URL: {url}")
        if out:
            print(f"       OUT: {out}")
        print()

    choice = input(f"{theme.TEXT}  Open output folder of most recent? (y/N): {RESET}").strip().lower()
    if choice in ("y", "yes"):
        most_recent = items[-1]
        out = most_recent.get("output_dir") or most_recent.get("output")
        if out:
            open_folder(os.path.dirname(out) if os.path.isfile(out) else out)


def download_video(url: str, save_dir: str, quality_choice: str, theme: Theme) -> Optional[str]:
    import yt_dlp

    os.makedirs(save_dir, exist_ok=True)

    if quality_choice == "5" and not has_ffmpeg():
        print_ffmpeg_help(theme)
        return None

    chosen_format = format_for_choice(quality_choice)
    quality_label = {
        "1": "Best",
        "2": "Max 1080p",
        "3": "Max 720p",
        "4": "Max 480p",
        "5": "Audio only",
    }.get(quality_choice, "Best")

    last_filename = {"path": None}

    def hook(d: Dict[str, Any]) -> None:
        # Custom progress line
        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes") or 0
            pct = (downloaded / total * 100) if total else 0.0
            spd = d.get("speed") or 0
            eta = d.get("eta") or 0
            sys.stdout.write(
                f"\r{theme.TEXT}  Downloading... {pct:5.1f}% | "
                f"{(spd/1024/1024):.2f} MiB/s | ETA {eta:>3}s{RESET}   "
            )
            sys.stdout.flush()
        elif status == "finished":
            sys.stdout.write(f"\r{theme.C_204}  [+] Download finished. Processing...{RESET}            \n")
            sys.stdout.flush()
        # Track filename if provided
        fn = d.get("filename")
        if fn:
            last_filename["path"] = fn

    opts: Dict[str, Any] = {
        "outtmpl": os.path.join(save_dir, "%(uploader)s_%(id)s.%(ext)s"),
        "format": chosen_format,
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        },
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [hook],
        "noprogress": True,
    }

    # Audio-only extraction
    if quality_choice == "5":
        opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "0",
            }
        ]
        # If ffmpeg isn't available, yt-dlp will error; we'll show it.

    started = time.time()
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

        # Resolve output path
        out_path = last_filename["path"]
        if out_path:
            out_path = os.path.abspath(out_path)

        elapsed = time.time() - started
        print(f"\n{theme.C_204}  [+] Done in {elapsed:.1f}s.{RESET}")
        if out_path:
            print(f"{theme.C_204}  [+] Saved file:{RESET} {out_path}")
        print(f"{theme.C_204}  [+] Output folder:{RESET} {os.path.abspath(save_dir)}\n")

        log_history({
            "ts": time.time(),
            "url": url,
            "status": "success",
            "quality": quality_label,
            "output": out_path or "",
            "output_dir": os.path.abspath(save_dir),
        })

        # Copy path to clipboard (file if known, else dir)
        to_copy = out_path or os.path.abspath(save_dir)
        if set_clipboard_text(to_copy):
            print(f"{theme.TEXT}  (Copied to clipboard) {to_copy}{RESET}\n")

        # Auto-open folder
        open_folder(os.path.abspath(save_dir))
        return out_path

    except Exception as e:
        print(f"\n{theme.C_RED}  [!] Download failed: {e}{RESET}\n")
        print(f"{theme.TEXT}      Tip: Make sure the URL is correct and the account is public.{RESET}\n")
        log_history({
            "ts": time.time(),
            "url": url,
            "status": "failed",
            "quality": quality_label,
            "error": str(e),
            "output": "",
            "output_dir": os.path.abspath(save_dir),
        })
        return None


def change_folder(current: str, theme: Theme) -> str:
    print(f"\n{theme.TEXT}  Current folder:{RESET} {theme.C_204}{os.path.abspath(current)}{RESET}")
    new = input(f"{theme.TEXT}  Enter new folder path (or press Enter to keep current): {RESET}").strip()
    if not new:
        return current
    new_norm = normalize_path(new)
    os.makedirs(new_norm, exist_ok=True)
    print(f"\n{theme.C_204}  [+] Output folder set to:{RESET} {new_norm}\n")
    return new_norm


def main() -> None:
    enable_windows_ansi()

    if not check_deps():
        install_deps()

    save_dir = default_save_dir()
    stealth_on = False
    theme = Theme.fiery()
    status = "Ready"

    while True:
        draw_ui(save_dir, theme, status=status, stealth_on=stealth_on)
        choice = input().strip()

        if choice == "1":
            status = "Selecting URL"
            url = prompt_url(theme)
            if url:
                status = "Selecting quality"
                q = choose_quality(theme)
                status = "Downloading"
                download_video(url, save_dir, q, theme)
                status = "Ready"
            input(f"{theme.TEXT}  Press Enter to return to menu...{RESET}")

        elif choice == "2":
            status = "Changing folder"
            save_dir = change_folder(save_dir, theme)
            status = "Ready"
            input(f"{theme.TEXT}  Press Enter to return to menu...{RESET}")

        elif choice == "3":
            status = "Viewing history"
            view_history(theme)
            status = "Ready"
            input(f"{theme.TEXT}  Press Enter to return to menu...{RESET}")

        elif choice == "4":
            stealth_on = not stealth_on
            theme = Theme.stealth() if stealth_on else Theme.fiery()
            status = "Theme toggled"
            time.sleep(0.25)
            status = "Ready"

        elif choice == "5":
            status = "Updating yt-dlp"
            update_yt_dlp(theme)
            status = "Ready"
            input(f"{theme.TEXT}  Press Enter to return to menu...{RESET}")

        elif choice == "6":
            print(f"\n{theme.TEXT}  Later!{RESET}\n")
            break

        else:
            status = "Invalid option"
            print(f"\n{theme.C_RED}  [!] Invalid option. Pick 1-6.{RESET}\n")
            input(f"{theme.TEXT}  Press Enter to continue...{RESET}")
            status = "Ready"


if __name__ == "__main__":
    main()
