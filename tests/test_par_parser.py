"""Tests for python/stamps/_par.py."""
from __future__ import annotations

from pathlib import Path

import pytest

from stamps._par import parse_par, ParError


def _write(path: Path, content: str, encoding: str = "utf-8") -> Path:
    path.write_bytes(content.encode(encoding))
    return path


def test_parses_azimuth_lines_integer(tmp_path: Path):
    f = _write(tmp_path / "t.par", "azimuth_lines:   1500\n")
    assert parse_par(f)["azimuth_lines"] == 1500
    assert isinstance(parse_par(f)["azimuth_lines"], int)


def test_parses_range_samples_integer(tmp_path: Path):
    f = _write(tmp_path / "t.par", "range_samples: 25000\n")
    assert parse_par(f)["range_samples"] == 25000


def test_parses_scientific_notation(tmp_path: Path):
    f = _write(tmp_path / "t.par", "prf: 1.717e3\n")
    assert parse_par(f)["prf"] == pytest.approx(1717.0)


def test_parses_negative_float(tmp_path: Path):
    f = _write(tmp_path / "t.par", "near_range_slc: -12345.6\n")
    assert parse_par(f)["near_range_slc"] == pytest.approx(-12345.6)


def test_trailing_whitespace_stripped(tmp_path: Path):
    f = _write(tmp_path / "t.par", "azimuth_lines: \t1500   \n")
    assert parse_par(f)["azimuth_lines"] == 1500


def test_crlf_line_endings(tmp_path: Path):
    f = _write(tmp_path / "t.par", "azimuth_lines: 1500\r\n")
    assert parse_par(f)["azimuth_lines"] == 1500


def test_utf8_bom_stripped(tmp_path: Path):
    f = _write(tmp_path / "t.par", "azimuth_lines: 1500\n",
               encoding="utf-8-sig")
    assert parse_par(f)["azimuth_lines"] == 1500


def test_malformed_line_skipped(tmp_path: Path):
    f = _write(tmp_path / "t.par", "not_a_kv\nazimuth_lines: 10\n")
    assert parse_par(f)["azimuth_lines"] == 10


def test_missing_key_raises_keyerror(tmp_path: Path):
    f = _write(tmp_path / "t.par", "other_key: 5\n")
    d = parse_par(f)
    with pytest.raises(KeyError):
        _ = d["azimuth_lines"]


def test_comment_lines_ignored(tmp_path: Path):
    f = _write(tmp_path / "t.par", "# comment\n% also comment\nazimuth_lines: 10\n")
    assert parse_par(f)["azimuth_lines"] == 10


def test_empty_file_returns_empty_dict(tmp_path: Path):
    f = _write(tmp_path / "t.par", "")
    assert parse_par(f) == {}


def test_nonexistent_file_raises(tmp_path: Path):
    with pytest.raises(ParError):
        parse_par(tmp_path / "does_not_exist.par")


def test_duplicate_key_first_wins(tmp_path: Path):
    f = _write(tmp_path / "t.par",
               "azimuth_lines: 10\nazimuth_lines: 20\n")
    assert parse_par(f)["azimuth_lines"] == 10


def test_path_with_spaces(tmp_path: Path):
    d = tmp_path / "my data"
    d.mkdir()
    f = _write(d / "t.par", "azimuth_lines: 42\n")
    assert parse_par(f)["azimuth_lines"] == 42


def test_non_ascii_filename(tmp_path: Path):
    f = _write(tmp_path / "città_2020.par", "azimuth_lines: 7\n")
    assert parse_par(f)["azimuth_lines"] == 7


def test_locale_invariant_decimal_comma(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("LC_NUMERIC", "it_IT.UTF-8")
    f = _write(tmp_path / "t.par", "prf: 1717.5\n")
    assert parse_par(f)["prf"] == pytest.approx(1717.5)
