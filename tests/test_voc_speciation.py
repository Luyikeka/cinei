"""Tests for cinei.voc_speciation.SECTOR_SAMPLE_RANGE completeness."""
from cinei.core import ALL_SECTORS
from cinei.voc_speciation import SECTOR_SAMPLE_RANGE


def test_covers_all_cinei_sectors():
    """Every CINEI sector must have a speciation column range."""
    assert set(SECTOR_SAMPLE_RANGE.keys()) == set(ALL_SECTORS)


def test_ranges_well_formed():
    """Each value must be (start, end) with int start < int end."""
    for sector, rng in SECTOR_SAMPLE_RANGE.items():
        assert isinstance(rng, tuple) and len(rng) == 2, (
            f"{sector}: expected 2-tuple, got {rng}"
        )
        start, end = rng
        assert isinstance(start, int) and isinstance(end, int), (
            f"{sector}: non-int bounds {rng}"
        )
        assert start < end, f"{sector}: start {start} >= end {end}"
        assert start >= 0, f"{sector}: negative start {start}"


def test_no_duplicates():
    """Sector keys should be unique — dict guarantees this, but assert."""
    keys = list(SECTOR_SAMPLE_RANGE.keys())
    assert len(keys) == len(set(keys))
    assert len(keys) == 8
