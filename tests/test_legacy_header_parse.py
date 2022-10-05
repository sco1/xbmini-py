from xbmini.heading_parser import HeaderInfo, LoggerType, SensorInfo, parse_header

SAMPLE_LEGACY_HEADER = [
    "Title, http://www.gcdataconcepts.com, HAM-IMU+alt, MPU9250 BMP280",
    "Version, 1379, Build date, Jan 12 2018,  SN:ABC122345F0420",
    "Start_time, 2007-02-04, 20:10:53.301",
    "Temperature, -999.00, deg C,  Vbat, 3926, mv",
    "MPU SR, 200,Hz,  Accel sens, 2048,counts/g, Gyro sens, 16,counts/dps,  Mag SR, 10,Hz,  Mag sens, 1666,counts/mT",
    "BMP280 SI, 0.050,s ",
    "Deadband, 0, counts",
    "DeadbandTimeout, 5,sec",
    "Time, P, T",
]

TRUTH_HEADER_INFO = HeaderInfo(
    n_header_lines=9,
    logger_type=LoggerType.HAM_IMU_ALT,
    firmware_version=1379,
    serial="ABC122345F0420",
    sensors={
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
    },
    header_spec=["time", "pressure", "temperature"],
)


def test_legacy_header_parse() -> None:
    assert parse_header(SAMPLE_LEGACY_HEADER) == TRUTH_HEADER_INFO
