from __future__ import annotations

import sys


def test_app_module_imports_headless():
    sys.modules.pop("tk_request_console.app", None)
    import tk_request_console.app as app_module

    assert hasattr(app_module, "RequestConsole")
    assert hasattr(app_module, "build_root")
