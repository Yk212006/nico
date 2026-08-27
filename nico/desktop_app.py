from __future__ import annotations

import asyncio
import threading
import tkinter as tk
from tkinter import ttk, font
from typing import Any

from nico.app import NicoApp
from nico.config.settings import Settings


class DesktopChatApp:
    def __init__(self) -> None:
        self.app: NicoApp | None = None
        self.loop = asyncio.new_event_loop()
        self.root = tk.Tk()
        self.root.title("NICO")
        self.root.geometry("900x650")
        self.root.minsize(640, 480)
        self.root.configure(bg="#111318")

        self._build_ui()

    def _build_ui(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        header = tk.Frame(self.root, bg="#151922", height=72)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        title = tk.Label(
            header,
            text="NICO",
            bg="#151922",
            fg="#f5f7fb",
            font=("Segoe UI", 18, "bold"),
        )
        title.pack(anchor="w", padx=18, pady=(14, 0))

        subtitle = tk.Label(
            header,
            text="Local offline chatbot",
            bg="#151922",
            fg="#8d98ab",
            font=("Segoe UI", 10),
        )
        subtitle.pack(anchor="w", padx=18)

        self.status = tk.Label(
            header,
            text="ready",
            bg="#151922",
            fg="#7ee787",
            font=("Segoe UI", 10, "bold"),
        )
        self.status.pack(anchor="e", padx=18, pady=(0, 12))

        body = tk.Frame(self.root, bg="#111318")
        body.pack(fill=tk.BOTH, expand=True, padx=14, pady=14)

        self.chat = tk.Text(
            body,
            wrap=tk.WORD,
            bg="#0e1117",
            fg="#e6edf3",
            insertbackground="#e6edf3",
            relief=tk.FLAT,
            borderwidth=0,
            padx=16,
            pady=16,
            font=("Segoe UI", 11),
            state=tk.DISABLED,
        )
        self.chat.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scroll = ttk.Scrollbar(body, command=self.chat.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.chat.config(yscrollcommand=scroll.set)

        footer = tk.Frame(self.root, bg="#111318")
        footer.pack(fill=tk.X, padx=14, pady=(0, 14))

        self.entry = tk.Entry(
            footer,
            bg="#0e1117",
            fg="#e6edf3",
            insertbackground="#e6edf3",
            relief=tk.FLAT,
            font=("Segoe UI", 11),
        )
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=10, padx=(0, 10))
        self.entry.bind("<Return>", self._send)

        self.send_btn = tk.Button(
            footer,
            text="Send",
            command=self._send,
            bg="#2f81f7",
            fg="white",
            activebackground="#1f6feb",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Segoe UI", 10, "bold"),
            padx=18,
            pady=8,
        )
        self.send_btn.pack(side=tk.RIGHT)

        self._append_system("NICO is ready. Ask anything.")

    def _append(self, speaker: str, text: str) -> None:
        self.chat.configure(state=tk.NORMAL)
        if speaker == "user":
            self.chat.insert(tk.END, f"\nYou\n{text}\n", "user")
        else:
            self.chat.insert(tk.END, f"\nNICO\n{text}\n", "nico")
        self.chat.tag_config("user", foreground="#9cc2ff", spacing1=8, spacing3=10)
        self.chat.tag_config("nico", foreground="#f5f7fb", spacing1=8, spacing3=10)
        self.chat.see(tk.END)
        self.chat.configure(state=tk.DISABLED)

    def _append_system(self, text: str) -> None:
        self.chat.configure(state=tk.NORMAL)
        self.chat.insert(tk.END, f"\n{text}\n", "system")
        self.chat.tag_config("system", foreground="#7ee787", font=("Segoe UI", 10, "italic"))
        self.chat.see(tk.END)
        self.chat.configure(state=tk.DISABLED)

    def _send(self, _event: Any = None) -> None:
        msg = self.entry.get().strip()
        if not msg:
            return
        if msg.lower() in {"exit", "quit"}:
            self.root.destroy()
            return
        self.entry.delete(0, tk.END)
        self._append("user", msg)
        self.send_btn.configure(state=tk.DISABLED)
        self.status.configure(text="thinking...")
        self._respond(msg)

    def _respond(self, msg: str) -> None:
        def runner() -> None:
            try:
                future = asyncio.run_coroutine_threadsafe(self._async_respond(msg), self.loop)
                future.result(timeout=120)
            except Exception as exc:
                self.root.after(0, self._append_system, f"Error: {exc}")
            finally:
                self.root.after(0, lambda: self.send_btn.configure(state=tk.NORMAL))
                self.root.after(0, lambda: self.status.configure(text="ready"))

        threading.Thread(target=runner, daemon=True).start()

    async def _async_respond(self, msg: str) -> None:
        if self.app is None:
            self.app = NicoApp(settings=Settings.from_env())
        response = await self.app.chat(msg)
        self.root.after(0, self._append, "nico", response)

    def run(self) -> None:
        threading.Thread(target=self._loop_runner, daemon=True).start()
        self.root.mainloop()

    def _loop_runner(self) -> None:
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()


def main() -> None:
    DesktopChatApp().run()


if __name__ == "__main__":
    main()
