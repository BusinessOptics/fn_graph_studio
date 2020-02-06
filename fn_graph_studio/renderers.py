import dash_core_components as dcc
import dash_html_components as html
import dash_table
import pandas as pd
import plotly


def render_dataframe(result):
    df = result.head(5000).reset_index()

    return dash_table.DataTable(
        id="table",
        filter_action="native",
        sort_action="native",
        # fixed_rows={"headers": True, "data": 0},
        sort_mode="multi",
        columns=[{"name": i, "id": i} for i in df.columns],
        # style_cell=dict(minWidth="100px"),
        # style_table={"height": "100%", "overflowX": "scroll"},
        data=df.to_dict("records"),
    )


def render_plotly(result):
    return dcc.Graph(figure=result, style=dict(height="100%"))


def render_object(result):
    return html.Pre(str(result), style=dict(paddingLeft="0.5rem", paddingTop="0.5rem"))


def add_default_renders(result_renderers):
    return [
        *(result_renderers or {}).items(),
        (pd.DataFrame, render_dataframe),
        (plotly.graph_objs._figure.Figure, render_plotly),
        (object, render_object),
    ]
