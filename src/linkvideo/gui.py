from __future__ import annotations

import io
import os
import queue
import threading
import tkinter as tk
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .cli import QUALITY_CHOICES, _download_with_ytdlp, _height_limit, _print_xiaohongshu_formats
from .platforms import Platform, detect_platform
from .xiaohongshu import download_xiaohongshu


APP_NAME = "Link Video Downloader"


class QueueWriter(io.TextIOBase):
    def __init__(self, events: queue.Queue[tuple[str, str]]) -> None:
        self.events = events

    def write(self, text: str) -> int:
        if text:
            self.events.put(("log", text))
        return len(text)

    def flush(self) -> None:
        return None


class DownloaderApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.events: queue.Queue[tuple[str, str]] = queue.Queue()
        self.url = tk.StringVar()
        self.output = tk.StringVar(value=str(Path.home() / "Downloads" / "LinkVideoDownloader"))
        self.quality = tk.StringVar(value="best")
        self.codec = tk.StringVar(value="auto")
        self.status = tk.StringVar(value="准备就绪")

        root.title(APP_NAME)
        root.geometry("760x590")
        root.minsize(680, 520)
        root.option_add("*Font", ("Microsoft YaHei UI", 10))
        self._build_ui()
        self.root.after(100, self._poll_events)

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=22)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(7, weight=1)

        ttk.Label(outer, text=APP_NAME, font=("Microsoft YaHei UI", 20, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            outer,
            text="下载公开可访问的小红书、B站和 YouTube 视频",
            foreground="#555555",
        ).grid(row=1, column=0, sticky="w", pady=(2, 18))

        ttk.Label(outer, text="视频链接").grid(row=2, column=0, sticky="w")
        self.url_entry = ttk.Entry(outer, textvariable=self.url)
        self.url_entry.grid(row=3, column=0, sticky="ew", pady=(5, 14))
        self.url_entry.focus_set()

        options = ttk.Frame(outer)
        options.grid(row=4, column=0, sticky="ew")
        options.columnconfigure(1, weight=1)
        options.columnconfigure(3, weight=1)

        ttk.Label(options, text="清晰度").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Combobox(
            options,
            textvariable=self.quality,
            values=QUALITY_CHOICES,
            state="readonly",
            width=12,
        ).grid(row=0, column=1, sticky="w")
        ttk.Label(options, text="编码").grid(row=0, column=2, sticky="w", padx=(28, 8))
        ttk.Combobox(
            options,
            textvariable=self.codec,
            values=("auto", "h264", "hevc"),
            state="readonly",
            width=12,
        ).grid(row=0, column=3, sticky="w")

        ttk.Label(options, text="保存位置").grid(row=1, column=0, sticky="w", pady=(14, 0), padx=(0, 8))
        ttk.Entry(options, textvariable=self.output).grid(
            row=1, column=1, columnspan=2, sticky="ew", pady=(14, 0)
        )
        ttk.Button(options, text="选择…", command=self._choose_output).grid(
            row=1, column=3, sticky="e", pady=(14, 0)
        )

        actions = ttk.Frame(outer)
        actions.grid(row=5, column=0, sticky="ew", pady=18)
        self.download_button = ttk.Button(actions, text="开始下载", command=lambda: self._start(False))
        self.download_button.pack(side="left")
        self.formats_button = ttk.Button(actions, text="查看可用格式", command=lambda: self._start(True))
        self.formats_button.pack(side="left", padx=10)
        ttk.Button(actions, text="打开下载文件夹", command=self._open_output).pack(side="left")
        ttk.Label(actions, textvariable=self.status).pack(side="right")

        ttk.Label(outer, text="运行记录").grid(row=6, column=0, sticky="w")
        log_frame = ttk.Frame(outer)
        log_frame.grid(row=7, column=0, sticky="nsew", pady=(5, 10))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self.log = tk.Text(log_frame, wrap="word", height=12, state="disabled")
        self.log.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(log_frame, command=self.log.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log.configure(yscrollcommand=scrollbar.set)

        ttk.Label(
            outer,
            text="请仅下载你拥有权利或已获授权保存的内容。本工具不绕过 DRM、付费墙或登录限制。",
            foreground="#666666",
            wraplength=700,
        ).grid(row=8, column=0, sticky="w")

    def _choose_output(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.output.get() or str(Path.home()))
        if selected:
            self.output.set(selected)

    def _open_output(self) -> None:
        folder = Path(self.output.get()).expanduser()
        folder.mkdir(parents=True, exist_ok=True)
        os.startfile(folder)  # type: ignore[attr-defined]

    def _append_log(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.configure(state="disabled")

    def _set_running(self, running: bool) -> None:
        state = "disabled" if running else "normal"
        self.download_button.configure(state=state)
        self.formats_button.configure(state=state)
        self.status.set("处理中…" if running else "准备就绪")

    def _start(self, list_only: bool) -> None:
        url = self.url.get().strip()
        if not url:
            messagebox.showwarning(APP_NAME, "请先粘贴视频链接。")
            self.url_entry.focus_set()
            return

        self._set_running(True)
        self._append_log("\n" + ("正在读取可用格式…\n" if list_only else "开始处理下载…\n"))
        output = Path(self.output.get()).expanduser()
        quality = self.quality.get()
        codec = self.codec.get()
        worker = threading.Thread(
            target=self._run_job,
            args=(url, list_only, output, quality, codec),
            daemon=True,
        )
        worker.start()

    def _run_job(
        self,
        url: str,
        list_only: bool,
        output: Path,
        quality: str,
        codec: str,
    ) -> None:
        writer = QueueWriter(self.events)
        try:
            with redirect_stdout(writer), redirect_stderr(writer):
                platform = detect_platform(url)
                print(f"已识别平台：{platform.value}")
                if platform is Platform.XIAOHONGSHU:
                    if list_only:
                        _print_xiaohongshu_formats(url)
                    else:
                        path = download_xiaohongshu(
                            url,
                            output,
                            max_height=_height_limit(quality),
                            codec=codec,
                        )
                        print(f"下载完成：{path}")
                else:
                    _download_with_ytdlp(
                        url,
                        output,
                        quality,
                        codec,
                        None,
                        list_only,
                    )
                    if not list_only:
                        print(f"下载完成：{output}")
            self.events.put(("done", "格式读取完成" if list_only else "视频下载完成"))
        except Exception as exc:
            self.events.put(("log", f"错误：{exc}\n"))
            self.events.put(("error", str(exc)))

    def _poll_events(self) -> None:
        try:
            while True:
                event, value = self.events.get_nowait()
                if event == "log":
                    self._append_log(value)
                elif event == "done":
                    self._set_running(False)
                    messagebox.showinfo(APP_NAME, value)
                elif event == "error":
                    self._set_running(False)
                    messagebox.showerror(APP_NAME, f"操作失败：{value}")
        except queue.Empty:
            pass
        self.root.after(100, self._poll_events)


def main() -> int:
    root = tk.Tk()
    ttk.Style(root)
    DownloaderApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
