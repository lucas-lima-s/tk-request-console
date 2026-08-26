from __future__ import annotations

import contextlib
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from tk_request_console.client import Response, send_request
from tk_request_console.config import AppConfig, load_config
from tk_request_console.directory import fetch_hosts
from tk_request_console.errors import AppError
from tk_request_console.profiles import Profile, load_profile, save_profile
from tk_request_console.protocol import RequestSpec, build_url, normalize_token, render_response
from tk_request_console.widgets import AutocompleteEntry


class RequestConsole(ttk.Frame):
    def __init__(
        self,
        master: tk.Misc,
        cfg: AppConfig,
        *,
        config_path: Path | None = None,
    ) -> None:
        super().__init__(master, padding=10)
        self.cfg = cfg
        self.config_path = config_path
        self._hosts_by_label: dict[str, str] = {}

        self.host_var = tk.StringVar(value=cfg.endpoint.default_host)
        self.port_var = tk.StringVar(value=str(cfg.endpoint.default_port))
        self.group_var = tk.StringVar()
        self.action_var = tk.StringVar()
        self.token_var = tk.StringVar()
        self.format_var = tk.StringVar(value=next(iter(cfg.endpoint.format_codes), ""))
        self.timeout_var = tk.StringVar(value="-1")
        self.base64_var = tk.BooleanVar(value=False)
        self.escapes_var = tk.BooleanVar(value=False)
        self.copy_response_var = tk.BooleanVar(value=True)
        self.url_preview_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="Ready")

        self._build_widgets()
        self._wire_events()
        self._update_url_preview()
        self._load_hosts_async()

    def _build_widgets(self) -> None:
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=2)
        self.rowconfigure(12, weight=1)

        labels = self.cfg.labels

        ttk.Label(self, text=f"{labels.host}:").grid(row=0, column=0, sticky="e")
        self.host_entry = AutocompleteEntry(
            self, textvariable=self.host_var, on_select=self._on_host_selected
        )
        self.host_entry.grid(row=0, column=1, sticky="ew")

        ttk.Label(self, text="Port:").grid(row=1, column=0, sticky="e")
        ttk.Entry(self, textvariable=self.port_var).grid(row=1, column=1, sticky="ew")

        ttk.Label(self, text=f"{labels.group}:").grid(row=2, column=0, sticky="e")
        ttk.Entry(self, textvariable=self.group_var).grid(row=2, column=1, sticky="ew")

        ttk.Label(self, text=f"{labels.action}:").grid(row=3, column=0, sticky="e")
        ttk.Entry(self, textvariable=self.action_var).grid(row=3, column=1, sticky="ew")

        ttk.Label(self, text=f"{labels.token}:").grid(row=4, column=0, sticky="e")
        ttk.Entry(self, textvariable=self.token_var).grid(row=4, column=1, sticky="ew")

        ttk.Label(self, text=f"{labels.fmt}:").grid(row=5, column=0, sticky="e")
        ttk.Combobox(
            self,
            textvariable=self.format_var,
            values=list(self.cfg.endpoint.format_codes),
            state="readonly",
        ).grid(row=5, column=1, sticky="ew")

        ttk.Label(self, text=labels.timeout).grid(row=6, column=0, sticky="e")
        int_validator = (self.register(self._validate_int), "%P")
        ttk.Entry(
            self,
            textvariable=self.timeout_var,
            validate="key",
            validatecommand=int_validator,
        ).grid(row=6, column=1, sticky="ew")

        options = ttk.Frame(self)
        options.grid(row=7, column=0, columnspan=2, sticky="w")
        ttk.Checkbutton(options, text="Base64 encode", variable=self.base64_var).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Checkbutton(options, text="Interpret escapes", variable=self.escapes_var).grid(
            row=1, column=0, sticky="w"
        )
        ttk.Checkbutton(
            options, text="Copy response to clipboard", variable=self.copy_response_var
        ).grid(row=2, column=0, sticky="w")

        ttk.Label(self, text="Payload:").grid(row=0, column=2, sticky="nw")
        self.payload_text = tk.Text(self, width=50, height=12, font=("Consolas", 10))
        self.payload_text.grid(row=0, column=2, rowspan=7, sticky="nsew")

        ttk.Label(self, text="URL preview:").grid(row=8, column=0, sticky="e")
        ttk.Entry(self, textvariable=self.url_preview_var, state="readonly").grid(
            row=8, column=1, columnspan=2, sticky="ew"
        )

        self.send_button = ttk.Button(self, text="Send (Ctrl+S)", command=self.send)
        self.send_button.grid(row=9, column=0, columnspan=3, sticky="ew", pady=5)

        status_bar = ttk.Label(self, textvariable=self.status_var, anchor="w", relief="sunken")
        status_bar.grid(row=10, column=0, columnspan=3, sticky="ew")

        ttk.Label(self, text="Response:").grid(row=11, column=0, columnspan=3, sticky="w")
        self.response_text = tk.Text(
            self, width=80, height=10, state="disabled", font=("Consolas", 10)
        )
        self.response_text.grid(row=12, column=0, columnspan=3, sticky="nsew")

        copy_button = ttk.Button(self, text="Copy response", command=self._copy_response)
        copy_button.grid(row=13, column=0, columnspan=3, sticky="e")

        self._build_menu()

    def _build_menu(self) -> None:
        root = self.winfo_toplevel()
        menubar = tk.Menu(root)

        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label="Open profile...", command=self._open_profile)
        file_menu.add_command(label="Save profile as...", command=self._save_profile_as)
        file_menu.add_command(label="Reload config", command=self._reload_config)
        file_menu.add_separator()
        file_menu.add_command(label="Quit", command=root.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(label="About", command=self._show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        with contextlib.suppress(tk.TclError):
            root.config(menu=menubar)

    def _wire_events(self) -> None:
        for var in (
            self.host_var,
            self.port_var,
            self.group_var,
            self.action_var,
            self.token_var,
            self.format_var,
            self.timeout_var,
        ):
            var.trace_add("write", lambda *_args: self._update_url_preview())
        for var in (self.base64_var, self.escapes_var):
            var.trace_add("write", lambda *_args: self._update_url_preview())
        self.winfo_toplevel().bind("<Control-s>", lambda _event: self.send())

    @staticmethod
    def _validate_int(new_value: str) -> bool:
        if new_value in ("", "-"):
            return True
        try:
            int(new_value)
            return True
        except ValueError:
            return False

    def _current_spec(self) -> RequestSpec | None:
        try:
            port = int(self.port_var.get())
            timeout = int(self.timeout_var.get() or "-1")
        except ValueError:
            return None
        return RequestSpec(
            host=self.host_var.get(),
            port=port,
            group=self.group_var.get(),
            action=self.action_var.get(),
            token=self.token_var.get(),
            fmt=self.format_var.get(),
            timeout=timeout,
            base64_encode=bool(self.base64_var.get()),
            interpret_escapes=bool(self.escapes_var.get()),
            payload=self.payload_text.get("1.0", "end").rstrip("\n"),
        )

    def _update_url_preview(self) -> None:
        spec = self._current_spec()
        if spec is None:
            self.url_preview_var.set("(invalid input)")
            return
        try:
            url = build_url(self.cfg.endpoint, spec)
        except AppError as exc:
            self.url_preview_var.set(f"(error: {exc})")
            return
        self.url_preview_var.set(self._mask_token(url, spec))

    def _mask_token(self, url: str, spec: RequestSpec) -> str:
        token = normalize_token(spec.token, self.cfg.endpoint.token_mode)
        if token in (None, ""):
            return url
        return url.replace(str(token), "***", 1)

    def send(self) -> None:
        spec = self._current_spec()
        if spec is None:
            messagebox.showerror("Invalid input", "Port and timeout must be integers.")
            return
        self.send_button.config(state="disabled")
        self.status_var.set("Sending...")

        def worker() -> None:
            try:
                response = send_request(self.cfg, spec)
            except AppError as exc:
                self.after(0, self._on_failure, exc)
                return
            self.after(0, self._on_success, response)

        threading.Thread(target=worker, daemon=True).start()

    def _on_success(self, response: Response) -> None:
        rendered = render_response(response.text)
        self._set_response(rendered)
        byte_count = len(response.text.encode("utf-8"))
        self.status_var.set(
            f"{response.status_code} - {response.elapsed_ms:.0f} ms - {byte_count} bytes"
        )
        if self.copy_response_var.get():
            self.clipboard_clear()
            self.clipboard_append(rendered)
        self.send_button.config(state="normal")

    def _on_failure(self, exc: Exception) -> None:
        self._set_response(f"ERROR: {exc}")
        self.status_var.set("Error")
        self.send_button.config(state="normal")

    def _set_response(self, text: str) -> None:
        self.response_text.config(state="normal")
        self.response_text.delete("1.0", "end")
        self.response_text.insert("1.0", text)
        self.response_text.config(state="disabled")

    def _copy_response(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self.response_text.get("1.0", "end").rstrip("\n"))

    def _on_host_selected(self, value: str) -> None:
        host = self._hosts_by_label.get(value)
        if host is not None:
            self.host_var.set(host)
        self._update_url_preview()

    def _load_hosts_async(self) -> None:
        if not self.cfg.directory.enabled:
            return

        def worker() -> None:
            entries = fetch_hosts(self.cfg)
            labels = [entry.label for entry in entries]
            hosts_by_label = {entry.label: entry.host for entry in entries}
            self.after(0, self._apply_hosts, labels, hosts_by_label)

        threading.Thread(target=worker, daemon=True).start()

    def _apply_hosts(self, labels: list[str], hosts_by_label: dict[str, str]) -> None:
        self._hosts_by_label = hosts_by_label
        self.host_entry.values = labels

    def _open_profile(self) -> None:
        path = filedialog.askopenfilename(
            initialdir=self.cfg.profiles_dir, filetypes=[("JSON", "*.json")]
        )
        if not path:
            return
        try:
            profile = load_profile(Path(path))
        except AppError as exc:
            messagebox.showerror("Profile error", str(exc))
            return
        self.apply_profile(profile)

    def apply_profile(self, profile: Profile) -> None:
        self.host_var.set(profile.host)
        self.port_var.set(str(profile.port))
        self.group_var.set(profile.group)
        self.action_var.set(profile.action)
        self.token_var.set(profile.token)
        self.format_var.set(profile.fmt)
        self.timeout_var.set(str(profile.timeout))
        self.base64_var.set(profile.base64_encode)
        self.escapes_var.set(profile.interpret_escapes)
        self.payload_text.delete("1.0", "end")
        self.payload_text.insert("1.0", profile.payload)
        self._update_url_preview()

    def _save_profile_as(self) -> None:
        spec = self._current_spec()
        if spec is None:
            messagebox.showerror("Invalid input", "Port and timeout must be integers.")
            return
        path = filedialog.asksaveasfilename(
            initialdir=self.cfg.profiles_dir,
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
        )
        if not path:
            return
        profile = Profile(
            name=Path(path).stem,
            description="",
            host=spec.host,
            port=spec.port,
            group=spec.group,
            action=spec.action,
            token=spec.token,
            fmt=spec.fmt,
            timeout=spec.timeout,
            base64_encode=spec.base64_encode,
            interpret_escapes=spec.interpret_escapes,
            payload=spec.payload,
        )
        save_profile(Path(path), profile)

    def _reload_config(self) -> None:
        try:
            self.cfg = load_config(self.config_path)
        except AppError as exc:
            messagebox.showerror("Config error", str(exc))
            return
        self._update_url_preview()

    def _show_about(self) -> None:
        messagebox.showinfo("About", "tk-request-console\nA config-driven HTTP request console.")


def build_root(
    cfg: AppConfig,
    *,
    config_path: Path | None = None,
    profile: Profile | None = None,
) -> tk.Tk:
    root = tk.Tk()
    root.title("tk-request-console")
    console = RequestConsole(root, cfg, config_path=config_path)
    console.grid(row=0, column=0, sticky="nsew")
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    if profile is not None:
        console.apply_profile(profile)
    return root


def main_gui(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="tk-request-console")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--profile", type=Path, default=None)
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    profile = load_profile(args.profile) if args.profile else None
    root = build_root(cfg, config_path=args.config, profile=profile)
    root.mainloop()
    return 0
