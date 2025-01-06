import typing as t
from pathlib import Path

import polars as pl
import pytest
from polars.testing import assert_series_equal

from xbmini.heading_parser import HeaderInfo
from xbmini.log_parser import GPS_COLS, PRESS_TEMP_COLS, XBMLog, load_log


def test_xbm_from_log(tmp_log: Path) -> None:
    log_obj = XBMLog.from_raw_log_file(tmp_log)
    assert log_obj._is_merged is False


def test_press_temp_split(tmp_log: Path) -> None:
    log_obj = XBMLog.from_raw_log_file(tmp_log)
    assert not (set(log_obj.mpu.columns) & set(PRESS_TEMP_COLS))
    assert set(log_obj.press_temp.columns) == {"time", *PRESS_TEMP_COLS}


def test_gps_data_split(tmp_log_gps: Path) -> None:
    log_obj = XBMLog.from_raw_log_file(tmp_log_gps)
    assert log_obj.gps is not None
    assert not (set(log_obj.mpu.columns) & set(GPS_COLS))
    assert set(log_obj.gps.columns) == {"time", *GPS_COLS}


def test_gps_normalize(tmp_log_gps: Path) -> None:
    log_obj = XBMLog.from_raw_log_file(tmp_log_gps, normalize_gps=True)
    assert log_obj.gps["latitude"][0] == pytest.approx(0)  # type: ignore[index]
    assert log_obj.gps["longitude"][0] == pytest.approx(0)  # type: ignore[index]


def test_xbm_from_multi(tmp_multi_log: list[Path]) -> None:
    log_obj = XBMLog.from_multi_raw_log(tmp_multi_log)

    check_t = pl.Series([0.01, 0.02])
    assert_series_equal(log_obj.mpu["time"], check_t, check_names=False)

    assert log_obj._is_merged is True


def test_xbm_from_multi_normalized_timestamp(tmp_multi_log: list[Path]) -> None:
    log_obj = XBMLog.from_multi_raw_log(tmp_multi_log, normalize_time=True)

    check_t = pl.Series([0.0, 0.01])
    assert_series_equal(log_obj.mpu["time"], check_t, check_names=False)

    assert log_obj._is_merged is True


LOG_FILE_DATA_T: t.TypeAlias = tuple[HeaderInfo, pl.DataFrame]


@pytest.fixture
def log_file_data(tmp_log: Path) -> LOG_FILE_DATA_T:
    full_data, header_info = load_log(tmp_log)

    return header_info, full_data


def test_press_alt_conversion(log_file_data: LOG_FILE_DATA_T) -> None:
    log_obj = XBMLog(*log_file_data)

    assert log_obj.press_temp["press_alt_m"][0] == pytest.approx(247.40, abs=1e-2)
    assert log_obj.press_temp["press_alt_ft"][0] == pytest.approx(811.67, abs=1e-2)


def test_press_alt_update(log_file_data: LOG_FILE_DATA_T) -> None:
    log_obj = XBMLog(*log_file_data)
    log_obj.ground_pressure = 100_000

    assert log_obj.ground_pressure == 100_000
    assert log_obj.press_temp["press_alt_m"][0] == pytest.approx(136.20, abs=1e-2)
    assert log_obj.press_temp["press_alt_ft"][0] == pytest.approx(446.86, abs=1e-2)


def test_get_idx_imu(tmp_log_multi_sample: Path) -> None:
    log_obj = XBMLog.from_raw_log_file(tmp_log_multi_sample, normalize_time=True)

    indices = log_obj._get_idx(0.01)
    assert indices == (1, 1, None)


def test_get_idx_imu_gps(tmp_log_gps_multi_sample: Path) -> None:
    log_obj = XBMLog.from_raw_log_file(tmp_log_gps_multi_sample, normalize_time=True)

    indices = log_obj._get_idx(0.01)
    assert indices == (1, 1, 1)


def test_get_idx_bad_col_raises(tmp_log_multi_sample: Path) -> None:
    log_obj = XBMLog.from_raw_log_file(tmp_log_multi_sample, normalize_time=True)

    with pytest.raises(ValueError, match="does not contain column 'foo'"):
        _ = log_obj._get_idx(0.01, ref_col="foo")
