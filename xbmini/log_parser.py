from __future__ import annotations

import datetime as dt
import json
import typing as t
from dataclasses import dataclass, field, fields
from pathlib import Path

import pandas as pd

from xbmini.heading_parser import HeaderInfo, extract_header, parse_header

NUMERIC_T = int | float

SENSOR_GROUPS = {
    "Accel": ["accel_x", "accel_y", "accel_z"],
    "Gyro": ["gyro_x", "gyro_y", "gyro_z"],
    "Mag": ["mag_x", "mag_y", "mag_z"],
    "Quat": ["quat_x", "quat_y", "quat_z", "quat_w"],
}
IMU_SENSORS = ("Accel", "Gyro", "Mag")

PRESS_TEMP_COLS = ["pressure", "temperature"]  # Pandas needs as a list for indexing

ROLLING_WINDOW_WIDTH = "200ms"


class HasSensitivity(t.Protocol):  # noqa: D101
    sensitivity: int


def load_log(
    log_filepath: Path,
    sensor_groups: dict[str, list[str]] = SENSOR_GROUPS,
    sensitivity_override: None | t.Mapping[str, HasSensitivity] = None,
    rolling_window_width: int | str = ROLLING_WINDOW_WIDTH,
) -> tuple[pd.DataFrame, HeaderInfo]:
    """
    Load data from the provided XBM log file.

    Once the raw data is loaded, the following transformations and derivations are performed:
        * Time values are converted to a `pandas.TimedeltaIndex` and used as the `DataFrame` index
        * Accelerometer, Gyroscope, and Magnetometer data is converted from raw counts to their
        respective units
        * Temperature is converted from mill-degree C to C
        * Quaternions are converted from raw counts and normalized with RMS
        * A `"total_accel"` column is calculated from the vector sum of the acceleration components
        * A `"total_accel_rolling"` column is calculated using a rolling mean of the `"total_accel"`
        values

    `rolling_window_width` may be specified in a format understood by `pandas.DataFrame.rolling`

    To work around known issues with some firmware where the sensor headers do not provide the
    correct counts/unit conversion constant, `sensitivity_override` may be optionally specified to
    manually provide these constants.
    """
    # Could probably combine these 2 steps using the same open file object if performance becomes
    # an issue
    header_info = parse_header(extract_header(log_filepath))
    full_data = pd.read_csv(
        log_filepath,
        skiprows=header_info.n_header_lines,
        header=None,
        names=header_info.header_spec,
        index_col="time",
        comment=";",
    )
    # Convert time index to timedelta so we can use rolling time windows later
    full_data.index = pd.TimedeltaIndex(full_data.index, unit="S")

    # Convert measurements from raw counts to measured values
    if sensitivity_override:
        sensor_info = sensitivity_override
    else:
        sensor_info = header_info.sensors

    for sensor in IMU_SENSORS:
        for column in sensor_groups[sensor]:
            full_data[column] = full_data[column] / sensor_info[sensor].sensitivity

    # Calculate total acceleration & a rolling average
    full_data["total_accel"] = full_data[sensor_groups["Accel"]].pow(2).sum(axis=1).pow(1 / 2)
    full_data["total_accel_rolling"] = (
        full_data["total_accel"].rolling(rolling_window_width, center=True).mean()
    )

    # Convert temperature from mill-degree C to C
    full_data["temperature"] = full_data["temperature"] / 1000

    # Convert quaternion data, incoming as 16bit values, then normalize with RMS
    quat_cols = sensor_groups["Quat"]
    full_data[quat_cols] = full_data[quat_cols] / 65536
    q_rms = full_data[quat_cols].pow(2).sum(axis=1).pow(1 / 2)
    for col in quat_cols:
        # Not sure what the magic pandas invocation is do do this without a loop
        full_data[col] = full_data[col] / q_rms

    return full_data, header_info


def _split_press_temp(
    log_df: pd.DataFrame, columns: t.List[str] = PRESS_TEMP_COLS
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Split off temperature & pressure columns since they sample at a lower rate.

    The columns are dropped from the incoming `DataFrame`, and the modified dataframe is returned.
    """
    press_temp_df = log_df[columns].dropna(axis=0)
    log_df = log_df.drop(columns, axis=1)

    return press_temp_df, log_df


@dataclass(slots=True)
class XBMLog:  # noqa: D101
    mpu: pd.DataFrame
    press_temp: pd.DataFrame
    header_info: HeaderInfo
    drop_date: dt.date | None = None
    drop_location: str | None = None
    drop_id: str | None = None
    _is_merged: bool = False
    _is_trimmed: bool = False
    _is_from_processed: bool = False

    analysis_dt: dt.datetime = field(default_factory=dt.datetime.now)
    _ground_pressure: NUMERIC_T = 101_325  # Pascals
    total_rigged_weight: None | NUMERIC_T = None

    _serialize_metadata_skip_fields: frozenset[str] = frozenset(
        (
            "mpu",
            "press_temp",
            "drop_date",
            "analysis_dt",
            "header_info",
            "_serialize_metadata_skip_fields",
        )
    )

    def __post_init__(self) -> None:
        # Calculate pressure altitude using the specified ground level pressure
        # Skip if we're loading a log that's already been processed
        if not self._is_from_processed:
            self._calculate_pressure_altitude()

    def _calculate_pressure_altitude(self) -> None:
        self.press_temp["press_alt_m"] = 44_330 * (
            1 - (self.press_temp["pressure"] / self.ground_pressure).pow(1 / 5.225)
        )
        self.press_temp["press_alt_ft"] = self.press_temp["press_alt_m"] * 3.2808

    @property
    def logger_id(self) -> str:  # noqa: D102  # pragma: no cover
        return self.header_info.serial

    @property
    def ground_pressure(self) -> NUMERIC_T:  # noqa: D102  # pragma: no cover
        return self._ground_pressure

    @ground_pressure.setter
    def ground_pressure(self, pressure: NUMERIC_T) -> None:
        """Recalculate pressure altitudes if the ground pressure changes."""
        self._ground_pressure = pressure
        self._calculate_pressure_altitude()

    def _serialize_metadata(self) -> str:
        """Dump the instance into a serializable dictionary."""
        # Rather than some complicated instance matching logic, just dump what's serializable first
        # and add in things that need custom handling
        out_dict = {
            _field.name: getattr(self, _field.name)
            for _field in fields(self)
            if _field.name not in self._serialize_metadata_skip_fields
        }

        # Serialize the remainder. _serialize_metadata_skip_fields is ignored
        out_dict["analysis_dt"] = self.analysis_dt.timestamp()
        out_dict["drop_date"] = self.drop_date.isoformat() if self.drop_date else None
        out_dict["header_info"] = self.header_info.to_dict()

        return json.dumps(out_dict)

    def to_csv(self, out_filepath: Path, header_prefix: str = ";") -> None:
        """
        Dump the current class instance into the provided CSV filepath.

        Logger metadata is serialized into JSON and inserted as a single line at the top of the
        file using the provided `header_prefix`. The MPU and Pressure/Temperature dataframes are
        horizontally concatenated and dumped by Pandas as CSV.
        """
        full_data = pd.concat((self.mpu, self.press_temp), axis=1)
        with out_filepath.open("w", newline="") as f:
            f.write(f"{header_prefix}{self._serialize_metadata()}\n")
            full_data.to_csv(f)

    @classmethod
    def from_raw_log_file(
        cls,
        log_filepath: Path,
        sensor_groups: dict[str, list[str]] = SENSOR_GROUPS,
        sensitivity_override: None | t.Mapping[str, HasSensitivity] = None,
        rolling_window_width: int | str = ROLLING_WINDOW_WIDTH,
        normalize_time: bool = False,
    ) -> XBMLog:
        """
        Build a log instance from the provided log file.

        To work around known issues with some firmware where the sensor headers do not provide the
        correct counts/unit conversion constant, `sensitivity_override` may be optionally specified
        to manually provide these constants.

        The `normalize_time` flag may be set to normalize the time index so it starts at 0 seconds,
        helping for cases where the XBM starts at some abnormally large time index.
        """
        # Since we're cheating and using the multi-load method, we have to set the merged flag back
        # to False before returning
        log = cls.from_multi_raw_log(
            log_filepaths=(log_filepath,),
            sensor_groups=sensor_groups,
            sensitivity_override=sensitivity_override,
            rolling_window_width=rolling_window_width,
            normalize_time=normalize_time,
        )
        log._is_merged = False

        return log

    @classmethod
    def from_multi_raw_log(
        cls,
        log_filepaths: t.Sequence[Path],
        sensor_groups: dict[str, list[str]] = SENSOR_GROUPS,
        sensitivity_override: None | t.Mapping[str, HasSensitivity] = None,
        rolling_window_width: int | str = ROLLING_WINDOW_WIDTH,
        normalize_time: bool = False,
    ) -> XBMLog:
        """
        Build a log instance by joining the provided log files.

        It is assumed that all of the provided log files are from the same logging session, so they
        share the same header information and timeseries.

        To work around known issues with some firmware where the sensor headers do not provide the
        correct counts/unit conversion constant, `sensitivity_override` may be optionally specified
        to manually provide these constants.

        The `normalize_time` flag may be set to normalize the time index so it starts at 0 seconds,
        helping for cases where the XBM starts at some abnormally large time index.
        """
        # Grab the header info from the first file so we don't have to worry in the list comp
        header_info = parse_header(extract_header(log_filepaths[0]))
        full_data = pd.concat(
            [
                # Skip the header info since we've already grabbed it
                load_log(
                    log_filepath=log_file,
                    sensor_groups=sensor_groups,
                    sensitivity_override=sensitivity_override,
                    rolling_window_width=rolling_window_width,
                )[0]
                for log_file in log_filepaths
            ]
        )

        if normalize_time:
            full_data.index = full_data.index - full_data.index[0]

        press_temp, mpu_data = _split_press_temp(full_data)

        return cls(
            mpu=mpu_data,
            press_temp=press_temp,
            header_info=header_info,
            _is_merged=True,
        )

    @classmethod
    def from_processed_csv(cls, in_filepath: Path, header_prefix: str = ";") -> XBMLog:
        """
        Rebuild a class instance from the provided CSV filepath.

        It is assumed that logger metadata has been serialized into JSON and inserted as a single
        header line at the top of the file using the provided `header_prefix`.
        """
        raise NotImplementedError


def _deserialize_metadata(in_json: str) -> dict:
    raise NotImplementedError
