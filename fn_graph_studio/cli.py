import os
import time
import traceback
from importlib import import_module, invalidate_caches

import click
import sh

from fn_graph_studio import run_studio


@click.group()
def cli():
    pass


def _run_module(composer):

    try:
        module_path, obj_path = composer.split(":")
    except ValueError:
        click.echo("The COMPOSER path must be specified as 'path.to.module:obj'")
        exit()

    # The previously displayed exception
    # Used for de-duplication
    previous_exc = ""

    while True:
        try:

            invalidate_caches()
            try:
                # Find the composer given the module declaration
                module = import_module(module_path)
            except ModuleNotFoundError as e:
                click.echo(e)
                exit()

            composer_obj = getattr(module, obj_path)

            os.system("cls" if os.name == "nt" else "clear")
            # Run the studio
            click.echo(click.style(f"Running studio {module_path}", fg="green"))
            run_studio(composer_obj)
            # When the dash runner is killed via ctrl-c this will exit
            break
        except KeyboardInterrupt:
            # This will run when ctrl-c is pressed outside of the dash server
            break
        except Exception as e:

            # Print the exception if it has changed
            formatted_exc = traceback.format_exc()
            if formatted_exc != previous_exc:
                os.system("cls" if os.name == "nt" else "clear")
                click.echo(click.style(formatted_exc, fg="red"))
            previous_exc = formatted_exc

            # Wait 1 second and try again
            time.sleep(1)


@click.command()
@click.argument("composer")
def run(composer):
    """
    Runs a studio for a composer specified by it's module.

    COMPOSER path to the composer

    The COMPOSER path must be specified path.to.module:obj where path.to.module 
    is a python module path and obj is the name of the composer object in that module.
    """
    _run_module(composer)


EXAMPLES = {
    "simple": "A simple example showing basic functionality",
    "complex": "A more complex example showing namespaces",
    "broken": "An example with a broken composer",
    "plotting": "Examples of various different supported plotting libraries",
    "caching": "An example showing caching behaviour",
}

EXAMPLE_STRING = "\n".join(
    [f"{name}:\n  {description}\n" for name, description in EXAMPLES.items()]
)


@click.command()
@click.argument("example")
def example(example):
    """Runs a studio for an example composer.

    The following examples are available:

    simple:
        A simple example showing basic functionality

    complex:
        A more complex example showing namespaces

    broken:
        An example with a broken composer

    plotting:
        Examples of various different supported plotting libraries

    caching:
        An example showing caching behavior

    EXAMPLE the name of the example to run, from the above list
    """

    if example not in EXAMPLES:
        help_string = f"EXAMPLE must be one of the below:\n\n{EXAMPLE_STRING}"
        click.echo(help_string)
        exit()

    _run_module(f"fn_graph_studio.examples.{example}:f")


cli.add_command(run)
cli.add_command(example)

if __name__ == "__main__":
    cli()
