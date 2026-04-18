"""Tests for cinei.preprocess.check_user_data."""
import pytest

from cinei.preprocess import CINEI_STANDARD, check_user_data


class TestNetCDFDiagnosis:
    def test_valid_file_returns_report(self, synthetic_nc):
        report = check_user_data(str(synthetic_nc))
        assert isinstance(report, dict)
        assert set(report.keys()) == {"status", "issues", "suggestions", "info"}
        assert report["status"] in {"ok", "warning"}

    def test_valid_file_reports_expected_dims(self, synthetic_nc):
        report = check_user_data(str(synthetic_nc))
        info_dims = report["info"]["dims"]
        assert "month" in info_dims
        assert "lat" in info_dims
        assert "lon" in info_dims

    def test_file_with_unrecognized_variables_warns(
        self, synthetic_nc_missing_sectors
    ):
        report = check_user_data(str(synthetic_nc_missing_sectors))
        assert report["status"] in {"warning", "error"}
        assert any("Unrecognized" in issue or "Missing" in issue
                   for issue in report["issues"])


class TestFileTypeHandling:
    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            check_user_data(str(tmp_path / "nonexistent.nc"))

    def test_unknown_extension_raises(self, tmp_path):
        bogus = tmp_path / "something.xyz"
        bogus.write_text("not a real file")
        with pytest.raises(ValueError, match="Cannot detect file type"):
            check_user_data(str(bogus))


def test_cinei_standard_is_consistent():
    """The standard definition should declare 9 sector variables (8 + sum)."""
    assert "sum" in CINEI_STANDARD["sectors"]
    assert len(CINEI_STANDARD["sectors"]) == 9
    assert CINEI_STANDARD["dims"] == ("month", "lat", "lon")
