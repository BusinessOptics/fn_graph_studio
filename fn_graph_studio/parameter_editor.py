from collections import defaultdict
from pprint import pformat

import dash_core_components as dcc
import dash_html_components as html

GREEN = "rgb(125, 194, 66)"


def get_parameter_attrs(key, type_):

    parameter_attrs = {
        bool: dict(type="bool"),  # This is overridden
        float: dict(type="number"),
        int: dict(type="number"),
        str: dict(type="text"),
    }

    for base_type, attrs in parameter_attrs.items():
        if issubclass(type_, base_type):
            return dict(**attrs, id={"type": "parameter", "key": key})

    return None


def create_input(key, type_, value, editable):

    if issubclass(type_, bool):
        return dcc.RadioItems(
            id={"type": "parameter", "key": key},
            options=[
                {"label": "True", "value": "True"},
                {"label": "False", "value": "False"},
            ],
            value=str(value),
            persistence=True,
            inputStyle=dict(marginRight=2),
            labelStyle=dict(marginRight=10),
        )

    attrs = get_parameter_attrs(key, type_)

    if attrs and editable:
        return dcc.Input(
            **attrs,
            debounce=True,
            value=value,
            persistence=True,
            style=dict(width="100%", border="1px solid lightgrey"),
        )
    else:
        return html.Pre(
            pformat(value),
            id={"type": "static-parameter", "key": key},
            style=dict(border="1px solid lightgrey", color="lightgrey"),
        )


def title(string):
    return string.replace("_", " ").capitalize()


def parameter_widgets(initial_parameters, current_values, editable_parameters):

    if editable_parameters:
        widgets = {
            key: create_input(
                key,
                type_,
                current_values[key] if key in current_values else value,
                True,
            )
            for key, (type_, value) in initial_parameters.items()
        }
    else:
        widgets = {
            key: create_input(key, type_, value, False)
            for key, (type_, value) in initial_parameters.items()
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
                        create_containers(level + 1, container_key, container_value)
                        for container_key, container_value in value.items()
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
                                create_containers(
                                    level + 1, container_key, container_value
                                )
                                for container_key, container_value in value.items()
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
                                html.Div(
                                    [
                                        create_containers(
                                            level + 1, container_key, container_value
                                        )
                                    ]
                                )
                                for container_key, container_value in value.items()
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
            function_name = value.id["key"]
            changed = (
                function_name in current_values
                and current_values[function_name]
                != initial_parameters[function_name][1]
            )

            return html.Div(
                [
                    html.Div(
                        [
                            html.Label(title(key)),
                            html.Span("(modified)") if changed else None,
                        ],
                        style=dict(
                            display="flex",
                            justifyContent="space-between",
                            fontWeight="bold",
                            color=GREEN if changed else None,
                        ),
                    ),
                    html.Div(value),
                ],
                style=dict(marginBottom="0.25rem"),
            )

    return create_containers(0, "", tree)
