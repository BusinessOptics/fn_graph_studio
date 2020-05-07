from io import BytesIO
from pprint import pformat

import dash_core_components as dcc
import dash_cytoscape as cyto
import dash_dangerously_set_inner_html
import dash_html_components as html
import dash_table
import matplotlib.artist
import matplotlib.pylab as plt
import networkx as nx
import pandas as pd
import plotly
import seaborn.axisgrid

from .layout_helpers import Pane, VStack, HStack, Fill, Scroll


def render_dataframe(result):
    max_length = 5000
    length = len(result)
    width = len(result.columns)
    render_length = max_length // width
    df = result.head(render_length).reset_index()
    return Fill(
        VStack(
            [
                html.Div(
                    f"Displaying {render_length:,} of {length:,} rows ({render_length * width:,} of {length * width:,} cells)",
                    style=dict(fontWeight="bold", textAlign="right", padding="2px"),
                )
                if length > max_length
                else None,
                Pane(
                    Scroll(
                        dash_table.DataTable(
                            id="table",
                            filter_action="native",
                            sort_action="native",
                            # fixed_rows={"headers": True, "data": 0},
                            sort_mode="multi",
                            columns=[{"name": i, "id": i} for i in df.columns],
                            data=df.to_dict("records"),
                        )
                    ),
                    style=dict(flexGrow=1, flexShrink=1),
                ),
            ],
            style=dict(height="100%"),
        )
    )


def render_plotly(result):
    return dcc.Graph(figure=result, style=dict(height="100%"))


def render_object(result):
    max_length = 10000
    formatted = pformat(result)
    length = len(formatted)
    if length > max_length:
        formatted = f"Truncated to {max_length:,} characters from {length:,}\n\n{formatted[:max_length]}..."

    return html.Pre(formatted, style=dict(paddingLeft="0.5rem", paddingTop="0.5rem"))


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


def render_networkx(G):
    nodes = [{"data": {"id": node, "label": node}} for node in G.nodes()]
    edges = [{"data": {"source": f, "target": t}} for (f, t) in G.edges()]

    if len(nodes) > 200:
        return render_object(G)

    return cyto.Cytoscape(
        layout={"name": "cose"},
        style={"width": "100%", "height": "100%"},
        elements=nodes + edges,
    )


def add_default_renderers(renderers):
    return [
        *(renderers or {}).items(),
        (pd.DataFrame, render_dataframe),
        (plotly.graph_objs.Figure, render_plotly),
        (matplotlib.artist.Artist, render_matplotlib),
        (seaborn.axisgrid.Grid, render_seaborn),
        (nx.Graph, render_networkx),
        (object, render_object),
    ]
