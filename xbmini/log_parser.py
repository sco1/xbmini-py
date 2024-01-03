from __future__ import annotations

import datetime as dt
import io
import json
import os
import typing as t
from collections import abc
from dataclasses import InitVar, dataclass, field, fields
from pathlib import Path

import pandas as pd

from xbmini.heading_parser import (
    DEFAULT_HEADER_PREFIX,
    HeaderInfo,
    LoggerType,
    ParserError,
    SensorInfo,
    extract_header,
    parse_header,
)

NUMERIC_T: t.TypeAlias = int | float

MINIMUM_SUPPORTED_FIRMWARE = 2108

# Group sensors that require conversions for easier iteration
SENSOR_GROUPS = {
    "Accel": ["accel_x", "accel_y", "accel_z"],
    "Gyro": ["gyro_x", "gyro_y", "gyro_z"],
    "Mag": ["mag_x", "mag_y", "mag_z"],
    "Quat": ["quat_x", "quat_y", "quat_z", "quat_w"],
}
IMU_SENSORS = ("Accel", "Gyro", "Mag")

# Group columns that we may want to look at separately
# Pandas needs these as a list for indexing
PRESS_TEMP_COLS = ["pressure", "temperature", "press_alt_m", "press_alt_ft"]
GPS_COLS = [
    "time_of_week",
    "latitude",
    "longitude",
    "height_ellipsoid",
    "height_msl",
    "hdop",
    "vdop",
    "utc_timestamp",
]

ROLLING_WINDOW_WIDTH = "200ms"

SKIP_STRINGS = ("processed", "trimmed", "combined")

# Until we re-implement sensor parsing, explicitly set the sensor information
DEFAULT_SENS_OVERRIDE = {
    "Accel": SensorInfo(
        name="Accel",
        sample_rate=200,
        sensitivity=2048,
        full_scale=-1,
        units="g",
    ),
    "Gyro": SensorInfo(
        name="Gyro",
        sample_rate=200,
        sensitivity=16,
        full_scale=-1,
        units="dps",
    ),
    "Mag": SensorInfo(
        name="Mag",
        sample_rate=10,
        sensitivity=1666,
        full_scale=-1,
        units="mT",
    ),
}


class HasSensitivity(t.Protocol):  # noqa: D101
    sensitivity: int


def load_log(
    log_filepath: Path,
    sensitivity_override: None | t.Mapping[str, HasSensitivity] = None,
    rolling_window_width: int | str = ROLLING_WINDOW_WIDTH,
) -> tuple[pd.DataFrame, HeaderInfo]:
    """
    Load data from the provided XBM log file.

    Once the raw data is loaded, the following transformations and derivations are performed:
        * Time values are converted to a `pandas.TimedeltaIndex` and used as the `DataFrame` index
            * For IMU-GPS devices, this time value should usually be a valid UTC timestamp & is
            copied to a separate `"utc_timestamp"` column & converted to a datetime
        * For HAM-IMU devices, the accelerometer, gyroscope, and magnetometer data is converted from
        raw counts to their respective units
            * IMU-GPS devices report as actual data values instead of counts so the conversion is
            not required
        * Temperature is converted from mill-degree C to C
        * Quaternions, if present, are converted from raw counts and normalized with RMS
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

    # For IMU-GPS, preserve UTC timestamp as a datetime instance
    if header_info.logger_type is LoggerType.IMU_GPS:
        full_data["utc_timestamp"] = pd.to_datetime(full_data.index, unit="s", utc=True)

    # Convert time index to timedelta so we can use rolling time windows later
    full_data.index = pd.TimedeltaIndex(full_data.index, unit="S")

    # Temperature is always recorded as milli-degree Celsius
    full_data["temperature"] = full_data["temperature"] / 1000

    if header_info.logger_type is not LoggerType.IMU_GPS:
        # Convert measurements from raw counts to measured values
        # IMU-GPS devices do not record in raw counts
        if sensitivity_override:
            sensor_info = sensitivity_override
        else:
            sensor_info = DEFAULT_SENS_OVERRIDE  # Use default until sensor parsing re-implemented

        for sensor in IMU_SENSORS:
            for col in SENSOR_GROUPS[sensor]:
                full_data[col] = full_data[col] / sensor_info[sensor].sensitivity

        # Convert quaternion data, incoming as 16bit values, then normalize with RMS
        # IMU-GPS devices do not log quaternions
        quat_cols = SENSOR_GROUPS["Quat"]
        full_data[quat_cols] = full_data[quat_cols] / 65536
        q_rms = full_data[quat_cols].pow(2).sum(axis=1).pow(1 / 2)
        for col in quat_cols:
            # Not sure what the magic pandas invocation is do do this without a loop
            full_data[col] = full_data[col] / q_rms
    elif header_info.logger_type is LoggerType.IMU_GPS:  # pragma: no branch
        # IMU-GPS devices always record acceleration in milli-gees & gyro in milli-dps
        for col in SENSOR_GROUPS["Accel"]:
            full_data[col] = full_data[col] / 1000

        for col in SENSOR_GROUPS["Gyro"]:
            full_data[col] = full_data[col] / 1000

    # Calculate total acceleration & a rolling average
    full_data["total_accel"] = full_data[SENSOR_GROUPS["Accel"]].pow(2).sum(axis=1).pow(1 / 2)
    full_data["total_accel_rolling"] = (
        full_data["total_accel"].rolling(rolling_window_width, center=True).mean()
    )

    return full_data, header_info


def _split_cols(log_df: pd.DataFrame, columns: t.List[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Split off the specified column(s) into their own dataframe & drop from original.

    The columns are dropped from the incoming `DataFrame`, and the modified dataframe is returned.
    """
    # Only try to index & drop the columns that exist (e.g. press_alt_ft might not exist yet)
    split_cols = log_df[log_df.columns.intersection(columns)].dropna(axis=0)
    log_df = log_df.drop(columns, axis=1, errors="ignore")

    return split_cols, log_df


@dataclass(slots=True)
class XBMLog:  # noqa: D101
    header_info: HeaderInfo
    log_data: InitVar[pd.DataFrame]
    mpu: pd.DataFrame = field(init=False)
    press_temp: pd.DataFrame = field(init=False)
    gps: pd.DataFrame | None = field(init=False)
    drop_date: dt.date | None = None
    drop_location: str | None = None
    drop_id: str | None = None
    _is_merged: bool = False
    _is_trimmed: bool = False

    analysis_dt: dt.datetime = field(default_factory=dt.datetime.now)
    _ground_pressure: NUMERIC_T = 101_325  # Pascals
    total_rigged_weight: None | NUMERIC_T = None

    _serialize_metadata_skip_fields: frozenset[str] = frozenset(
        (
            # Split dataframes are skipped, we concatenate them back together before dumping
            "mpu",
            "press_temp",
            "gps",
            "drop_date",
            "analysis_dt",
            "header_info",
            "_serialize_metadata_skip_fields",
        )
    )

    def __post_init__(self, log_data: pd.DataFrame) -> None:
        # Split out pressure/temperature data & GPS, if available
        press_temp, mpu_data = _split_cols(log_data, columns=PRESS_TEMP_COLS)
        self.press_temp = press_temp

        if self.header_info.logger_type is LoggerType.IMU_GPS:
            gps_data, mpu_data = _split_cols(mpu_data, columns=GPS_COLS)
            self.gps = gps_data
        else:
            self.gps = None

        self.mpu = mpu_data

        # Calculate pressure altitude using the specified ground level pressure
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

    @property
    def _full_dataframe(self) -> pd.DataFrame:
        return pd.concat((self.mpu, self.press_temp, self.gps), axis=1)

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

    def to_csv(self, out_filepath: Path, header_prefix: str = DEFAULT_HEADER_PREFIX) -> None:
        """
        Dump the current class instance into the provided CSV filepath.

        Logger metadata is serialized into JSON and inserted as a single line at the top of the
        file using the provided `header_prefix`. The MPU, pressure/temperature, and GPS dataframes
        are horizontally concatenated and dumped by Pandas as CSV.
        """
        out_filepath.write_text(self._to_string(header_prefix))

    def _to_string(self, header_prefix: str = DEFAULT_HEADER_PREFIX) -> str:
        """
        Dump the current class instance to a string.

        Logger metadata is serialized into JSON and inserted as a single line at the beginning of
        the string using the provided `header_prefix`. The MPU, pressure/temperature, and GPS
        dataframes are horizontally concatenated and dumped by Pandas as CSV.
        """
        full_data = self._full_dataframe
        buff = io.StringIO(newline="")
        buff.write(f"{header_prefix}{self._serialize_metadata()}\n")
        full_data.to_csv(buff)

        return buff.getvalue()

    @classmethod
    def from_raw_log_file(
        cls,
        log_filepath: Path,
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
                    sensitivity_override=sensitivity_override,
                    rolling_window_width=rolling_window_width,
                )[0]
                for log_file in log_filepaths
            ]
        )

        if normalize_time:
            full_data.index = full_data.index - full_data.index[0]

        return cls(
            header_info=header_info,
            log_data=full_data,
            _is_merged=True,
        )

    @classmethod
    def from_processed_csv(
        cls, in_log: Path | io.StringIO, header_prefix: str = DEFAULT_HEADER_PREFIX
    ) -> XBMLog:
        """
        Rebuild a class instance from the provided CSV filepath.

        It is assumed that logger metadata has been serialized into JSON and inserted as a single
        header line at the top of the file using the provided `header_prefix`.
        """
        if isinstance(in_log, Path):
            with in_log.open("r") as f:
                metadata_header = f.readline().lstrip(header_prefix).strip()
                full_data = pd.read_csv(f, index_col=0)
        elif isinstance(in_log, io.StringIO):  # pragma: no branch
            metadata_header = in_log.readline().lstrip(header_prefix).strip()
            full_data = pd.read_csv(in_log, index_col=0)

        full_data.index = pd.TimedeltaIndex(full_data.index)
        metadata = cls._deserialize_metadata(metadata_header)

        return cls(log_data=full_data, **metadata)

    @staticmethod
    def _deserialize_metadata(in_json: str) -> dict:
        """
        Reconstruct the incoming processed XBM log metadata from the provided JSON string.

        Most fields can be loaded as-is, only requiring the following to get additional attention:
            * `drop_date`
            * `analysis_dt`
            * `header_info`
        """
        metadata: dict = json.loads(in_json)
        metadata["drop_date"] = (
            dt.date.fromisoformat(metadata["drop_date"]) if metadata["drop_date"] else None
        )
        metadata["analysis_dt"] = (
            dt.datetime.fromtimestamp(metadata["analysis_dt"]) if metadata["analysis_dt"] else None
        )
        metadata["header_info"] = HeaderInfo.from_raw_dict(metadata["header_info"])

        return metadata


def batch_combine(
    top_dir: Path,
    pattern: str = "*.CSV",
    dry_run: bool = False,
    skip_strs: abc.Collection[str] = SKIP_STRINGS,
) -> None:
    """
    Batch combine raw XBM log files for each logger and dump a serialized `XBMLog` instance to CSV.

    If a filename contains any of the substrings contained in `skip_strs` it will not be included in
    the files to be combined.

    If `dry_run` is specified, a listing of logger directories is printed and no CSV files will be
    generated.

    NOTE: All CSV files in a specific logger's directory are assumed to be from the same session &
    are combined into a single file.

    NOTE: Any pre-existing combined file in a given logger directory will be overwritten.
    """
    log_dirs = {log_file.parent for log_file in top_dir.rglob(pattern)}
    print(f"Found {len(log_dirs)} logger(s) to combine.")

    for log_dir in log_dirs:
        snipped_dir = f"...{os.sep}{os.sep.join(str(log_dir).split(os.sep)[-4:])}"
        out_filepath = log_dir / f"{log_dir.name}_processed.CSV"

        # Filter files using the given skip_strs
        files_to_combine = []
        for file in log_dir.glob(pattern):
            if not any(substr in file.name for substr in skip_strs):
                files_to_combine.append(file)

        if dry_run:
            print(f"Would combine {len(files_to_combine)} log(s) from {snipped_dir}")
            continue

        print(
            f"Combining {len(files_to_combine)} log(s) from {snipped_dir} ... ", end="", flush=True
        )

        try:
            log = XBMLog.from_multi_raw_log(files_to_combine, normalize_time=True)
            log.to_csv(out_filepath)
        except ParserError as e:
            print(f"{e}, skipping logger")
            continue

        print("Done!")
