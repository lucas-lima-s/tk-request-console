from __future__ import annotations

import pytest

from tk_request_console.errors import TokenError
from tk_request_console.protocol import bool_literal, format_code, normalize_token


def test_normalize_token_decimal_int():
    assert normalize_token("42") == 42
    assert normalize_token("-7") == -7


def test_normalize_token_hex_uppercased():
    assert normalize_token("0x6f0a1") == "0x6F0A1"
    assert normalize_token("0X6f0a1") == "0x6F0A1"


def test_normalize_token_symbolic_uppercased():
    assert normalize_token("abcDEF") == "ABCDEF"


def test_normalize_token_empty_is_none():
    assert normalize_token("") is None
    assert normalize_token("   ") is None


def test_normalize_token_modes():
    assert normalize_token("abc", mode="upper") == "ABC"
    assert normalize_token("42", mode="int") == 42
    assert normalize_token("a b&c", mode="raw") == "a b&c"
    with pytest.raises(TokenError):
        normalize_token("not-a-number", mode="int")


def test_format_code_known():
    codes = {"text": 0, "json": 1}
    assert format_code("json", codes) == 1


def test_format_code_passthrough_unknown():
    codes = {"text": 0, "json": 1}
    assert format_code("custom", codes) == "custom"


def test_bool_literal_styles():
    assert bool_literal(True, "true_false") == "true"
    assert bool_literal(False, "true_false") == "false"
    assert bool_literal(True, "one_zero") == "1"
    assert bool_literal(False, "one_zero") == "0"
    assert bool_literal(True, "yes_no") == "yes"
    assert bool_literal(False, "yes_no") == "no"
