"""Tests for cinei.regions.get_region_bbox."""
import pytest

from cinei.regions import REGION_PRESETS, get_region_bbox, list_regions


class TestKnownPresets:
    def test_china(self):
        lon_min, lon_max, lat_min, lat_max, name = get_region_bbox(region="China")
        assert (lon_min, lon_max, lat_min, lat_max) == (70.0, 150.0, 10.0, 60.0)
        assert name == "China"

    def test_case_insensitive(self):
        lower = get_region_bbox(region="beijing")
        upper = get_region_bbox(region="BEIJING")
        assert lower[:4] == upper[:4]
        # Returned name is title-cased
        assert lower[4] == "Beijing"

    @pytest.mark.parametrize("region", list(REGION_PRESETS.keys()))
    def test_all_presets_resolve(self, region):
        bbox = get_region_bbox(region=region)
        assert len(bbox) == 5
        lon_min, lon_max, lat_min, lat_max, _ = bbox
        assert lon_min < lon_max
        assert lat_min < lat_max


class TestGlobalDomain:
    def test_global_flag(self):
        assert get_region_bbox(global_domain=True) == (
            -180.0, 180.0, -90.0, 90.0, "global"
        )


class TestManualBbox:
    def test_all_four_provided(self):
        bbox = get_region_bbox(lon_min=100, lon_max=130,
                               lat_min=20, lat_max=45)
        assert bbox[:4] == (100, 130, 20, 45)
        assert "custom" in bbox[4]


class TestDefaultFallback:
    def test_no_args_returns_china(self):
        bbox = get_region_bbox()
        assert bbox[:4] == REGION_PRESETS["china"]


class TestInvalidRegion:
    def test_unknown_region_raises(self):
        with pytest.raises(ValueError, match="not found"):
            get_region_bbox(region="Atlantis")


def test_list_regions_runs(capsys):
    """list_regions() should print without error."""
    list_regions()
    captured = capsys.readouterr()
    assert "China" in captured.out or "china" in captured.out.lower()
