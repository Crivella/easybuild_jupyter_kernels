"""List available kernels."""
import json
import os
import shutil

from ..kernelspec import EBKernelSpecManager
from .main import cli, click


@cli.command()
@click.option('--verbose', is_flag=True, help='Show detailed information about each kernel.')
def list_kernels(verbose):
    """List available kernels."""
    manager = EBKernelSpecManager()
    kernels = manager.find_kernel_specs()
    if not kernels:
        click.echo('No kernels found.')
        return
    click.echo('Available kernels:')
    for name, path in kernels.items():
        click.echo(f"- {name}: {path}")
        spec = manager.get_kernel_spec(name)
        if verbose:
            click.echo(f"  Display name: {spec.to_dict()}")

@cli.command()
@click.argument(
    'output_dir',
    default=os.path.expanduser('~/.local/share/jupyter/kernels'),
    type=click.Path(file_okay=False, dir_okay=True, writable=True),
)
def store_kernels(output_dir):
    """Store kernels in the specified directory."""
    manager = EBKernelSpecManager()
    kernels = manager.find_kernel_specs()
    if not kernels:
        click.echo('No kernels found.')
        return
    for name, _ in kernels.items():
        spec = manager.get_kernel_spec(name)

        kernel_dir = os.path.join(output_dir, name)
        os.makedirs(kernel_dir, exist_ok=True)

        with open(os.path.join(kernel_dir, 'kernel.json'), 'w', encoding='utf-8') as f:
            json.dump(spec.to_dict(), f, indent=2)

        resource_dir = spec.resource_dir
        if resource_dir and os.path.exists(resource_dir):
            for item in os.listdir(resource_dir):
                if item == 'kernel.json':
                    continue
                s = os.path.join(resource_dir, item)
                d = os.path.join(kernel_dir, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    shutil.copy2(s, d)

    click.echo(f"Stored {len(kernels)} kernels in {output_dir}.")

__all__ = ['list_kernels', 'store_kernels']
