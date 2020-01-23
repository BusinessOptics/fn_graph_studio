import base64
import inspect

from dash import Dash
import dash_core_components as dcc
import dash_html_components as html
import dash_table
import dash_treeview_antd
import networkx as nx
import pandas as pd
import plotly.graph_objs
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from dash_split_pane import DashSplitPane
from dash_interactive_graphviz import DashInteractiveGraphviz
from fn_graph.calculation import NodeInstruction, get_execution_instructions


def BasePane(default_style):
    def wrapper(*args, style=dict(), **kwargs):
        return html.Div(*args, style={**default_style, **style}, **kwargs)

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
    return dcc.Graph(figure=result)


def render_object(result):
    return html.Pre(str(result), style=dict(paddingLeft="0.5rem", paddingTop="0.5rem"))


def add_default_renders(result_renderers):
    return [
        *(result_renderers or {}).items(),
        (pd.DataFrame, render_dataframe),
        (plotly.graph_objs._figure.Figure, render_plotly),
        (object, render_object),
    ]


class BaseStudio:
    def __init__(self, app, composer, result_renderers=None):

        app.title = "Fn Compose Studio"

        app.layout = self.layout(composer)

        app.callback(
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
            ],
        )(
            lambda *args: self.populate_result_pane(
                composer, add_default_renders(result_renderers), *args
            )
        )

        app.callback(
            Output(component_id="graphviz-viewer", component_property="dot_source"),
            [
                Input(component_id="graph-display-options", component_property="value"),
                Input(component_id="graph-neighbourhood", component_property="value"),
                Input(
                    component_id="graph-neighbourhood-size", component_property="value"
                ),
                Input(component_id="function-tree", component_property="selected"),
            ],
        )(lambda *args: self.populate_graph(composer, *args))

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
                dict(display="block" if option == explorer else "none")
                for option in sidebar_components.keys()
            ]

        @app.callback(
            Output("session", "data"),
            [
                Input("function-tree", "selected"),
                Input("function-tree", "expanded"),
                Input("result-processor", "value"),
                Input("explorer-selector", "value"),
            ],
            [State("session", "data")],
        )
        def on_save_to_session(
            selected, expanded, result_processor, explorer_selector, data
        ):
            if selected and isinstance(selected[0], list):
                selected = selected[0]

            data = data or {}
            data.update(
                {
                    "selected": selected,
                    "expanded": expanded,
                    "result_processor": result_processor,
                    "explorer_selector": explorer_selector,
                }
            )
            return data

        @app.callback(
            [
                Output("function-tree", "expanded"),
                Output("result-processor", "value"),
                Output("explorer-selector", "value"),
            ],
            [Input("url", "pathname")],
            [State("session", "data")],
        )
        def on_initial_load(path, data):

            data = data or {}

            return (
                data.get("expanded", []),
                data.get("result_processor", ""),
                data.get("explorer_selector", "tree"),
            )

        @app.callback(
            Output("function-tree", "selected"),
            [Input("graphviz-viewer", "selected"), Input("url", "pathname")],
            [State("session", "data")],
        )
        def update_tree_node(selected, url, data):
            data = data or {}
            if selected:
                return [selected]
            else:
                return data.get("selected", [])

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

    def function_tree(self, id, composer):
        functions = [dict(label=node, value=node) for node in composer.dag().nodes()]
        tree = composer._build_name_tree()

        def format_tree(key, value):
            formatted = {}
            children = []
            if isinstance(value, str):
                return {"title": key, "key": value}
            else:
                return {
                    "title": key,
                    "key": key,
                    "selectable": False,
                    "children": [format_tree(k, v) for k, v in value.items()],
                }

        return Scroll(
            dash_treeview_antd.TreeView(
                id=id,
                multiple=False,
                checkable=False,
                selected=[],
                expanded=["_root_"],
                data=format_tree("_root_", tree),
            )
        )

    def function_graph(self, composer):
        return VStack(
            [
                html.Div(
                    [
                        html.Strong("Filter: "),
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
                            labelStyle=dict(paddingLeft=10),
                            style=dict(display="inline"),
                        ),
                    ]
                ),
                html.Div(
                    [
                        html.Strong("Neighbourhood size: "),
                        dcc.Input(
                            id="graph-neighbourhood-size",
                            type="number",
                            value=1,
                            min=0,
                            persistence=True,
                            style=dict(border="1px solid lightgrey"),
                        ),
                    ]
                ),
                html.Div(
                    [
                        html.Strong("Display: "),
                        dcc.Checklist(
                            id="graph-display-options",
                            options=[
                                {"label": "Flatten", "value": "flatten"},
                                {"label": "Parameters", "value": "parameters"},
                                {"label": "Links", "value": "links"},
                                {"label": "Caching", "value": "caching"},
                            ],
                            persistence=True,
                            labelStyle=dict(paddingLeft=10),
                            style=dict(display="inline"),
                        ),
                    ]
                ),
                Pane(
                    DashInteractiveGraphviz(id="graphviz-viewer"),
                    style=dict(flexGrow=1),
                ),
            ],
            style=dict(height="100%", width="100%", position="absolute", padding="5px"),
        )

    def sidebar_components(self, composer):
        return {
            "graph": Fill(
                self.function_graph(composer),
                id="function-graph-holder",
                style=dict(display="none"),
            ),
            "tree": Fill(
                self.function_tree("function-tree", composer),
                id="function-tree-holder",
                style=dict(display="none"),
            ),
        }

    def result_processor(self):
        return dcc.Textarea(
            id="result-processor",
            placeholder="e.g. result.query(....)",
            rows=5,
            style=dict(width="100%", border="none"),
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
                        html.Strong("Navigator: "),
                        dcc.RadioItems(
                            id="explorer-selector",
                            options=explorer_options,
                            labelStyle=dict(paddingLeft=10),
                            value="",
                        ),
                    ],
                    style=dict(
                        flexShrink=0, padding="5px", borderBottom="1px solid lightgrey"
                    ),
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
                    ],
                    value="result",
                    persistence=True,
                ),
            ],
            style=dict(
                padding="0.5rem", display="flex", justifyContent="space-between"
            ),
        )

        error_container = html.Div(id="error-container")
        
        # TODO: Use this when Dash gets updated
        # result = dcc.Loading(
        #     Pane(Scroll(id="result-container"), style=dict(height="100%")),
        #     style=dict(flexGrow=1)
        # )

        result = Pane(Scroll(id="result-container"), style=dict(flexGrow=1))
        
        return VStack(
            [status_bar, error_container, result],
            style=dict(flexGrow=1, flexShrink=1, height="100%"),
        )

    def process_result(self, result, result_processor_value):
        return eval(result_processor_value, globals(), dict(result=result))

    def render_result(self, renderers, result):
        for typ, render in renderers:
            if isinstance(result, typ):
                return render(result)
        return "Rendering error - No matching renderer"

    def populate_result(
        self, composer, renderers, function_name, result_processor_value
    ):
        result = composer.calculate([function_name])[function_name]

        error = None
        if result_processor_value:
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
        fn = composer.raw_function(function_name)
        is_parameter = function_name in composer._parameters

        if is_parameter:
            source = f"{function_name} = lambda: {composer._parameters[function_name]}"
        elif getattr(fn, "_is_fn_graph_link", False):
            parameter = list(inspect.signature(fn).parameters.keys())[0]
            source = f"{function_name} = lambda {parameter}: {parameter}"
        else:
            source = inspect.getsource(fn)

        return function_name, None, None, html.Pre(source, style=dict(padding="0.5rem"))

    def populate_result_pane(
        self,
        composer,
        renderers,
        function_names,
        result_processor,
        result_or_definition,
    ):
        if not function_names or function_names[0] not in set(composer.dag().nodes()):
            return None, None, None, None

        function_name = function_names[0]

        if result_or_definition == "result":
            return self.populate_result(
                composer, renderers, function_name, result_processor
            )
        else:
            return self.populate_definition(composer, function_name)

    def populate_graph(
        self,
        composer,
        graph_display_options,
        graph_neighbourhood,
        graph_neighbourhood_size,
        selected_nodes,
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

        if selected_nodes and selected_nodes[0] in G:
            selected_node = selected_nodes[0]

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
            highlight=selected_nodes,
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
        return dcc.Textarea(
            id="result-processor",
            placeholder='Enter a query string.\n\nYou can use full pandas query strings.\ne.g.: merchant_id == "ABC"',
            rows=5,
            style=dict(width="100%", border="none"),
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
    app = Dash(__name__)
    ExternalStudio(app, composer, **kwargs)
    app.run_server(debug=True)


def run_studio(composer, **kwargs):
    """
    Run a development studio for the given composer.
    """
    app = Dash(__name__)
    Studio(app, composer, **kwargs)
    app.run_server(debug=True)
