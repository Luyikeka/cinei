"""Tests for cinei.core._parse_month."""
import pytest

from cinei.core import _parse_month


class TestIntegerInputs:
    @pytest.mark.parametrize("m", list(range(1, 13)))
    def test_all_valid_ints(self, m):
        assert _parse_month(m) == m

    @pytest.mark.parametrize("m", [0, 13, -1, 100])
    def test_out_of_range_int_raises(self, m):
        with pytest.raises(ValueError):
            _parse_month(m)


class TestZeroPaddedStrings:
    @pytest.mark.parametrize("s,expected", [
        ("01", 1), ("02", 2), ("09", 9), ("10", 10), ("12", 12),
    ])
    def test_zero_padded(self, s, expected):
        assert _parse_month(s) == expected


class TestPlainStrings:
    @pytest.mark.parametrize("s,expected", [
        ("1", 1), ("2", 2), ("9", 9), ("10", 10), ("12", 12),
    ])
    def test_plain_digit_strings(self, s, expected):
        assert _parse_month(s) == expected


class TestMonthNames:
    @pytest.mark.parametrize("s,expected", [
        ("Jan", 1), ("jan", 1), ("JAN", 1),
        ("Feb", 2), ("Mar", 3), ("Apr", 4),
        ("May", 5), ("Jun", 6), ("Jul", 7),
        ("Aug", 8), ("Sep", 9), ("Oct", 10),
        ("Nov", 11), ("Dec", 12),
    ])
    def test_abbreviations_case_insensitive(self, s, expected):
        assert _parse_month(s) == expected

    @pytest.mark.parametrize("s,expected", [
        ("January", 1), ("february", 2), ("MARCH", 3),
        ("April", 4), ("june", 6), ("December", 12),
    ])
    def test_full_names_case_insensitive(self, s, expected):
        assert _parse_month(s) == expected

    def test_whitespace_stripped(self):
        assert _parse_month("  Jan  ") == 1


class TestInvalidInputs:
    @pytest.mark.parametrize("bad", ["Janu", "13", "0", "xyz", ""])
    def test_unknown_string_raises(self, bad):
        with pytest.raises(ValueError):
            _parse_month(bad)
