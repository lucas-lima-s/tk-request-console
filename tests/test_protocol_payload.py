from __future__ import annotations

import base64

from tk_request_console.protocol import encode_payload, render_response


def test_encode_payload_utf8():
    data = encode_payload("héllo", base64_encode=False, interpret_escapes=False)
    assert data == "héllo".encode()


def test_encode_payload_base64():
    data = encode_payload("hello", base64_encode=True, interpret_escapes=False)
    assert data == base64.b64encode(b"hello")


def test_encode_payload_interprets_escapes():
    data = encode_payload(r"a\0b\nc\td", base64_encode=False, interpret_escapes=True)
    assert data == b"a\0b\nc\td"


def test_encode_payload_escapes_off_keeps_literals():
    data = encode_payload(r"a\0b", base64_encode=False, interpret_escapes=False)
    assert data == rb"a\0b"


def test_render_response_control_chars():
    assert render_response("line1\0line2") == "line1\nline2"
    assert render_response("line1\0line2", render_control_chars=False) == "line1\0line2"
