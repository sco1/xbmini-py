import base64
import datetime as dt
import io
import os

import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
from dash import Dash, dcc, exceptions, html, no_update
from dash.dependencies import Input, Output, State

from xbmini.log_parser import XBMLog, _split_press_temp
from xbmini.viz import make_plot

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

upload_panel = dbc.Card(
    children=[
        dcc.Upload(
            id="upload-log-data",
            children=html.Div(["Drag and Drop or ", html.A("Select Processed CSV File")]),
            style={
                "lineHeight": "60px",
                "borderWidth": "1px",
                "borderStyle": "dashed",
                "borderRadius": "5px",
                "textAlign": "center",
                "margin": "10px",
            },
            multiple=False,
        ),
    ],
    body=True,
)

trim_panel = dbc.Card(
    children=[
        dbc.Button(id="trim-data-button", children="Trim Data"),
        html.Div(id="trim-msg"),
    ],
    body=True,
)

app.layout = dbc.Container(
    children=[
        html.H1("XBM Triminator 9000"),
        html.Hr(),
        dbc.Row(
            children=[dbc.Col(upload_panel)],
            align="center",
        ),
        dbc.Row(
            children=[dbc.Col(dcc.Graph(id="press-alt-plot"))],
        ),
        dbc.Row(
            children=[dbc.Col(trim_panel)],
        ),
        dcc.Store(id="log-data"),
        dcc.Store(id="log-metadata"),
        dcc.Download(id="dl-trimmed-log"),
    ],
)


@app.callback(
    Output("log-data", "data"),
    Output("log-metadata", "data"),
    Input("upload-log-data", "contents"),
    prevent_initial_call=True,
)
def process_upload(contents: str) -> tuple[str, str]:
    """
    Deserialize the provided CSV File into its metadata and `pd.DataFrame` components.

    It is assumed that the upload component is limited to a single file, so the file's `contents`
    are provided as a base64 encoded string. The CSV is assumed to contain a serialized instance of
    `XBMLog`.

    The log's data is concatenated and sent to the `log-data` store as JSON, and its metadata
    is re-serialized to JSON and sent to the `log-metadata` store.
    """
    if contents is not None:
        decoded = base64.b64decode(contents.split(",")[1])
        log = XBMLog.from_processed_csv(io.StringIO(decoded.decode("utf-8")))
    else:
        raise exceptions.PreventUpdate

    full_df = pd.concat((log.mpu, log.press_temp), axis=1)
    return _serialize_df(full_df), log._serialize_metadata()


@app.callback(
    Output("press-alt-plot", "figure"),
    Input("log-data", "data"),
    prevent_initial_call=True,
)
def build_plot(log_data: str) -> go.Figure:  # noqa: D103
    log_df = _deserialze_df(log_data)
    fig = make_plot(
        xdata=log_df.index.total_seconds(),
        ydata=log_df["press_alt_ft"],
        xlabel="Elased Time (s)",
        ylabel={"press_alt_ft": "Pressure Altitude (ft. AGL)"},
        title="Pressure Altitude vs. Time",
        fig_size=None,
    )
    return fig


@app.callback(
    Output("dl-trimmed-log", "data"),
    Output("trim-msg", "children"),
    Input("trim-data-button", "n_clicks"),
    State("log-data", "data"),
    State("log-metadata", "data"),
    State("press-alt-plot", "relayoutData"),
    State("upload-log-data", "filename"),
    prevent_initial_call=True,
)
def trim_plot_data(
    n_clicks: int,
    log_data: str,
    log_metadata: str,
    layout_data: dict[str, float],
    in_filename: str,
) -> tuple[dict, str]:
    """Trim the stored `pd.DataFrame` using the current zoom limits & export to CSV."""
    # Skip trimming if the plot hasn't actually been zoomed
    if layout_data is None or layout_data.get("autosize"):
        return no_update, "Please window the data before trimming."

    log_df = _deserialze_df(log_data)
    window = [
        dt.timedelta(seconds=layout_data["xaxis.range[0]"]),
        dt.timedelta(seconds=layout_data["xaxis.range[1]"]),
    ]
    trimmed_df = log_df.loc[(log_df.index >= window[0]) & (log_df.index <= window[1])]

    metadata = XBMLog._deserialize_metadata(log_metadata)
    press_temp, mpu = _split_press_temp(trimmed_df)
    log = XBMLog(mpu, press_temp, **metadata)
    log._is_merged = True

    name, ext = os.path.splitext(in_filename)
    out_filename = f"{name}_trimmed{ext}"

    return dict(content=log._to_string(), filename=out_filename), "Trimmed file saved successfully!"


def _serialize_df(in_df: pd.DataFrame) -> str:
    ser: str = in_df.to_json(date_unit="ns")
    return ser


def _deserialze_df(in_json: str) -> pd.DataFrame:
    log_df = pd.read_json(in_json, date_unit="ns")
    # Set the index name explicitly since none of the to_json() orient options will preserve it
    log_df.index = pd.TimedeltaIndex(log_df.index, unit="ns").rename("time")
    return log_df


if __name__ == "__main__":
    app.run(debug=True)
