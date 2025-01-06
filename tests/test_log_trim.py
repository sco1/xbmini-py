from pathlib import Path

import pytest
from polars.testing import assert_frame_equal

from tests.conftest import TRUTH_DF, TRUTH_DF_GPS
from xbmini.log_parser import XBMLog


def test_trim_log_ham_imu(tmp_log_multi_sample: Path) -> None:
    log_df = XBMLog.from_raw_log_file(tmp_log_multi_sample)

    log_df.trim_log(0, 0.01, normalize_time=False)
    # Use the helper method for simplicity, but drop the derived columns before comparing
    joined_df = log_df._full_dataframe
    joined_df = joined_df.drop(("press_alt_m", "press_alt_ft"))

    assert_frame_equal(joined_df, TRUTH_DF, check_column_order=False)


def test_trim_log_ham_imu_normalize_time(tmp_log_multi_sample: Path) -> None:
    log_df = XBMLog.from_raw_log_file(tmp_log_multi_sample)

    log_df.trim_log(0, 0.01, normalize_time=True)

    # Since we already tested the trim data, just check that the time has been normalized
    assert log_df.mpu["time"][0] == pytest.approx(0)
    assert log_df.press_temp["time"][0] == pytest.approx(0)


def test_trim_log_imu_gps(tmp_log_gps_multi_sample: Path) -> None:
    log_df = XBMLog.from_raw_log_file(tmp_log_gps_multi_sample)

    log_df.trim_log(0, 0.1, normalize_time=False)
    # Use the helper method for simplicity, but drop the derived columns before comparing
    joined_df = log_df._full_dataframe
    joined_df = joined_df.drop(("press_alt_m", "press_alt_ft"))

    assert_frame_equal(joined_df, TRUTH_DF_GPS, check_column_order=False)


def test_trim_log_imu_gps_normalize_time(tmp_log_gps_multi_sample: Path) -> None:
    log_df = XBMLog.from_raw_log_file(tmp_log_gps_multi_sample)

    log_df.trim_log(0, 0.1, normalize_time=True)

    # Since we already tested the trim data, just check that the time has been normalized
    assert log_df.mpu["time"][0] == pytest.approx(0)
    assert log_df.press_temp["time"][0] == pytest.approx(0)
    assert log_df.gps["time"][0] == pytest.approx(0)  # type: ignore[index]
