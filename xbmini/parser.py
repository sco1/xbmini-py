from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

HEADER_MAP = {
    "Time": "time",
    "Ax": "accel_x",
    "Ay": "accel_y",
    "Az": "accel_z",
    "Gx": "gyro_x",
    "Gy": "gyro_y",
    "Gz": "gyro_z",
    "Qw": "quat_w",
    "Qx": "quat_x",
    "Qy": "quat_y",
    "Qz": "quat_z",
    "Mx": "mag_x",
    "My": "mag_y",
    "Mz": "mag_z",
    "P": "pressure",
    "T": "temperature",
}

VER_SN_RE = re.compile(r"Version,\s+(\d+)[\w\s,]+SN:(\w+)")
EXPECTED_SENSOR_NAMES = {"Accel", "Gyro", "Mag"}


class ParserError(RuntimeError):  # noqa: D101
    ...


class LoggerType(Enum):  # noqa: D101
    HAM_IMU_ALT = "HAM-IMU+alt"


@dataclass
class SensorInfo:  # noqa: D101
    name: str
    sample_rate: int
    sensitivity: int
    full_scale: int
    units: str

    @classmethod
    def from_header_line(cls, header_line: str) -> SensorInfo:
        """
        Parse sensor configuration from the provided header line.

        Sensor headers are assumed to be of the form:
            <name, sample rate, counts per unit, full scale value, units>

        e.g. `"Accel, 225, 1000, 16, g"`
        """
        split_line = [chunk.strip() for chunk in header_line.split(",")]
        name = split_line[0]
        sample_rate = int(split_line[1])
        sensitivity = int(split_line[2])
        full_scale = int(split_line[3])
        units = split_line[4]

        return cls(
            name=name,
            sample_rate=sample_rate,
            sensitivity=sensitivity,
            full_scale=full_scale,
            units=units,
        )


@dataclass
class HeaderInfo:  # noqa: D101
    n_header_lines: int
    logger_type: LoggerType
    firmware_version: int
    serial: str
    sensors: dict[str, SensorInfo]
    header_spec: list[str]


def _map_headers(
    header_line: str,
    header_map: dict[str, str] = HEADER_MAP,
    verbose: bool = True,
) -> list[str]:
    """
    Map comma-separated header shortnames to human-readable values.

    If a value cannot be mapped it will be left as-is. A warning can be optionally printed by
    setting the `verbose` flag.
    """
    header_spec = []
    for shortname in header_line.split(","):
        shortname = shortname.strip()
        mapped_name = header_map.get(shortname, None)
        if mapped_name is None:
            if verbose:
                print(f"Could not map column header '{shortname}' to human-readable value.")

            header_spec.append(shortname)
        else:
            header_spec.append(mapped_name)

    return header_spec


def extract_header(log_filepath: Path, header_prefix: str = ";") -> list[str]:
    """Extract header lines from the provided log file."""
    header_lines = []
    with log_filepath.open("r") as f:
        for line in f:
            if line.startswith(header_prefix):
                header_lines.append(line.lstrip(header_prefix).strip())
            else:
                break

    return header_lines


def parse_header(header_lines: list[str], header_prefix: str = ";") -> HeaderInfo:
    """Parse log file information from the provided header lines."""
    sensor_info = {}
    for line in header_lines:
        if line.startswith("Title"):
            # Expected like "Title, http://www.gcdataconcepts.com, HAM-IMU+alt, MPU9250 BMP280"
            split_line = [chunk.strip() for chunk in line.split(",")]
            logger_type = LoggerType(split_line[2])
            continue

        if line.startswith("Version"):
            try_match = VER_SN_RE.match(line)
            if try_match:
                firmware_version = int(try_match.group(1))
                device_serial = try_match.group(2)
            else:
                raise ParserError("Unexpected formatting of 'Version' header line encountered.")

            continue

        if any(line.startswith(sensor_name) for sensor_name in EXPECTED_SENSOR_NAMES):
            spec = SensorInfo.from_header_line(line)
            sensor_info[spec.name] = spec

    # If we didn't find all of the expected sensors then we should abort here to prevent issues
    # issues downstream
    if not sensor_info:
        raise ParserError("Unable to locate any sensor configuration header lines.")

    key_diff = EXPECTED_SENSOR_NAMES - sensor_info.keys()
    if key_diff:
        raise ParserError(
            f"Unable to locate all expected sensor names. Missing: {', '.join(key_diff)}"
        )

    # Column headers should be the last line, convert these to more readable names
    header_spec = _map_headers(header_lines[-1])

    try:
        header_info = HeaderInfo(
            n_header_lines=len(header_lines),
            logger_type=logger_type,
            firmware_version=firmware_version,
            serial=device_serial,
            sensors=sensor_info,
            header_spec=header_spec,
        )
    except NameError as e:
        missing_varname = re.findall(r"'(\w+)'", str(e))[0]
        raise ParserError(
            f"Unable to locate necessary header information. Missing: '{missing_varname}'"
        )

    return header_info
