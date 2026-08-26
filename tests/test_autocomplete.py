from __future__ import annotations

import time
import tkinter as tk

import pytest

from tk_request_console.widgets import AutocompleteEntry

pytestmark = pytest.mark.gui


def _create_tk(attempts: int = 3) -> tk.Tk:
    last_error: tk.TclError | None = None
    for attempt in range(attempts):
        try:
            return tk.Tk()
        except tk.TclError as exc:
            last_error = exc
            if attempt < attempts - 1:
                time.sleep(0.2)
    raise last_error


@pytest.fixture(scope="module")
def _tk_root():
    window = _create_tk()
    window.withdraw()
    yield window
    window.destroy()


@pytest.fixture
def root(_tk_root):
    yield _tk_root
    for child in list(_tk_root.winfo_children()):
        child.destroy()


def test_autocomplete_filters_case_insensitive(root):
    entry = AutocompleteEntry(root, values=["Alpha", "beta", "Gamma"])
    entry.pack()
    root.update()

    matches = entry._matches("AL")
    assert matches == ["Alpha"]

    matches = entry._matches("BET")
    assert matches == ["beta"]


def test_autocomplete_prefix_matches_first(root):
    entry = AutocompleteEntry(root, values=["beta", "alphabet", "alpha"])
    entry.pack()
    root.update()

    matches = entry._matches("alpha")
    assert matches == ["alphabet", "alpha"]


def test_autocomplete_keyboard_navigation(root):
    entry = AutocompleteEntry(root, values=["one", "two", "three"])
    entry.pack()
    root.update()

    entry._variable.set("t")
    root.update()
    assert entry._listbox is not None
    assert list(entry._listbox.get(0, tk.END)) == ["two", "three"]

    entry._move_selection(1)
    assert entry._listbox.curselection() == (1,)

    entry._move_selection(1)
    assert entry._listbox.curselection() == (0,)

    entry._move_selection(-1)
    assert entry._listbox.curselection() == (1,)


def test_autocomplete_values_setter_repopulates(root):
    entry = AutocompleteEntry(root, values=["one"])
    entry.pack()
    root.update()

    entry._variable.set("o")
    root.update()
    assert list(entry._listbox.get(0, tk.END)) == ["one"]

    entry.values = ["one", "onward"]
    root.update()
    assert list(entry._listbox.get(0, tk.END)) == ["one", "onward"]


def test_autocomplete_selection_sets_variable(root):
    selected = []
    entry = AutocompleteEntry(root, values=["alpha", "beta"], on_select=selected.append)
    entry.pack()
    root.update()

    entry._variable.set("al")
    root.update()
    entry._select("alpha")
    assert entry._variable.get() == "alpha"
    assert selected == ["alpha"]
    assert entry._dropdown is None


def test_autocomplete_closes_when_entry_empties(root):
    entry = AutocompleteEntry(root, values=["alpha", "beta"])
    entry.pack()
    root.update()

    entry._variable.set("al")
    root.update()
    assert entry._dropdown is not None

    entry._variable.set("")
    root.update()
    assert entry._dropdown is None
