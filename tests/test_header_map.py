import pytest

from xbmini.heading_parser import _map_headers

HEADER_MAP = {"f": "foo", "b": "bar"}


def test_header_map_success() -> None:
    header = "f,b"
    assert _map_headers(header, header_map=HEADER_MAP) == ["foo", "bar"]


def test_header_map_missing_key() -> None:
    header = "f,b,c"
    assert _map_headers(header, header_map=HEADER_MAP, verbose=False) == ["foo", "bar", "c"]


def test_header_map_missing_key_verbosity(capfd: pytest.CaptureFixture) -> None:
    header = "f,b,c"
    _ = _map_headers(header, header_map=HEADER_MAP) == ["foo", "bar", "c"]

    captured = capfd.readouterr()
    assert captured.out == "Could not map column header 'c' to human-readable value.\n"
