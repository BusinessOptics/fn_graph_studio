import dash_html_components as html


def BasePane(default_style):
    def wrapper(*args, style=None, **kwargs):
        return html.Div(
            *args,
            style={"box-sizing": "border-box", **default_style, **(style or {})},
            **kwargs,
        )

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
