import base64
import io

import pandas as pd
import plotly.graph_objects as go
from dash import Dash, dcc, exceptions, html
from dash.dependencies import Input, Output

from xbmini.log_parser import XBMLog
from xbmini.viz import make_plot

app = Dash(__name__)
app.layout = html.Div(
    [
        dcc.Upload(
            id="upload-log-data",
            children=html.Div(["Drag and Drop or ", html.A("Select Processed CSV File")]),
            style={
                "width": "75%",
                "height": "60px",
                "lineHeight": "60px",
                "borderWidth": "1px",
                "borderStyle": "dashed",
                "borderRadius": "5px",
                "textAlign": "center",
                "margin": "10px",
            },
            multiple=False,
        ),
        dcc.Store(id="log-data"),
        dcc.Store(id="log-metadata"),
        dcc.Graph(id="press-alt-plot", style={"width": "75%"}),
        html.Button(id="trim-data", children="Trim Data"),
        html.Div(id="trim-msg"),
    ],
)


@app.callback(
    Output("log-data", "data"),
    Output("log-metadata", "data"),
    Input("upload-log-data", "contents"),
)
def process_upload(contents: str) -> tuple[str, str]:
    if contents is not None:
        decoded = base64.b64decode(contents.split(",")[1])
        log = XBMLog.from_processed_csv(io.StringIO(decoded.decode("utf-8")))
    else:
        raise exceptions.PreventUpdate

    # It's easier if we concatenate and store the data separately from the metadata, we'll only
    # need the metadata again when it's time to write back to disk
    full_df = pd.concat((log.mpu, log.press_temp), axis=1)
    return full_df.to_json(date_unit="ns"), log._serialize_metadata()


@app.callback(
    Output("press-alt-plot", "figure"),
    Input("log-data", "data"),
)
def build_plot(log_data: str) -> go.Figure:
    log_df = pd.read_json(log_data)
    log_df.index = pd.TimedeltaIndex(log_df.index, unit="ns")
    fig = make_plot(
        xdata=log_df.index.total_seconds(),
        ydata=log_df["press_alt_ft"],
        xlabel="Elased Time (s)",
        ylabel={"press_alt_ft": "Pressure Altitude (ft. AGL)"},
        title="Sample Plot",
    )
    return fig


if __name__ == "__main__":
    app.run_server(debug=True)
