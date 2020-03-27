import sh
import click
from importlib import import_module, invalidate_caches
from fn_graph_studio import run_studio
import traceback
import time


@click.group()
def cli():
    pass


def _run_module(composer):
    # The previously displayed exception
    # Used for de-duplication
    previous_exc = ""

    while True:
        try:

            # Find the composer given the module declaration
            module_path, obj_path = composer.split(":")
            invalidate_caches()
            module = import_module(module_path)
            composer_obj = getattr(module, obj_path)

            # Run the studio
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
                print(formatted_exc)
            previous_exc = formatted_exc

            # Wait 1 second and try again
            time.sleep(1)


@click.command()
@click.argument("composer")
def run(composer):
    _run_module(composer)


@click.command()
@click.argument("example")
def example(example):
    _run_module(f"fn_graph_studio.examples.{example}:f")


cli.add_command(run)
cli.add_command(example)

if __name__ == "__main__":
    cli()
