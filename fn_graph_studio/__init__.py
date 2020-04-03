import inspect
import traceback
from pathlib import Path

import dash_ace_persistent
import dash_core_components as dcc
import dash_dangerously_set_inner_html
import dash_html_components as html
import networkx as nx
import numpy as np
import pandas as pd
import plotly.express as px
from dash import Dash
from dash.dependencies import Input, Output, State
from dash_interactive_graphviz import DashInteractiveGraphviz
from dash_split_pane import DashSplitPane
from dash_treebeard import DashTreebeard
from fn_graph.calculation import (
    NodeInstruction,
    calculate_collect_exceptions,
    get_execution_instructions,
)
from fn_graph.profiler import Profiler
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import PythonLexer

from .parameter_editor import (
    get_variable_parameter_ids,
    get_variable_parameter_keys,
    parameter_widgets,
)
from .result_renderers import add_default_renderers

__package__ = "fn_graph_studio"


# Load up embedded styles
# We embed the styles directly in the template ofr portabilities sake
# I feel there is likely a better way to do this but I cannot fnd it.
with open(Path(__file__).parent / "styles.css") as f:
    styles = f.read()

with open(Path(__file__).parent / "highlight.css") as f:
    highlight_styles = f.read()


def BasePane(default_style):
    def wrapper(*args, style=None, **kwargs):
        return html.Div(*args, style={**default_style, **(style or {})}, **kwargs)

    return wrapper


grid_border = 0

Pane = BasePane(dict(position="relative", border=f"{grid_border}px solid black"))

Scroll = BasePane(
    dict(
        overflow="auto",
        width="100%",
        height="100%",
        position="absolute",
        border=f"{grid_border}px solid yellow",
    )
)
Fill = BasePane(
    dict(
        height="100%",
        width="100%",
        position="absolute",
        overflow="hidden",
        border=f"{grid_border}px solid green",
    )
)
HStack = BasePane(
    dict(
        display="flex",
        overflow="hidden",
        position="relative",
        border=f"{grid_border}px solid blue",
    )
)
VStack = BasePane(
    dict(
        display="flex",
        flexDirection="column",
        overflow="hidden",
        position="relative",
        border=f"{grid_border}px solid red",
    )
)


class BaseStudio:
    def __init__(self, app, composer, renderers=None):

        app.title = "Fn Graph Studio"

        app.layout = self.layout(composer)

        app.index_string = (
            """
        <!DOCTYPE html>
        <html>
            <head>
                {%metas%}
                <title>{%title%}</title>
                {%favicon%}
                {%css%}
                <style>
                """
            + styles
            + "\n\n"
            + highlight_styles
            + """
                </style>
            </head>
            <body>                
                {%app_entry%}
                <footer>
                    {%config%}
                    {%scripts%}
                    {%renderer%}
                </footer>                
            </body>
        </html>
        """
        )

        parameter_keys = list(get_variable_parameter_keys(composer.parameters()))
        parameter_ids = list(get_variable_parameter_ids(composer.parameters()))

        @app.callback(
            [
                Output(
                    component_id="result-function-name", component_property="children"
                ),
                Output(component_id="result-type", component_property="children"),
                Output(component_id="error-container", component_property="children"),
                Output(component_id="result-container", component_property="children"),
            ],
            [
                Input(component_id="function-tree", component_property="selected"),
                Input(component_id="result-processor", component_property="value"),
                Input(component_id="result-or-definition", component_property="value"),
                *[
                    Input(component_id=id_, component_property="value")
                    for id_ in parameter_ids
                ],
            ],
        )
        def populate_result_with_composer(
            function_name, result_processor, result_or_definition, *parameter_values
        ):
            return self.populate_result_pane(
                composer,
                add_default_renderers(renderers),
                parameter_keys,
                function_name,
                result_processor,
                result_or_definition,
                parameter_values,
            )

        @app.callback(
            Output(component_id="graphviz-viewer", component_property="dot_source"),
            [
                Input(component_id="node-name-filter", component_property="value"),
                Input(component_id="graph-display-options", component_property="value"),
                Input(component_id="graph-neighbourhood", component_property="value"),
                Input(
                    component_id="graph-neighbourhood-size", component_property="value"
                ),
                Input(component_id="function-tree", component_property="selected"),
                *[
                    Input(component_id=id_, component_property="value")
                    for id_ in parameter_ids
                ],
            ],
        )
        def populate_graph_with_composer(
            node_name_filter,
            graph_display_options,
            graph_neighbourhood,
            graph_neighbourhood_size,
            selected_node,
            *parameter_values,
        ):
            return self.populate_graph(
                composer,
                node_name_filter,
                graph_display_options,
                graph_neighbourhood,
                graph_neighbourhood_size,
                selected_node,
                parameter_keys,
                parameter_values,
            )

        @app.callback(
            Output(component_id="function-tree", component_property="data"),
            [Input(component_id="node-name-filter", component_property="value")],
        )
        def populate_tree_with_composer(node_name_filter):
            if node_name_filter:
                matching_nodes = [
                    key
                    for key in composer.functions().keys()
                    if node_name_filter.strip().lower() in key.lower()
                ]
                tree = composer.subgraph(matching_nodes)._build_name_tree()
            else:
                tree = composer._build_name_tree()

            def format_tree(key, value):
                if isinstance(value, str):
                    return {"name": key, "key": value}
                else:
                    return {
                        "name": key,
                        "key": key,
                        "children": [format_tree(k, v) for k, v in value.items()],
                    }

            return format_tree("_root_", tree)

        sidebar_components = self.sidebar_components(composer)

        @app.callback(
            [
                Output(component.id, "style")
                for component in sidebar_components.values()
            ],
            [Input("explorer-selector", "value")],
        )
        def toggle_explorer(explorer):
            return [
                dict(
                    height="100%",
                    width="100%",
                    position="absolute",
                    overflow="auto",
                    display="block" if option == explorer else "none",
                )
                for option in sidebar_components.keys()
            ]

        @app.callback(
            Output("session", "data"),
            [Input("function-tree", "selected")],
            [State("session", "data")],
        )
        def on_save_to_session(selected, data):
            if selected and isinstance(selected[0], list):
                selected = selected[0]

            data = data or {}
            data.update({"selected": selected})
            return data

        @app.callback(
            Output("function-tree", "selected"),
            [Input("graphviz-viewer", "selected"), Input("url", "pathname")],
            [State("session", "data")],
        )
        def update_tree_node(selected, _url, data):
            data = data or {}
            if selected:
                return selected
            else:
                return data.get("selected", "")

    def layout(self, composer):
        return Pane(
            children=[
                dcc.Location(id="url", refresh=False),
                dcc.Store(id="session", storage_type="session"),
                DashSplitPane(
                    [self.sidebar(composer), self.results_pane()],
                    size=400,
                    persistence=True,
                ),
            ],
            style=dict(width="100%", height="100%", position="absolute"),
        )

    def function_tree(self, component_id, composer):
        return Scroll(
            DashTreebeard(
                id=component_id,
                data={"name": "_root_", "key": "_root_", "children": []},
                persistence="tree",
            )
        )

    def function_graph(self):
        label_width = 50

        def Label(text):
            return html.Strong(
                f"{text}: ", style=dict(display="inline-block", width=label_width)
            )

        return VStack(
            [
                dcc.Checklist(
                    id="graph-neighbourhood",
                    options=[
                        {"label": "All", "value": "all"},
                        {"label": "Ancestors", "value": "ancestors"},
                        {"label": "Descendants", "value": "descendants"},
                        {"label": "Neighbours", "value": "neighbours"},
                    ],
                    value=["all"],
                    persistence=True,
                    labelStyle=dict(paddingRight=10),
                    inputStyle=dict(marginRight=2),
                    style=dict(display="inline", marginBottom="5px"),
                ),
                dcc.Input(
                    id="graph-neighbourhood-size",
                    type="number",
                    value=1,
                    min=0,
                    persistence=1,
                    style=dict(
                        border="1px solid lightgrey", width="100%", marginBottom="5px"
                    ),
                ),
                dcc.Checklist(
                    id="graph-display-options",
                    options=[
                        {"label": "Flatten", "value": "flatten"},
                        {"label": "Parameters", "value": "parameters"},
                        {"label": "Links", "value": "links"},
                        {"label": "Caching", "value": "caching"},
                    ],
                    persistence=1,
                    labelStyle=dict(paddingRight=10),
                    inputStyle=dict(marginRight=2),
                ),
                Pane(
                    DashInteractiveGraphviz(id="graphviz-viewer", persistence=False),
                    style=dict(flexGrow=1),
                ),
            ],
            style=dict(
                height="100%",
                width="100%",
                position="absolute",
                padding="5px",
                paddingTop="0px",
            ),
        )

    def parameters(self, composer):
        return parameter_widgets(composer.parameters())

    def sidebar_components(self, composer):
        return {
            "graph": Fill(
                self.function_graph(),
                id="function-graph-holder",
                style=dict(display="none"),
            ),
            "tree": Fill(
                self.function_tree("function-tree", composer),
                id="function-tree-holder",
                style=dict(display="none"),
            ),
            "parameters": Fill(
                self.parameters(composer),
                id="parameters-holder",
                style=dict(display="none"),
            ),
        }

    def result_processor(self):
        return dash_ace_persistent.DashAceEditor(
            id="result-processor",
            value="",
            theme="github",
            mode="python",
            tabSize=2,
            placeholder="e.g. result.query(....)",
            maxLines=10,
            minLines=5,
            showGutter=False,
            persistence=True,
            highlightActiveLine=False,
            debounceChangePeriod=1000,
        )

    def sidebar(self, composer):
        sidebar_components = self.sidebar_components(composer)
        explorer_options = [
            dict(value=k, label=k.capitalize()) for k in sidebar_components
        ]

        return VStack(
            [
                HStack(
                    [
                        dcc.Tabs(
                            id="explorer-selector",
                            value="tab-1-example",
                            parent_className="custom-tabs",
                            className="custom-tabs-container",
                            children=[
                                dcc.Tab(label=option["label"], value=option["value"])
                                for option in explorer_options
                            ],
                            persistence=True,
                        )
                    ],
                    style=dict(flexShrink=0),
                ),
                Pane(
                    dcc.Input(
                        id="node-name-filter",
                        type="text",
                        placeholder="Filter nodes",
                        value="",
                        persistence=True,
                        style=dict(
                            border="1px solid lightgrey",
                            width=" calc(100% - 10px)",
                            margin="5px",
                        ),
                        debounce=True,
                    )
                ),
                Pane(
                    list(sidebar_components.values()),
                    style=dict(flexGrow=1, flexShrink=1),
                ),
                VStack(
                    [html.Strong("Result Processor"), self.result_processor()],
                    style=dict(
                        borderTop="1px solid lightgrey", padding="0.5rem", flexShrink=0
                    ),
                ),
            ],
            style=dict(flexShrink=0, height="100%", borderRight="1px solid lightgrey"),
        )

    def results_pane(self):

        status_bar = html.Div(
            [
                html.Span(
                    [
                        html.Strong(f"Function name: "),
                        html.Span(id="result-function-name"),
                        html.Span(" "),
                        html.Span(id="result-type"),
                    ]
                ),
                dcc.RadioItems(
                    id="result-or-definition",
                    options=[
                        {"label": "Result", "value": "result"},
                        {"label": "Definition", "value": "definition"},
                        {"label": "Profiler", "value": "profiler"},
                    ],
                    value="result",
                    persistence=True,
                    inputStyle=dict(marginLeft="10px", marginRight="2px"),
                ),
            ],
            style=dict(
                padding="0.5rem", display="flex", justifyContent="space-between"
            ),
        )

        error_container = html.Div(id="error-container")

        result = dcc.Loading(
            Pane(Scroll(id="result-container"), style=dict(height="100%")),
            style=dict(flexGrow=1),
            className="result-loader",
            color="#7dc242",
        )

        return VStack(
            [status_bar, error_container, result],
            style=dict(flexGrow=1, flexShrink=1, height="100%"),
        )

    def process_result(self, result, result_processor_value):

        return eval(
            result_processor_value, globals(), dict(result=result, px=px, pd=pd, np=np)
        )

    def render_result(self, renderers, result):
        for typ, render in renderers:
            if isinstance(result, typ):
                return render(result)
        return "Rendering error - No matching renderer"

    def render_exception(self, exception_info):

        etype, evalue, etraceback, function_key = exception_info

        lines = []
        for frame in traceback.extract_tb(etraceback)[1:]:
            lines.extend(
                [
                    html.Div(
                        [
                            f"{frame.filename}, line {frame.lineno}, in ",
                            html.Span(frame.name, style=dict(fontWeight="bold")),
                        ],
                        style=dict(paddingBottom="2px"),
                    ),
                    html.Pre(
                        frame.line,
                        style=dict(
                            borderRadius="3px",
                            border="1px solid #ac9",
                            padding="5px",
                            backgroundColor="#eeffcc",
                            color="#333333",
                            lineHeight="120%",
                        ),
                    ),
                ]
            )

        return html.Div(
            [
                html.H2(["Exception when calculating ", html.Strong(function_key)]),
                html.Div(
                    repr(evalue),
                    style=dict(
                        color="red",
                        paddingBottom="1rem",
                        fontWeight="bold",
                        fontSize="1.2rem",
                    ),
                ),
                html.Div(lines),
            ],
            style=dict(padding="0.5rem"),
        )

    def populate_result(
        self, composer, renderers, function_name, result_processor_value, parameters
    ):

        composer = self.update_composer_parameters(composer, parameters)

        results, exception_info = calculate_collect_exceptions(
            composer, [function_name]
        )

        if exception_info:
            return (function_name, None, None, self.render_exception(exception_info))

        result = results[function_name]

        error = None
        if result_processor_value.strip():
            try:
                result = self.process_result(result, result_processor_value)
            except Exception as e:
                error = str(e)

        error_bar = (
            html.Div(
                [
                    html.Div(
                        [html.Strong("Result processor error: "), html.Span(error)]
                    ),
                    html.Pre(result_processor_value),
                ],
                style=dict(padding="0.5rem", border="1px solid red", color="red"),
            )
            if error
            else None
        )

        return (
            function_name,
            str(type(result)),
            error_bar,
            self.render_result(renderers, result),
        )

    def populate_definition(self, composer, function_name):

        source = composer.get_source(function_name)
        highlighted = highlight(source, PythonLexer(), HtmlFormatter())

        return (
            function_name,
            None,
            None,
            html.Div(
                dash_dangerously_set_inner_html.DangerouslySetInnerHTML(highlighted),
                style=dict(padding="0.5rem"),
            ),
        )

    def populate_profiler(self, composer, function_name, parameters):

        composer = self.update_composer_parameters(composer, parameters)

        profiler = Profiler()
        calculate_collect_exceptions(
            composer, [function_name], progress_callback=profiler
        )

        profile = profiler.results()

        green = "#7dc242"

        totals = [
            metrics["total"]
            for metrics in [
                *profile["functions"].values(),
                *profile["startup"].values(),
            ]
        ]

        highest = max(totals)
        total = sum(totals)

        def plot_bars(*metrics):
            return [
                html.Div(
                    style=dict(
                        width=f"{value}%",
                        display="inline-block",
                        background=color,
                        height="1rem",
                    ),
                    title=f"{key} = {metric_total:.2f}% ({metric_absolute:.3f}s)",
                )
                for key, value, metric_total, metric_absolute, color in metrics
            ]

        def profile_section(section, bar_description):
            return [
                html.Tr(
                    [
                        html.Th(k, style=dict(width="20%", padding="3px")),
                        html.Td(
                            plot_bars(
                                *[
                                    (
                                        key,
                                        metrics[key] / highest * 90,
                                        metrics[key] / total * 100,
                                        metrics[key],
                                        color,
                                    )
                                    for key, color in bar_description
                                ]
                            ),
                            style=dict(padding="3px"),
                        ),
                    ],
                    style=dict(
                        border="1px solid white",
                        background="#eee" if i % 2 == 0 else None,
                    ),
                )
                for i, (k, metrics) in enumerate(section.items())
            ]

        content = html.Div(
            html.Table(
                html.Tbody(
                    profile_section(profile["startup"], [("preparation", "lightgrey")])
                    + [html.Tr(html.Td(style=dict(height="2rem")))]
                    + profile_section(
                        profile["functions"],
                        [
                            ("overhead", "lightgrey"),
                            ("cache_retrieval", "grey"),
                            ("execution", green),
                            ("cache_store", "grey"),
                        ],
                    )
                ),
                style=dict(width="100%", boxSizing="border-box"),
            ),
            style=dict(margin="0.5rem"),
        )

        return (function_name, None, None, content)

    def populate_result_pane(
        self,
        composer,
        renderers,
        parameter_keys,
        function_name,
        result_processor,
        result_or_definition,
        parameter_values,
    ):

        if function_name not in set(composer.dag().nodes()):
            return None, None, None, None

        if result_or_definition == "result":
            return self.populate_result(
                composer,
                renderers,
                function_name,
                result_processor,
                dict(zip(parameter_keys, parameter_values)),
            )
        elif result_or_definition == "definition":
            return self.populate_definition(composer, function_name)
        else:
            return self.populate_profiler(
                composer, function_name, dict(zip(parameter_keys, parameter_values))
            )

    def update_composer_parameters(self, composer, parameters):
        def smartish_cast(type_, value):
            if issubclass(type_, bool) and isinstance(value, str):
                return value.lower()[0] == "t"
            else:
                return value

        parameters = {
            key: smartish_cast(type_, parameters[key])
            for key, (type_, _) in composer.parameters().items()
            if key in parameters
        }
        return composer.update_parameters(**parameters)

    def populate_graph(
        self,
        composer,
        node_name_filter,
        graph_display_options,
        graph_neighbourhood,
        graph_neighbourhood_size,
        selected_node,
        parameter_keys,
        parameter_values,
    ):
        graph_display_options = graph_display_options or []
        hide_parameters = "parameters" not in graph_display_options
        flatten = "flatten" in graph_display_options
        caching = "caching" in graph_display_options
        expand_links = "links" in graph_display_options

        composer = self.update_composer_parameters(
            composer, dict(zip(parameter_keys, parameter_values))
        )

        G = composer.dag()
        subgraph = set()

        if "all" in graph_neighbourhood:
            subgraph.update(G.nodes())

        if selected_node in G:

            if "ancestors" in graph_neighbourhood:
                subgraph.update(
                    nx.ego_graph(
                        G.reverse(),
                        selected_node,
                        radius=graph_neighbourhood_size,
                        undirected=False,
                    )
                )

            if "descendants" in graph_neighbourhood:
                subgraph.update(
                    nx.ego_graph(
                        G,
                        selected_node,
                        radius=graph_neighbourhood_size,
                        undirected=False,
                    )
                )

            if "neighbours" in graph_neighbourhood:
                subgraph.update(
                    nx.ego_graph(
                        G,
                        selected_node,
                        radius=graph_neighbourhood_size,
                        undirected=True,
                    )
                )

        if node_name_filter:
            subgraph = {
                node
                for node in subgraph
                if node_name_filter.strip().lower() in node.lower()
            }

        if caching:
            instructions = get_execution_instructions(composer, composer.dag(), [])

            def get_node_styles(instruction):
                return {
                    NodeInstruction.IGNORE: dict(color="green", penwidth="2"),
                    NodeInstruction.RETRIEVE: dict(color="orange", penwidth="2"),
                    NodeInstruction.CALCULATE: dict(color="red", penwidth="2"),
                }[instruction]

            extra_node_styles = {
                node: get_node_styles(instruction) for node, instruction in instructions
            }
        else:
            extra_node_styles = {}

        return composer.graphviz(
            hide_parameters=hide_parameters,
            flatten=flatten,
            expand_links=expand_links,
            highlight=[selected_node],
            filter=subgraph,
            extra_node_styles=extra_node_styles,
        ).source


class Studio(BaseStudio):
    pass


class ExternalStudio(BaseStudio):
    """
    This studio is mean to be suitable for release on the public internet.
    It does not allow for code injection (We think).

    Use with Caution, this is a WIP.
    """

    def result_processor(self):
        return dash_ace_persistent.DashAceEditor(
            id="result-processor",
            value="",
            theme="github",
            mode="python",
            tabSize=2,
            placeholder='Enter a query string.\n\nYou can use full pandas query strings.\ne.g.: merchant_id == "ABC"',
            maxLines=10,
            minLines=5,
            showGutter=False,
            persistence=True,
            highlightActiveLine=False,
            debounceChangePeriod=1000,
        )

    def process_result(self, result, value):
        from pandas import DataFrame

        if isinstance(result, DataFrame):
            return result.query(value, truediv=True)
        else:
            return result


def run_external_studio(composer, **kwargs):
    """
    Run an external studio for the given composer.
    """
    _run_studio(ExternalStudio, composer, **kwargs)


def run_studio(composer, **kwargs):
    """
    Run a development studio for the given composer.
    """
    _run_studio(Studio, composer, **kwargs)


def _run_studio(cls, composer, **kwargs):
    """
    Run a studio of type cls for the given composer.
    """
    app = Dash(__name__)
    cls(app, composer, **kwargs)
    app.run_server(debug=True)
