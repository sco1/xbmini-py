from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

CD = Path()


def make_plot(
    *,
    xdata: pd.TimedeltaIndex,
    ydata: pd.Series | pd.DataFrame,
    title: str,
    xlabel: str,
    ylabel: dict[str, str],
    line_width: int | float = 1.5,
    width: int = 1440,
    height: int = 900,
    show_plot: bool = False,
) -> go.Figure:
    """
    Build a plot from the provided input data stream.

    `ylabel` is assumed to be provided as a dictionary whose keys map to the `name` of a `pd.Series`
    or their respective column name(s) in a `pd.DataFrame`.

    To plot on multiple y axes with respect to a common time index, provide `ydata` as a
    `pd.DataFrame` with multiple columns.

    NOTE: A maximum of 2 y axes is currently supported.
    """
    if isinstance(ydata, pd.Series):
        is_multi = False
    elif isinstance(ydata, pd.DataFrame):
        is_multi = True
        _, ncols = ydata.shape
        if ncols > 2:
            raise ValueError(f"Plotting not supported for more than 2 data series. Given: {ncols}")

    # Secondary y won't show if there's nothing plotted on it
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    if is_multi:
        is_secondary = False
        for col in ydata:
            fig.add_trace(
                go.Scatter(x=xdata, y=ydata[col], name=col, line_width=line_width),
                secondary_y=is_secondary,
            )
            fig.update_yaxes(title_text=ylabel[col], secondary_y=is_secondary)
            is_secondary = True  # We can only have 2 columns so a simple flip is sufficient
    else:
        fig.add_trace(go.Scatter(x=xdata, y=ydata, name=xdata.name, line_width=line_width))
        fig.update_yaxes(title_text=ylabel[ydata.name], secondary_y=False)

    # Set properties that don't vary by plot type
    fig.update_layout(title_text=title, xaxis_title=xlabel, width=width, height=height)

    if show_plot:
        fig.show()

    return fig


def write_plot(
    *,
    fig: go.Figure,
    out_file_stem: str,
    out_dir: Path = CD,
    write_img: bool = True,
    write_html: bool = False,
    write_pdf: bool = False,
) -> None:
    """Export the provided figure to the destination in the format(s) specified."""
    if any((write_img, write_html, write_pdf)):
        out_dir.mkdir(exist_ok=True)

    if write_img:
        fig.write_image(out_dir / f"{out_file_stem}.png")
    if write_html:
        fig.write_html(out_dir / f"{out_file_stem}.html")
    if write_pdf:
        fig.write_image(out_dir / f"{out_file_stem}.pdf")
