#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube 高画質ダウンローダー(単一ファイル・完全ローカル動作)

必要なもの:
    pip install yt-dlp
    ffmpeg (映像+音声の結合に必要。PATHが通っている必要があります)
        Windows: https://www.gyan.dev/ffmpeg/builds/ からダウンロードしPATHに追加
        Mac:     brew install ffmpeg
        Linux:   sudo apt install ffmpeg  など

起動方法:
    python youtube_downloader.py

このアプリは完全にローカルで動作し、YouTube以外の外部サーバーへは
動画取得のためにのみ接続します(ダウンロード自体はローカルに保存されます)。
"""

import os
import sys
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    import yt_dlp
except ImportError:
    print("yt-dlp がインストールされていません。")
    print("次のコマンドでインストールしてください: pip install yt-dlp")
    sys.exit(1)


def check_ffmpeg() -> bool:
    """ffmpeg がインストールされ、PATHが通っているか確認する"""
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


class DownloaderApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("YouTube,X 高画質ダウンローダー")
        self.root.geometry("640x420")
        self.root.resizable(False, False)

        self.save_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        self.is_downloading = False

        self._build_ui()

        if not check_ffmpeg():
            messagebox.showwarning(
                "ffmpeg が見つかりません",
                "ffmpeg がインストールされていないか、PATHが通っていません。\n"
                "最高画質でダウンロードするには映像と音声の結合にffmpegが必要です。\n\n"
                "Windows: https://www.gyan.dev/ffmpeg/builds/\n"
                "Mac: brew install ffmpeg\n"
                "Linux: sudo apt install ffmpeg",
            )

    # ---------- UI構築 ----------
    def _build_ui(self):
        pad = {"padx": 12, "pady": 6}

        # URL入力
        url_frame = tk.LabelFrame(self.root, text="動画URL", padx=8, pady=8)
        url_frame.pack(fill="x", **pad)
        self.url_var = tk.StringVar()
        tk.Entry(url_frame, textvariable=self.url_var, font=("", 11)).pack(
            fill="x", ipady=4
        )

        # 画質選択
        quality_frame = tk.LabelFrame(self.root, text="画質", padx=8, pady=8)
        quality_frame.pack(fill="x", **pad)
        self.quality_var = tk.StringVar(value="best")
        qualities = [
            ("最高画質(推奨・4K/8K対応)", "best"),
            ("1080p以下", "1080"),
            ("720p以下", "720"),
            ("480p以下", "480"),
            ("音声のみ(MP3)", "audio"),
        ]
        for label, val in qualities:
            tk.Radiobutton(
                quality_frame, text=label, variable=self.quality_var, value=val
            ).pack(anchor="w")

        # 保存先
        save_frame = tk.LabelFrame(self.root, text="保存先フォルダ", padx=8, pady=8)
        save_frame.pack(fill="x", **pad)
        self.save_var = tk.StringVar(value=self.save_dir)
        row = tk.Frame(save_frame)
        row.pack(fill="x")
        tk.Entry(row, textvariable=self.save_var, state="readonly").pack(
            side="left", fill="x", expand=True, ipady=4
        )
        tk.Button(row, text="変更", command=self._choose_dir).pack(
            side="left", padx=(8, 0)
        )

        # ダウンロードボタン
        self.download_btn = tk.Button(
            self.root,
            text="ダウンロード開始",
            font=("", 12, "bold"),
            bg="#c00",
            fg="white",
            command=self._start_download,
        )
        self.download_btn.pack(fill="x", padx=12, pady=(6, 6), ipady=6)

        # 進捗
        self.progress = ttk.Progressbar(self.root, mode="determinate")
        self.progress.pack(fill="x", padx=12, pady=(0, 4))
        self.status_var = tk.StringVar(value="待機中")
        tk.Label(self.root, textvariable=self.status_var, anchor="w").pack(
            fill="x", padx=12
        )

    def _choose_dir(self):
        d = filedialog.askdirectory(initialdir=self.save_dir)
        if d:
            self.save_dir = d
            self.save_var.set(d)

    # ---------- ダウンロード処理 ----------
    def _start_download(self):
        if self.is_downloading:
            return
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("エラー", "動画のURLを入力してください")
            return

        self.is_downloading = True
        self.download_btn.config(state="disabled", text="ダウンロード中...")
        self.progress["value"] = 0
        self.status_var.set("準備中...")

        thread = threading.Thread(target=self._download_worker, args=(url,), daemon=True)
        thread.start()

    def _download_worker(self, url: str):
        quality = self.quality_var.get()

        if quality == "audio":
            fmt = "bestaudio/best"
            postprocessors = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "320",
                }
            ]
            merge_ext = None
        else:
            if quality == "best":
                fmt = "bestvideo+bestaudio/best"
            else:
                fmt = f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]"
            postprocessors = [{"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}]
            merge_ext = "mp4"

        ydl_opts = {
            "format": fmt,
            "outtmpl": os.path.join(self.save_dir, "%(title)s.%(ext)s"),
            "progress_hooks": [self._progress_hook],
            "postprocessors": postprocessors,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
        }
        if merge_ext:
            ydl_opts["merge_output_format"] = merge_ext

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            self.root.after(0, self._on_success)
        except Exception as e:
            self.root.after(0, self._on_error, str(e))

    def _progress_hook(self, d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            downloaded = d.get("downloaded_bytes", 0)
            if total:
                percent = downloaded / total * 100
                self.root.after(0, self._update_progress, percent, d.get("_speed_str", ""))
        elif d["status"] == "finished":
            self.root.after(0, self.status_var.set, "結合処理中(ffmpeg)...")

    def _update_progress(self, percent, speed):
        self.progress["value"] = percent
        self.status_var.set(f"ダウンロード中... {percent:.1f}%  速度: {speed}")

    def _on_success(self):
        self.progress["value"] = 100
        self.status_var.set("完了しました!")
        self.is_downloading = False
        self.download_btn.config(state="normal", text="ダウンロード開始")
        messagebox.showinfo("完了", f"ダウンロードが完了しました。\n保存先: {self.save_dir}")

    def _on_error(self, message):
        self.status_var.set("エラーが発生しました")
        self.is_downloading = False
        self.download_btn.config(state="normal", text="ダウンロード開始")
        messagebox.showerror("エラー", f"ダウンロードに失敗しました:\n{message}")


def main():
    root = tk.Tk()
    DownloaderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
