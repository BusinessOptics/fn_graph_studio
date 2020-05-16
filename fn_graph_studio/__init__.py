import inspect
import traceback
from pathlib import Path

import dash
import dash_ace_persistent
import dash_core_components as dcc
import dash_dangerously_set_inner_html
import dash_html_components as html
import networkx as nx
import numpy as np
import pandas as pd
import plotly.express as px
from dash import Dash
from dash.dependencies import ALL, Input, Output, State
from dash_interactive_graphviz import DashInteractiveGraphviz
from dash_split_pane import DashSplitPane
from dash_treebeard import DashTreebeard
from fn_graph.calculation import (
    NodeInstruction,
    calculate_collect_exceptions,
    get_execution_instructions,
)
from fn_graph.profiler import Profiler
from fn_graph import Composer
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import PythonLexer

from .parameter_editor import parameter_widgets
from .result_renderers import add_default_renderers
from .layout_helpers import Pane, VStack, HStack, Fill, Scroll

__package__ = "fn_graph_studio"


# Load up embedded styles
# We embed the styles directly in the template for portabilities sake
# I feel there is likely a better way to do this but I cannot fnd it.
with open(Path(__file__).parent / "styles.css") as f:
    styles = f.read()

with open(Path(__file__).parent / "highlight.css") as f:
    highlight_styles = f.read()


class BaseStudio:
    def __init__(
        self,
        app,
        *,
        get_composer,
        title="Fn Graph Studio",
        show_profiler=True,
        editable_parameters=True,
        renderers=None,
    ):
        self._get_composer = get_composer
        self.show_profiler = show_profiler
        self.editable_parameters = editable_parameters
        app.title = title

        app.layout = self.layout()

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

        @app.callback(
            [
                Output("result-function-name", "children"),
                Output("result-type", "children"),
                Output("error-container", "children"),
                Output("result-container", "children"),
                Output("cache-invalidation-store", "data"),
            ],
            [
                Input("function-tree", "selected"),
                Input("result-processor", "value"),
                Input("result-or-definition", "value"),
                Input("invalidate-cache", "n_clicks"),
                Input("url", "pathname"),
                Input({"type": "parameter", "key": ALL}, "value"),
            ],
            [State("cache-invalidation-store", "data")],
        )
        def populate_result_with_composer(
            function_name,
            result_processor,
            result_or_definition,
            invalidate_cache_clicks,
            path,
            parameter_values,
            cache_invalidation_store,
        ):
            composer = self.get_composer(path)
            parameters = {
                input["id"]["key"]: input["value"]
                for input in dash.callback_context.inputs_list[-1]
            }

            invalidate_cache = (cache_invalidation_store or 0) < (
                invalidate_cache_clicks or 0
            )
            if invalidate_cache:
                composer.cache_invalidate(function_name)
                cache_invalidation_store = invalidate_cache_clicks

            return self.populate_result_pane(
                composer,
                add_default_renderers(renderers),
                parameters,
                function_name,
                result_processor,
                result_or_definition,
            ) + (cache_invalidation_store,)

        @app.callback(
            Output("graphviz-viewer", "dot_source"),
            [
                Input("node-name-filter", "value"),
                Input("graph-display-options", "value"),
                Input("graph-neighbourhood", "value"),
                Input("graph-neighbourhood-size", "value"),
                Input("function-tree", "selected"),
                Input("url", "pathname"),
            ],
            [State("cache-invalidation-store", "data")],
        )
        def populate_graph_with_composer(
            node_name_filter,
            graph_display_options,
            graph_neighbourhood,
            graph_neighbourhood_size,
            selected_node,
            url,
            cache_invalidation_store,
        ):
            composer = self.get_composer(url)
            return self.populate_graph(
                composer,
                node_name_filter,
                graph_display_options,
                graph_neighbourhood,
                graph_neighbourhood_size,
                selected_node,
            )

        @app.callback(
            Output("function-tree", "data"),
            [Input("node-name-filter", "value"), Input("url", "pathname")],
        )
        def populate_tree_with_composer(node_name_filter, url):
            composer = self.get_composer(url)
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

        @app.callback(
            Output("parameters-widgets", "children"),
            [
                Input("url", "pathname"),
                Input("parameter-reset-button", "n_clicks"),
                Input({"type": "parameter", "key": ALL}, "value"),
            ],
            [State("parameter_store", "data")],
        )
        def populate_parameters_with_composer(
            url, reset_button, parameter_value_placeholder, store
        ):
            changed_id = [p["prop_id"] for p in dash.callback_context.triggered][0]
            composer = self.get_composer(url)

            if "parameter-reset-button" in changed_id:
                # We want to reset all the values
                parameter_values = {}
                store = {}
            else:
                parameter_values = {
                    input["id"]["key"]: input["value"]
                    for input in dash.callback_context.inputs_list[-1]
                }

            return parameter_widgets(
                composer.parameters(),
                parameter_values or store or {},
                self.editable_parameters,
            )

        sidebar_components = self.sidebar_components()

        @app.callback(
            [Output(component.id, "style") for component in sidebar_components.values()]
            + [Output("node-name-filter", "style")],
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
            ] + [
                dict(
                    border="1px solid lightgrey",
                    width=" calc(100% - 10px)",
                    margin="5px",
                    display="block" if "parameters" != explorer else "none",
                )
            ]

        @app.callback(
            Output("parameter_store", "data"),
            [
                Input("url", "pathname"),
                Input({"type": "parameter", "key": ALL}, "value"),
            ],
        )
        def save_parameters_to_session(url, parameter_values):
            composer = self.get_composer(url)
            composer_parameters = composer.parameters()
            changed_parameters = {
                input["id"]["key"]: input["value"]
                for input in dash.callback_context.inputs_list[-1]
                if input["value"] != composer_parameters[input["id"]["key"]]
            }

            return changed_parameters

        @app.callback(
            Output("tree_store", "data"),
            [Input("function-tree", "selected")],
            [State("tree_store", "data")],
        )
        def save_tree_to_session(selected, data):
            if selected and isinstance(selected[0], list):
                selected = selected[0]

            data = data or {}
            data.update({"selected": selected})
            return data

        @app.callback(
            Output("function-tree", "selected"),
            [Input("graphviz-viewer", "selected"), Input("url", "pathname")],
            [State("tree_store", "data")],
        )
        def update_tree_node(selected, _url, data):
            data = data or {}
            if selected:
                return selected
            else:
                return data.get("selected", "")

    def get_composer(self, path) -> Composer:
        """
        Lazily calls the get_composer function based on the path

        This allows it to dynamically choose  a composer.
        """
        return self._get_composer(path)

    def layout(self):
        return Pane(
            children=[
                dcc.Location(id="url", refresh=False),
                dcc.Store(id="parameter_store", storage_type="session"),
                dcc.Store(id="tree_store", storage_type="session"),
                dcc.Store(id="cache-invalidation-store", storage_type="memory"),
                DashSplitPane(
                    [self.sidebar_layout(), self.results_pane_layout()],
                    size=400,
                    persistence=True,
                ),
            ],
            style=dict(width="100%", height="100%", position="absolute"),
        )

    def function_tree(self, component_id):
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

    def sidebar_components(self):
        return {
            "graph": Fill(
                self.function_graph(),
                id="function-graph-holder",
                style=dict(display="none"),
            ),
            "tree": Fill(
                self.function_tree("function-tree"),
                id="function-tree-holder",
                style=dict(display="none"),
            ),
            "parameters": Fill(
                VStack(
                    [
                        Pane(
                            id="parameters-widgets",
                            style=dict(flexGrow=1, flexShrink=1, overflowY="auto"),
                        ),
                        Pane(
                            html.Button(
                                "Reset parameters", id="parameter-reset-button"
                            ),
                            style=dict(padding="0.5rem", textAlign="right"),
                        ),
                    ],
                    style=dict(height="100%"),
                ),
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

    def sidebar_layout(self):
        sidebar_components = self.sidebar_components()
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
                        style=dict(display="none"),
                        persistence=True,
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

    def results_pane_layout(self):

        options = [
            {"label": "Result", "value": "result"},
            {"label": "Definition", "value": "definition"},
        ]
        if self.show_profiler:
            options.append({"label": "Profiler", "value": "profiler"})

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
                html.Span(
                    [
                        html.Button("Invalidate Cache", id="invalidate-cache"),
                        dcc.RadioItems(
                            id="result-or-definition",
                            options=options,
                            value="result",
                            persistence=True,
                            inputStyle=dict(marginLeft="10px", marginRight="2px"),
                        ),
                    ],
                    style=dict(display="flex", alignItems="center"),
                ),
            ],
            style=dict(
                padding="0.5rem", display="flex", justifyContent="space-between"
            ),
        )

        error_container = html.Div(id="error-container")

        result = dcc.Loading(
            Pane(Scroll(id="result-container"), style=dict(height="100%")),
            color="#7dc242",
        )

        return VStack(
            [status_bar, error_container, result],
            style=dict(flexGrow=1, flexShrink=1, height="100%"),
            className="result-layout",
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
        parameters,
        function_name,
        result_processor,
        result_or_definition,
    ):

        if function_name not in set(composer.dag().nodes()):
            return None, None, None, None

        if result_or_definition == "result":
            return self.populate_result(
                composer, renderers, function_name, result_processor, parameters
            )
        elif result_or_definition == "definition":
            return self.populate_definition(composer, function_name)
        else:
            return self.populate_profiler(composer, function_name, parameters)

    def update_composer_parameters(self, composer, parameters):
        """
        Ensures that boolean parameters et cast correctly
        """

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
    ):
        graph_display_options = graph_display_options or []
        hide_parameters = "parameters" not in graph_display_options
        flatten = "flatten" in graph_display_options
        caching = "caching" in graph_display_options
        expand_links = "links" in graph_display_options

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
    app = Dash(__name__, suppress_callback_exceptions=True)
    cls(app, get_composer=lambda path: composer, **kwargs)
    app.run_server(debug=True)
