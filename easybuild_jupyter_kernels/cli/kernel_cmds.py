"""List available kernels."""
import json
import os
import re
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

def filter_path_like_envvar(env_var_value: str, patterns: list[str]) -> tuple[list[str], list[str]]:
    """Filter a PATH-like environment variable value based on provided regex patterns."""
    if not env_var_value:
        return [], []
    if not patterns:
        return env_var_value, []
    patterns = list(patterns) + [r'^$']  # Avoid filtering empty paths
    paths = env_var_value.split(os.pathsep)
    stored_paths = []
    filtered_paths = []
    for p in paths:
        if any(re.search(pattern, p) for pattern in patterns):
            stored_paths.append(p)
        else:
            filtered_paths.append(p)
    return stored_paths, filtered_paths

@cli.command()
@click.argument(
    'output_dir',
    default=os.path.expanduser('~/.local/share/jupyter/kernels'),
    type=click.Path(file_okay=False, dir_okay=True, writable=True),
)
@click.option(
    '--filter-paths', type=str, multiple=True,
    help=(
        'List of path regexes to filter the kernels to be stored. '
        'Only kernels whose paths match any of the provided regexes will be stored.'
    )
)
@click.option(
    '--filter-env-paths', type=str, multiple=True,
    help=(
        'Filter PATH-like environmenet variable so that all entries match at least one of the provided regexes.'
    )
)
def store_kernels(output_dir, filter_paths, filter_env_paths):
    """Store kernels in the specified directory."""
    click.echo(f"Storing kernels in {output_dir}...")
    click.echo(f"Filter: {filter_paths}")
    click.echo(f"Filter env paths: {filter_env_paths}")

    manager = EBKernelSpecManager()
    kernels = manager.find_kernel_specs()
    if not kernels:
        click.echo('No kernels found.')
        return

    for name, path in kernels.items():
        if filter_paths and not any(re.search(pattern, path) for pattern in filter_paths):
            click.echo(f"Skipping kernel {name} as its path {path} does not match any filter.")
            continue
        spec = manager.get_kernel_spec(name)

        kernel_dir = os.path.join(output_dir, name)
        os.makedirs(kernel_dir, exist_ok=True)

        spec_dict = spec.to_dict()
        env_dct = spec_dict.get('env', {})
        for key in env_dct:
            stored_paths, filtered_paths = filter_path_like_envvar(env_dct[key], filter_env_paths)
            env_dct[key] = os.pathsep.join(stored_paths)

            if filtered_paths:
                click.echo(
                    f"Filtered {len(filtered_paths)} entries from env var '{key}' for kernel {name}: "
                    f"{', '.join(filtered_paths)}"
                )

        with open(os.path.join(kernel_dir, 'kernel.json'), 'w', encoding='utf-8') as f:
            json.dump(spec_dict, f, indent=2)

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
