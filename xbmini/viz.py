from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from xbmini.log_parser import XBMLog

CD = Path()


def accel_plot(
    *,
    log_data: XBMLog,
    title_base: str,
    out_dir: Path = CD,
    out_file_stem: str,
    accel_range: list[int],
    alt_range: list[int],
    show_altitude: bool = True,
    line_width: int | float = 1.5,
    width: int = 1440,
    height: int = 900,
    show_plot: bool = False,
    write_img: bool = True,
    write_html: bool = False,
    write_pdf: bool = False,
) -> go.Figure:
    """
    Plot `"total_accel_rolling"` vs. time using the data from the provided drop log.

    A plot of `"press_alt_ft"` is also optionally added onto a secondary data axis.
    """
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(
            x=log_data.mpu.index,
            y=log_data.mpu["total_accel_rolling"],
            name="Total Accel",
            line_color="royalblue",
            line_width=line_width,
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=log_data.press_temp.index,
            y=log_data.press_temp["press_alt_ft"],
            name="Pressure Altitude",
            line_color="firebrick",
            line_width=line_width,
            visible=show_altitude,
        ),
        secondary_y=True,
    )

    fig.update_layout(
        title_text=title_base,
        xaxis_title="Elased Time (s)",
        width=width,
        height=height,
    )
    fig.update_yaxes(
        title_text="Total Acceleration, 200ms rolling avg (g)",
        secondary_y=False,
        range=accel_range,
    )
    fig.update_yaxes(
        title_text="Pressure Altitude (ft. AGL)",
        secondary_y=True,
        range=alt_range,
    )

    if show_plot:
        fig.show()

    if any((write_img, write_html, write_pdf)):
        out_dir.mkdir(exist_ok=True)

    if write_img:
        fig.write_image(out_dir / f"{out_file_stem}.png")
    if write_html:
        fig.write_html(out_dir / f"{out_file_stem}.html")
    if write_pdf:
        fig.write_image(out_dir / f"{out_file_stem}.pdf")
