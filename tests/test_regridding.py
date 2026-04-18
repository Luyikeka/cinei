"""Tests for cinei.regridding._regrid_conservative."""
import numpy as np
import pytest

from cinei.regridding import SUPPORTED_RESOLUTIONS, _regrid_conservative


def test_supported_resolutions_sorted():
    assert SUPPORTED_RESOLUTIONS == sorted(SUPPORTED_RESOLUTIONS)
    assert 0.25 in SUPPORTED_RESOLUTIONS


class TestConservation:
    def test_sum_preserved_aggregating_fine_to_coarse(self):
        """
        All 25 source cells at 0.1° fall into the single 0.5° dst cell
        centered at (0.25, 0.25) whose half-window is [0.0, 0.5).
        The sum must be preserved exactly.
        """
        src_res = 0.1
        src_lat = np.arange(0.05, 0.5, src_res)
        src_lon = np.arange(0.05, 0.5, src_res)
        assert len(src_lat) == len(src_lon) == 5

        rng = np.random.default_rng(42)
        data = rng.random((5, 5)).astype(np.float32)

        dst_lat = np.array([0.25], dtype=np.float32)
        dst_lon = np.array([0.25], dtype=np.float32)
        dst_res = 0.5

        out = _regrid_conservative(data, src_lat, src_lon,
                                   dst_lat, dst_lon, dst_res)
        assert out.shape == (1, 1)
        np.testing.assert_allclose(out[0, 0], data.sum(), rtol=1e-5)

    def test_conservation_ratio_near_one_on_larger_grid(self):
        """
        Aggregate a 20×20 source grid at 0.1° into an 8×8 dst grid at 0.25°
        with domains that align (src covers dst fully). Conservation ratio
        = sum(dst) / sum(src) should be ~1.0.
        """
        src_res = 0.1
        dst_res = 0.25

        src_lat = np.arange(0.05, 2.0, src_res)
        src_lon = np.arange(0.05, 2.0, src_res)
        dst_lat = np.arange(dst_res / 2, 2.0, dst_res)
        dst_lon = np.arange(dst_res / 2, 2.0, dst_res)

        rng = np.random.default_rng(0)
        data = rng.random((len(src_lat), len(src_lon))).astype(np.float32)

        out = _regrid_conservative(data, src_lat, src_lon,
                                   dst_lat, dst_lon, dst_res)

        ratio = out.sum() / data.sum()
        assert 0.99 <= ratio <= 1.01, f"conservation ratio {ratio} not ~1.0"

    def test_zero_input_yields_zero_output(self):
        src_lat = np.arange(0.05, 1.0, 0.1)
        src_lon = np.arange(0.05, 1.0, 0.1)
        dst_lat = np.arange(0.125, 1.0, 0.25)
        dst_lon = np.arange(0.125, 1.0, 0.25)

        data = np.zeros((len(src_lat), len(src_lon)), dtype=np.float32)
        out = _regrid_conservative(data, src_lat, src_lon,
                                   dst_lat, dst_lon, 0.25)
        assert np.all(out == 0)

    def test_output_shape(self):
        src_lat = np.arange(0.05, 1.0, 0.1)
        src_lon = np.arange(0.05, 1.0, 0.1)
        dst_lat = np.arange(0.125, 1.0, 0.25)
        dst_lon = np.arange(0.125, 1.0, 0.25)
        data = np.ones((len(src_lat), len(src_lon)), dtype=np.float32)

        out = _regrid_conservative(data, src_lat, src_lon,
                                   dst_lat, dst_lon, 0.25)
        assert out.shape == (len(dst_lat), len(dst_lon))
        assert out.dtype == np.float32
