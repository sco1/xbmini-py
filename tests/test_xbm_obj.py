import datetime as dt
import typing as t
from pathlib import Path

import pandas as pd
import pytest

from xbmini.heading_parser import HeaderInfo
from xbmini.log_parser import GPS_COLS, PRESS_TEMP_COLS, XBMLog, load_log


def test_xbm_from_log(tmp_log: Path) -> None:
    log_obj = XBMLog.from_raw_log_file(tmp_log)
    assert log_obj._is_merged is False


def test_press_temp_split(tmp_log: Path) -> None:
    log_obj = XBMLog.from_raw_log_file(tmp_log)
    assert not (set(log_obj.mpu.columns.values) & set(PRESS_TEMP_COLS))
    assert set(log_obj.press_temp.columns.values) == set(PRESS_TEMP_COLS)


def test_gps_data_split(tmp_log_gps: Path) -> None:
    log_obj = XBMLog.from_raw_log_file(tmp_log_gps)
    assert log_obj.gps is not None
    assert not (set(log_obj.mpu.columns.values) & set(GPS_COLS))
    assert set(log_obj.gps.columns.values) == set(GPS_COLS)


def test_xbm_from_multi(tmp_multi_log: list[Path]) -> None:
    log_obj = XBMLog.from_multi_raw_log(tmp_multi_log)

    check_index = pd.to_timedelta((dt.timedelta(seconds=0.01), dt.timedelta(seconds=0.02)))
    pd.testing.assert_index_equal(log_obj.mpu.index, check_index, check_names=False)

    assert log_obj._is_merged is True


def test_xbm_from_multi_normalized_timestamp(tmp_multi_log: list[Path]) -> None:
    log_obj = XBMLog.from_multi_raw_log(tmp_multi_log, normalize_time=True)

    check_index = pd.to_timedelta((dt.timedelta(seconds=0), dt.timedelta(seconds=0.01)))
    pd.testing.assert_index_equal(log_obj.mpu.index, check_index, check_names=False)

    assert log_obj._is_merged is True


LOG_FILE_DATA_T: t.TypeAlias = tuple[HeaderInfo, pd.DataFrame]


@pytest.fixture
def log_file_data(tmp_log: Path) -> LOG_FILE_DATA_T:
    full_data, header_info = load_log(tmp_log)

    return header_info, full_data


def test_press_alt_conversion(log_file_data: LOG_FILE_DATA_T) -> None:
    log_obj = XBMLog(*log_file_data)

    assert log_obj.press_temp["press_alt_ft"].iloc[0] == pytest.approx(811.67, abs=1e-2)
    assert log_obj.press_temp["press_alt_m"].iloc[0] == pytest.approx(247.40, abs=1e-2)


def test_press_alt_update(log_file_data: LOG_FILE_DATA_T) -> None:
    log_obj = XBMLog(*log_file_data)
    log_obj.ground_pressure = 100_000

    assert log_obj.ground_pressure == 100_000
    assert log_obj.press_temp["press_alt_ft"].iloc[0] == pytest.approx(446.86, abs=1e-2)
    assert log_obj.press_temp["press_alt_m"].iloc[0] == pytest.approx(136.20, abs=1e-2)
