"""Tests for cinei.download._normalize_species."""
import pytest

from cinei.download import SPECIES_VARIANTS, _normalize_species


class TestCaseInsensitive:
    @pytest.mark.parametrize("inp,expected", [
        (["CO"],    ["CO"]),
        (["co"],    ["CO"]),
        (["Co"],    ["CO"]),
        (["NOx"],   ["NOX"]),
        (["nox"],   ["NOX"]),
        (["NOX"],   ["NOX"]),
        (["so2"],   ["SO2"]),
        (["SO2"],   ["SO2"]),
    ])
    def test_single_species(self, inp, expected):
        assert _normalize_species(inp) == expected


class TestVariantMapping:
    def test_voc_maps_to_nmvoc(self):
        """'voc' is a variant of NMVOC."""
        assert _normalize_species(["voc"]) == ["NMVOC"]
        assert _normalize_species(["VOC"]) == ["NMVOC"]

    def test_pm25_variants(self):
        """PM2.5 normalizes to PM25."""
        assert _normalize_species(["PM2.5"]) == ["PM25"]
        assert _normalize_species(["pm2.5"]) == ["PM25"]


class TestMultipleSpecies:
    def test_mixed_case_list(self):
        result = _normalize_species(["co", "NOx", "SO2", "nh3"])
        assert result == ["CO", "NOX", "SO2", "NH3"]

    def test_order_preserved(self):
        result = _normalize_species(["NH3", "CO", "SO2"])
        assert result == ["NH3", "CO", "SO2"]


class TestInvalidSpecies:
    def test_unknown_species_raises(self):
        with pytest.raises(ValueError, match="Unrecognized species"):
            _normalize_species(["XYZ"])

    def test_unknown_among_valid_raises(self):
        with pytest.raises(ValueError, match="Unrecognized species"):
            _normalize_species(["CO", "bogus"])


def test_all_canonical_keys_roundtrip():
    """Every canonical key in SPECIES_VARIANTS should normalize to itself."""
    for key in SPECIES_VARIANTS:
        assert _normalize_species([key]) == [key]
