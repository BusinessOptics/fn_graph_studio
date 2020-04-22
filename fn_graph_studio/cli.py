import os
import time
import traceback
from importlib import import_module, invalidate_caches
from io import StringIO
from pathlib import Path

import click
import sh

import fn_graph.examples
from fn_graph_studio import run_studio


@click.group()
def cli():
    pass


def _run_module(composer, clear):

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

            if clear:
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
                if clear:
                    os.system("cls" if os.name == "nt" else "clear")
                click.echo(click.style(formatted_exc, fg="red"))
            previous_exc = formatted_exc

            # Wait 1 second and try again
            time.sleep(1)


@click.command()
@click.argument("composer")
@click.option("--clear/--no-clear", "clear", default=True)
def run(composer, clear):
    """
    Runs a studio for a composer specified by it's module.

    COMPOSER path to the composer

    The COMPOSER path must be specified path.to.module:obj where path.to.module 
    is a python module path and obj is the name of the composer object in that module.
    """
    _run_module(composer, clear)


EXAMPLES = {
    "simple": "A simple example showing basic functionality",
    "namespaces": "A more complex example showing namespaces",
    "broken": "An example with a broken composer",
    "plotting": "Examples of various different supported plotting libraries",
    "caching": "An example showing caching behaviour",
    "machine_learning": "A simple machine learing example based",
}


@click.command()
@click.argument("example")
@click.option("--clear/--no-clear", "clear", default=True)
def example(example, clear):
    """Runs a studio for an example composer.

    EXAMPLE the name of the example to run, enter "list" to list possibilities.
    """

    examples_path = Path(fn_graph.examples.__path__[0])
    example_module_names = [
        path.stem
        for path in examples_path.glob("*.py")
        if not path.stem.startswith("__")
    ]

    if example in example_module_names:
        _run_module(f"fn_graph.examples.{example}:f", clear)
    else:
        buffer = StringIO()
        buffer.write("EXAMPLE must be one of the below:\n\n")

        for module_name in example_module_names:
            buffer.write(f"{module_name}:\n")
            module = import_module(f"fn_graph.examples.{module_name}")
            doc_string = module.__doc__ or ""
            doc_string = doc_string[: doc_string.find(".") + 1].strip()
            buffer.write(f"  {doc_string}\n\n")

        buffer.seek(0)
        click.echo(buffer.read())


cli.add_command(run)
cli.add_command(example)

if __name__ == "__main__":
    cli()
