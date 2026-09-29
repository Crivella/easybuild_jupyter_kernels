"""Test the CLI commands."""
import pytest
from click.testing import CliRunner
from commons import EESSI_PREFIX

from easybuild_jupyter_kernels import environment as env
from easybuild_jupyter_kernels.cli.kernel_cmds import list_kernels, store_kernels


def test_list_kernels(lmod_environment):
    """Test the list_kernels command."""
    runner = CliRunner()
    result = runner.invoke(list_kernels)
    assert result.exit_code == 0
    assert 'python3: ' in result.output, \
        "Expected 'python3' kernel from jupyter-server dependency to be listed in the output"


def test_list_kernels_verbose(lmod_environment):
    """Test the list_kernels command with verbose option."""
    runner = CliRunner()
    result = runner.invoke(list_kernels, ['--verbose'])
    assert result.exit_code == 0
    assert 'python3: ' in result.output
    assert "'argv': ['python', '-m', 'ipykernel_launcher', '-f', '{connection_file}']" in result.output, \
        "Expected detailed information about the 'python3' kernel to be listed in the output"


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

def test_store_kernels(tmp_path, lmod_environment):
    """Test the store_kernels command."""
    output_dir = tmp_path / 'kernels'
    runner = CliRunner()
    result = runner.invoke(store_kernels, [str(output_dir)])
    assert result.exit_code == 0
    assert output_dir.exists(), 'Expected output directory to be created'
    assert (output_dir / 'python3' / 'kernel.json').exists(), \
        "Expected 'python3' kernel.json to be stored in the output directory"
