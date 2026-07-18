"""NICO Desktop GUI — no terminal needed."""

from __future__ import annotations

import asyncio
import threading
import tkinter as tk
from tkinter import scrolledtext, font
from typing import Any

try:
    from nico.app import NicoApp
    from nico.config.settings import Settings
except ImportError:
    NicoApp = None
    Settings = None


class NicoGUI:
    """Simple chat window for NICO."""

    def __init__(self) -> None:
        self.app: Any = None
        self.loop = asyncio.new_event_loop()
        self._build_ui()

    def _build_ui(self) -> None:
        self.root = tk.Tk()
        self.root.title("NICO Assistant")
        self.root.geometry("700x500")
        self.root.minsize(400, 300)

        try:
            self.root.iconbitmap("nico.ico")
        except Exception:
            pass

        fnt = font.Font(size=11)

        self.chat_area = scrolledtext.ScrolledText(
            self.root, wrap=tk.WORD, font=fnt, state=tk.DISABLED,
            bg="#1e1e1e", fg="#d4d4d4", insertbackground="white",
        )
        self.chat_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        bottom = tk.Frame(self.root)
        bottom.pack(fill=tk.X, padx=5, pady=(0, 5))

        self.entry = tk.Entry(bottom, font=fnt)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entry.bind("<Return>", self._on_send)

        self.send_btn = tk.Button(bottom, text="Send", command=self._on_send, font=fnt)
        self.send_btn.pack(side=tk.RIGHT, padx=(5, 0))

        self._append("NICO", "Type a message and press Enter.\n")

    def _append(self, sender: str, text: str) -> None:
        self.chat_area.config(state=tk.NORMAL)
        if sender == "NICO":
            self.chat_area.insert(tk.END, f"{text}\n")
        else:
            self.chat_area.insert(tk.END, f"\nYou: {text}\n", "user")
            self.chat_area.tag_config("user", foreground="#6a9955")
        self.chat_area.see(tk.END)
        self.chat_area.config(state=tk.DISABLED)

    def _on_send(self, _event: Any = None) -> None:
        msg = self.entry.get().strip()
        if not msg:
            return
        if msg.lower() in ("exit", "quit"):
            self.root.destroy()
            return
        self.entry.delete(0, tk.END)
        self._append("You", msg)
        self._respond(msg)

    def _respond(self, msg: str) -> None:
        def _run() -> None:
            try:
                future = asyncio.run_coroutine_threadsafe(
                    self._async_respond(msg), self.loop
                )
                future.result(timeout=30)
            except Exception as exc:
                self.root.after(0, self._append, "NICO", f"Error: {exc}")

        threading.Thread(target=_run, daemon=True).start()

    async def _async_respond(self, msg: str) -> None:
        if self.app is None:
            self._init_app()
        try:
            response = await self.app.chat(msg)
            self.root.after(0, self._append, "NICO", response)
        except Exception as exc:
            self.root.after(0, self._append, "NICO", f"Error: {exc}")

    def _init_app(self) -> None:
        try:
            settings = Settings.from_env()
            self.app = NicoApp(settings=settings)
        except Exception as exc:
            self.root.after(0, self._append, "NICO", f"Init error: {exc}")

    def run(self) -> None:
        threading.Thread(target=self._run_loop, daemon=True).start()
        self.root.mainloop()

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()


def main() -> None:
    gui = NicoGUI()
    gui.run()


if __name__ == "__main__":
    main()
