"""Cli to manage stored kernelspecs."""
import os

try:
    import click as original_click
    import rich_click as click
except ImportError:
    import click  # pylint: disable=ungrouped-imports
    import click as original_click

try:
    from rich.traceback import install
except ImportError:
    def install(*args, **kwargs):  #pylint: disable=unused-argument
        """Mock install function if rich is not available."""

@click.group()
def cli():
    """Cli to manage stored kernelspecs."""
    show_locals = os.environ.get('RICH_TRACEBACK_SHOW_LOCALS', '1').lower() in ('1', 'true', 'yes')
    install(show_locals=show_locals, suppress=[click, original_click])

__all__ = ['cli']
