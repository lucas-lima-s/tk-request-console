from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

_BANNED_PATTERNS = [
    r"e-?deploy",
    r"bkmenuboard",
    r"\brbi\.com\b",
    r"arthur-ferreira",
    r"ldlimaedp",
    r"\bRDC\b",
    r"systools",
    r"mwapp",
    r"ORDERMGR",
    r"TABLEMGR",
    r"NKDSCTRL",
    r"nReports",
    r"ProductionSystem",
    r"hypervisor",
    r"\bHV\b",
    r"Remote HV",
    r"send-hv-message",
    r"0x6f00001",
    r"12583171",
    r"4038066209",
    r"C:[\\/]+Users[\\/]+lucas",
    r"C:[\\/]+Projects[\\/]+EDP",
    r"D:[\\/]+Projects",
    r"drythz",
    r"OneDrive",
    r"APED",
    r"OXAP",
]

_COMBINED = re.compile("|".join(f"(?:{pattern})" for pattern in _BANNED_PATTERNS), re.IGNORECASE)
_TK_JARGON = re.compile(r"TK_[A-Z_]+")

_BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".ico", ".exe"}

_PY2_PATTERNS = [
    (re.compile(r"print [^(]"), "bare print statement"),
    (re.compile(r"\biteritems\b"), "iteritems"),
    (re.compile(r"\bTkinter\b"), "Python 2 Tkinter import"),
    (re.compile(r"from ttk import"), "from ttk import"),
]


def _tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [REPO_ROOT / line for line in result.stdout.splitlines() if line.strip()]


def test_no_banned_references():
    offenders = []
    for path in _tracked_files():
        if path.name == "test_hygiene.py":
            continue
        if path.suffix.lower() in _BINARY_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        match = _COMBINED.search(text)
        if match:
            offenders.append(f"{path}: {match.group(0)!r}")
        jargon_match = _TK_JARGON.search(text)
        if jargon_match:
            offenders.append(f"{path}: {jargon_match.group(0)!r}")
    assert offenders == [], "banned references found:\n" + "\n".join(offenders)


def test_no_python2_syntax():
    src_root = REPO_ROOT / "src"
    offenders = []
    for path in src_root.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        compile(source, str(path), "exec")
        for pattern, description in _PY2_PATTERNS:
            if pattern.search(source):
                offenders.append(f"{path}: {description}")
    assert offenders == [], "Python 2 syntax found:\n" + "\n".join(offenders)
