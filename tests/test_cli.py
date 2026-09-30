"""Test the CLI commands."""
import os
import re

import pytest
from click.testing import CliRunner
from commons import EESSI_PREFIX, kernelspec_response_common

from easybuild_jupyter_kernels import environment as env
from easybuild_jupyter_kernels.cli.kernel_cmds import list_kernels, store_kernels
from easybuild_jupyter_kernels.kernelspec import MODULE_KERNEL_MAP


def test_list_kernels(ijulia_module1):
    """Test the list_kernels command."""
    runner = CliRunner()
    result = runner.invoke(list_kernels)
    assert result.exit_code == 0
    assert 'python3: ' in result.output, \
        "Expected 'python3' kernel from jupyter-server dependency to be listed in the output"
    julia_kernel_name = f"{ijulia_module1.kname}__{ijulia_module1.version}"
    assert f"{julia_kernel_name}: " in result.output, \
        f"Expected '{julia_kernel_name}' kernel from jupyter-server dependency to be listed in the output"


def test_list_kernels_verbose(ijulia_module2):
    """Test the list_kernels command with verbose option."""
    runner = CliRunner()
    result = runner.invoke(list_kernels, ['--verbose'])
    assert result.exit_code == 0

    julia_kernel_name = f"{ijulia_module2.kname}__{ijulia_module2.version}"
    assert f"{julia_kernel_name}: " in result.output, \
        f"Expected '{julia_kernel_name}' kernel from jupyter-server dependency to be listed in the output"
    kernel_mapping = MODULE_KERNEL_MAP[ijulia_module2.kname]
    launcher_args = kernel_mapping.launcher_args
    launcher_args_str = str(launcher_args)[1:-1]  # Remove the surrounding brackets
    assert launcher_args_str in result.output, \
        f"Expected detailed information about the '{julia_kernel_name}' kernel to be listed in the output"


@pytest.mark.skipif(EESSI_PREFIX is None, reason='EESSI environment not detected')
def test_list_kernels_in_eessi_2023(monkeypatch):
    """Test the list_kernels command within EESSI 2023.06."""
    monkeypatch.setenv(env.INIT_MODULES_ENV_NAME, 'EESSI/2023.06')

    runner = CliRunner()
    result = runner.invoke(list_kernels)
    assert result.exit_code == 0
    assert '/cvmfs/software.eessi.io/versions/2023.06' in result.output, \
        'Expected kernels from jupyter-server modules in EESSI to be listed in the output'


@pytest.mark.skipif(EESSI_PREFIX is None, reason='EESSI environment not detected')
def test_list_kernels_in_eessi_2025(monkeypatch):
    """Test the list_kernels command within EESSI 2025.06."""
    monkeypatch.setenv(env.INIT_MODULES_ENV_NAME, 'EESSI/2025.06')

    runner = CliRunner()
    result = runner.invoke(list_kernels)
    assert result.exit_code == 0
    assert '/cvmfs/software.eessi.io/versions/2025.06' in result.output, \
        'Expected kernels from jupyter-server modules in EESSI to be listed in the output'


def test_store_kernels(tmp_path, ijulia_module1, jupyter_server_module1):
    """Test the store_kernels command."""
    output_dir = tmp_path / 'kernels'
    runner = CliRunner()
    result = runner.invoke(store_kernels, [str(output_dir)])
    assert result.exit_code == 0
    assert output_dir.exists(), 'Expected output directory to be created'

    julia_kernel_name = f"{ijulia_module1.kname}__{ijulia_module1.version}"
    assert (output_dir / julia_kernel_name / 'kernel.json').exists(), \
        f"Expected '{julia_kernel_name}' kernel.json to be stored in the output directory"

    python_kernel_name = f"{jupyter_server_module1.kname}__{jupyter_server_module1.version}"
    assert (output_dir / python_kernel_name / 'kernel.json').exists(), \
        f"Expected '{python_kernel_name}' kernel.json to be stored in the output directory"


def test_store_kernels_with_path_filters(tmp_path, ijulia_module1, jupyter_server_module1):
    """Test the store_kernels command with path filters."""
    output_dir = tmp_path / 'kernels'
    runner = CliRunner()
    filter_paths = [r'.*julia.*']
    result = runner.invoke(store_kernels, [str(output_dir), '--filter-paths'] + filter_paths)
    assert result.exit_code == 0
    assert output_dir.exists(), 'Expected output directory to be created'

    julia_kernel_name = f"{ijulia_module1.kname}__{ijulia_module1.version}"
    assert (output_dir / julia_kernel_name / 'kernel.json').exists(), \
        f"Expected '{julia_kernel_name}' kernel.json to be stored in the output directory"

    python_kernel_name = f"{jupyter_server_module1.kname}__{jupyter_server_module1.version}"
    assert not (output_dir / python_kernel_name / 'kernel.json').exists(), \
        f"Did not expect '{python_kernel_name}' kernel.json to be stored in the output directory due to filter"


def test_store_kernels_with_env_path_filters(monkeypatch, tmp_path, ijulia_module1, mock_julia):
    """Test the store_kernels command with environment path filters."""
    base_path = os.path.dirname(mock_julia)

    # Add a path that should be filtered out
    old_path = os.environ.get('PATH', '')
    fake_path = '/fake' + base_path
    new_path = f"{fake_path}{os.pathsep}{old_path}"
    monkeypatch.setenv('PATH', new_path)

    output_dir = tmp_path / 'kernels'
    runner = CliRunner()
    filter_env_paths = [rf'^{base_path}']
    result = runner.invoke(store_kernels, [str(output_dir), '--filter-env-paths'] + filter_env_paths)

    assert result.exit_code == 0
    assert output_dir.exists(), 'Expected output directory to be created'

    julia_kernel_name = f"{ijulia_module1.kname}__{ijulia_module1.version}"
    assert (output_dir / julia_kernel_name / 'kernel.json').exists(), \
        f"Expected '{julia_kernel_name}' kernel.json to be stored in the output directory"

    assert re.search(rf"Filtered \d+ entries from env var 'PATH' for kernel .* {fake_path}", result.output), \
        'Expected output to indicate that the fake path was filtered out from the PATH environment variable'


# Test a server without the EBKernelSpecManager to ensure that the generated kernels work
@pytest.mark.parametrize('jp_server_config', ['base'], indirect=True)
async def test_store_kernels_and_run(monkeypatch, tmp_path, jp_fetch, ijulia_module1):
    """Test that the kernels stored by store_kernels can be used in a server without EBKernelSpecManager."""
    monkeypatch.setenv('JUPYTER_PATH', str(tmp_path))

    output_dir = tmp_path / 'kernels'
    runner = CliRunner()
    result = runner.invoke(store_kernels, [str(output_dir)])
    assert result.exit_code == 0
    assert output_dir.exists(), 'Expected output directory to be created'

    kernel_name = f"{ijulia_module1.kname}__{ijulia_module1.version}"
    kernelspecs = kernelspec_response_common(await jp_fetch('api/kernelspecs'))
    assert kernel_name.lower() in kernelspecs, \
        f"Expected kernel '{kernel_name}' to be available in the server using pre-generated kernels"
