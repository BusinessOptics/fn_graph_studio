from collections import defaultdict

import dash_core_components as dcc
import dash_html_components as html


def get_parameter_attrs(key, type_):

    if issubclass(type_, bool):
        return None

    parameter_attrs = {
        bool: dict(type="text"),
        float: dict(type="number"),
        int: dict(type="number"),
        str: dict(type="text"),
    }

    for base_type, attrs in parameter_attrs.items():
        if issubclass(type_, base_type):
            return dict(**attrs, id=f"parameter_{key}")

    return None


def create_input(key, type_, value):

    if issubclass(type_, bool):
        return dcc.RadioItems(
            options=[
                {"label": "True", "value": "True"},
                {"label": "False", "value": "False"},
            ],
            value=str(value),
        )

    attrs = get_parameter_attrs(key, type_)

    if attrs:
        return dcc.Input(
            **attrs,
            debounce=True,
            value=value,
            persistence=True,
            style=dict(width="100%", border="1px solid lightgrey"),
        )
    else:
        return html.Pre(
            str(value), style=dict(border="1px solid lightgrey", color="lightgrey")
        )


def get_variable_parameter_keys(parameters):
    for key, (type_, value) in parameters.items():
        attrs = get_parameter_attrs(key, type_)
        if attrs:
            yield key


def get_variable_parameter_ids(parameters):
    for key, (type_, value) in parameters.items():
        attrs = get_parameter_attrs(key, type_)
        if attrs:
            yield attrs["id"]


def title(string):
    return string.replace("_", " ").capitalize()


def parameter_widgets(parameters):

    widgets = {
        key: create_input(key, type_, value)
        for key, (type_, value) in parameters.items()
    }

    def recursive_tree():
        return defaultdict(recursive_tree)

    tree = recursive_tree()

    for key, component in widgets.items():
        parts = key.split("__")
        root = tree

        for part in parts[:-1]:
            root = root[part]
        root[parts[-1]] = component

    def create_containers(level, key, value):
        if isinstance(value, dict):

            if level == 0:
                return html.Div(
                    [
                        create_containers(level + 1, ckey, cvalue)
                        for ckey, cvalue in value.items()
                    ],
                    style=dict(padding="0.5rem"),
                )
            elif level == 1:
                return html.Div(
                    [
                        html.Div(
                            title(key),
                            style=dict(
                                borderBottom="1px solid lightgrey",
                                padding="0.25rem",
                                backgroundColor="#eee",
                                fontWeight="bold",
                            ),
                        ),
                        html.Div(
                            [
                                create_containers(level + 1, ckey, cvalue)
                                for ckey, cvalue in value.items()
                            ],
                            style=dict(padding="0.25rem"),
                        ),
                    ],
                    style=dict(border="1px solid lightgrey", marginBottom="0.25rem"),
                )
            else:
                return html.Div(
                    [
                        html.Label(title(key), style=dict(fontWeight="bold")),
                        html.Div(
                            [
                                html.Div([create_containers(level + 1, ckey, cvalue)])
                                for ckey, cvalue in value.items()
                            ],
                            style=dict(
                                marginLeft="0.25rem",
                                paddingLeft="0.25rem",
                                borderLeft="1px solid lightgrey",
                                borderLeftWidth=f"{1 if level > 0 else 0}px",
                            ),
                        ),
                    ]
                )

        else:
            return html.Div(
                [
                    html.Label(title(key), style=dict(fontWeight="bold")),
                    html.Div(value),
                ],
                style=dict(marginBottom="0.25rem"),
            )

    return create_containers(0, "", tree)
