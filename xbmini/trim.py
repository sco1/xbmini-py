from pathlib import Path

from matplotlib_window.window import flexible_window

from xbmini.log_parser import XBMLog


def windowtrim_log_file(log_filepath: Path, write_csv: bool = False) -> XBMLog:
    log_data = XBMLog.from_raw_log_file(log_filepath)

    xdata = log_data.press_temp
