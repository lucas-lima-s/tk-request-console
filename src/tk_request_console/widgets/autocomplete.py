from __future__ import annotations

import contextlib
import tkinter as tk
from collections.abc import Callable, Sequence
from tkinter import ttk


class AutocompleteEntry(ttk.Entry):
    def __init__(
        self,
        master: tk.Misc | None = None,
        *,
        values: Sequence[str] = (),
        on_select: Callable[[str], None] | None = None,
        max_visible: int = 8,
        **kwargs: object,
    ) -> None:
        self._variable: tk.StringVar = kwargs.pop("textvariable", None) or tk.StringVar()
        kwargs["textvariable"] = self._variable
        super().__init__(master, **kwargs)

        self._values: list[str] = list(values)
        self._on_select = on_select
        self._max_visible = max_visible
        self._dropdown: tk.Toplevel | None = None
        self._listbox: tk.Listbox | None = None
        self._suppress_change = False

        self._variable.trace_add("write", self._on_change)
        self.bind("<Down>", self._on_down)
        self.bind("<Up>", self._on_up)
        self.bind("<Return>", self._on_return)
        self.bind("<Escape>", self._on_escape)
        self.bind("<Tab>", self._on_tab)
        self.bind("<FocusOut>", self._on_focus_out)

    @property
    def values(self) -> list[str]:
        return list(self._values)

    @values.setter
    def values(self, new_values: Sequence[str]) -> None:
        self._values = list(new_values)
        if self._dropdown is not None:
            self._refresh_dropdown()

    def _matches(self, text: str) -> list[str]:
        if not text:
            return []
        needle = text.casefold()
        prefix_matches: list[str] = []
        substring_matches: list[str] = []
        for value in self._values:
            haystack = value.casefold()
            if haystack.startswith(needle):
                prefix_matches.append(value)
            elif needle in haystack:
                substring_matches.append(value)
        return prefix_matches + substring_matches

    def _on_change(self, *_args: object) -> None:
        if self._suppress_change:
            return
        text = self._variable.get()
        if text == "":
            self._close_dropdown()
            return
        matches = self._matches(text)
        if not matches:
            self._close_dropdown()
            return
        self._open_dropdown(matches)

    def _ensure_dropdown(self) -> None:
        if self._dropdown is not None:
            return
        self._dropdown = tk.Toplevel(self)
        self._dropdown.wm_overrideredirect(True)
        with contextlib.suppress(tk.TclError):
            self._dropdown.wm_attributes("-topmost", True)

        frame = ttk.Frame(self._dropdown)
        frame.pack(fill="both", expand=True)
        scrollbar = ttk.Scrollbar(frame, orient="vertical")
        self._listbox = tk.Listbox(
            frame,
            yscrollcommand=scrollbar.set,
            activestyle="dotbox",
            exportselection=False,
        )
        scrollbar.config(command=self._listbox.yview)
        self._listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self._listbox.bind("<ButtonRelease-1>", self._on_click_select)
        self._listbox.bind("<Double-Button-1>", self._on_click_select)

    def _open_dropdown(self, matches: list[str]) -> None:
        self._ensure_dropdown()
        assert self._listbox is not None
        assert self._dropdown is not None

        self._listbox.delete(0, tk.END)
        for value in matches:
            self._listbox.insert(tk.END, value)

        visible_rows = min(len(matches), self._max_visible)
        self._listbox.configure(height=visible_rows)
        self._listbox.selection_clear(0, tk.END)
        self._listbox.selection_set(0)
        self._listbox.activate(0)

        self._position_dropdown()

    def _position_dropdown(self) -> None:
        if self._dropdown is None:
            return
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height()
        width = max(self.winfo_width(), 1)
        self._dropdown.wm_geometry(f"{width}x{self._row_height() * self._max_visible}+{x}+{y}")

    @staticmethod
    def _row_height() -> int:
        return 18

    def _refresh_dropdown(self) -> None:
        text = self._variable.get()
        matches = self._matches(text)
        if matches:
            self._open_dropdown(matches)
        else:
            self._close_dropdown()

    def _close_dropdown(self) -> None:
        if self._dropdown is not None:
            self._dropdown.destroy()
        self._dropdown = None
        self._listbox = None

    def _current_selection(self) -> str | None:
        if self._listbox is None:
            return None
        selection = self._listbox.curselection()
        if not selection:
            return None
        return self._listbox.get(selection[0])

    def _select(self, value: str) -> None:
        self._suppress_change = True
        try:
            self._variable.set(value)
        finally:
            self._suppress_change = False
        self.icursor(tk.END)
        self._close_dropdown()
        if self._on_select is not None:
            self._on_select(value)

    def _on_click_select(self, _event: object) -> None:
        value = self._current_selection()
        if value is not None:
            self._select(value)

    def _on_return(self, _event: object) -> str | None:
        value = self._current_selection()
        if value is not None:
            self._select(value)
            return "break"
        return None

    def _move_selection(self, delta: int) -> None:
        if self._listbox is None:
            return
        size = self._listbox.size()
        if size == 0:
            return
        current = self._listbox.curselection()
        index = current[0] if current else -1
        index = (index + delta) % size
        self._listbox.selection_clear(0, tk.END)
        self._listbox.selection_set(index)
        self._listbox.activate(index)
        self._listbox.see(index)

    def _on_down(self, _event: object) -> str | None:
        if self._dropdown is None:
            return None
        self._move_selection(1)
        return "break"

    def _on_up(self, _event: object) -> str | None:
        if self._dropdown is None:
            return None
        self._move_selection(-1)
        return "break"

    def _on_escape(self, _event: object) -> None:
        self._close_dropdown()

    def _on_tab(self, _event: object) -> None:
        self._close_dropdown()

    def _on_focus_out(self, _event: object) -> None:
        self.after(150, self._close_if_focus_elsewhere)

    def _close_if_focus_elsewhere(self) -> None:
        try:
            focused = self.focus_get()
        except KeyError:
            focused = None
        if focused is self._listbox:
            return
        self._close_dropdown()
