from pathlib import Path

from matplotlib_window.window import flexible_window

from xbmini.log_parser import XBMLog


def windowtrim_log_file(
    log_filepath: Path,
    normalize_time: bool = True,
    write_csv: bool = False,
) -> XBMLog:
    """
    Plot the provided log file's pressure altitude vs. elapsed time for interactive windowing.

    If `write_csv` is `True`, a trimmed CSV with a `"_trimmed"` suffix is written to the same
    directory as the input log data. Note that any existing trimmed file with the same name will be
    overwritten.
    """
    log_data = XBMLog.from_raw_log_file(log_filepath)

    xdata = log_data.press_temp["time"]
    ydata = log_data.press_temp["press_alt_ft"]
    l_bound, r_bound = flexible_window(x_data=xdata, y_data=ydata, position=10, window_width=20)

    log_data.trim_log(l_bound, r_bound, normalize_time=normalize_time)

    if write_csv:
        out_filepath = log_filepath.with_stem(f"{log_filepath.stem}_trimmed")
        log_data.to_csv(out_filepath)

    return log_data
