from io import BytesIO

import dash_core_components as dcc
import dash_dangerously_set_inner_html
import dash_html_components as html
import dash_table
import matplotlib.artist
import matplotlib.pylab as plt
import pandas as pd
import plotly
import seaborn.axisgrid


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


def mpl_to_svg(in_fig: matplotlib.artist.Artist):
    # This normalizes multiple matplotlib artists to the base figure
    in_fig = in_fig.figure if (hasattr(in_fig, "figure") and in_fig.figure) else in_fig

    out_img = BytesIO()
    in_fig.savefig(out_img, format="svg")

    # We refresh the plot so we don't get side effects between runs
    plt.subplots()

    out_img.seek(0)  # rewind file
    svg_doc = out_img.read().decode("utf8")

    # This strips out the document declarations
    # This is not my most elegant work
    svg_tag = svg_doc[svg_doc.find("<svg") :]
    return svg_tag


def render_seaborn(result: seaborn.axisgrid.Grid):
    svg = mpl_to_svg(result.fig)
    return html.Div(
        dash_dangerously_set_inner_html.DangerouslySetInnerHTML(svg),
        style=dict(display="flex", justifyContent=" center"),
    )


def render_matplotlib(result):
    svg = mpl_to_svg(result)

    return html.Div(
        dash_dangerously_set_inner_html.DangerouslySetInnerHTML(svg),
        style=dict(display="flex", justifyContent=" center"),
    )


def add_default_renderers(renderers):
    return [
        *(renderers or {}).items(),
        (pd.DataFrame, render_dataframe),
        (plotly.graph_objs._figure.Figure, render_plotly),
        (matplotlib.artist.Artist, render_matplotlib),
        (seaborn.axisgrid.Grid, render_seaborn),
        (object, render_object),
    ]
