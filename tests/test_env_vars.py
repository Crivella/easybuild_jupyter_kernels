"""Tests for checking if the custom kernelspec manager finds the expected kernels from EasyBuild's `jupyter-server`
modules."""
from commons import kernelspec_response_common

from easybuild_jupyter_kernels.environment import (
    DEFAULT_DISPLAY_LIMIT, DEFAULT_DISPLAY_PREFIX, get_display_prefix, get_kernel_display_limit,
)
from easybuild_jupyter_kernels.loose_version import LooseVersion


def test_get_kernel_display_limit_none(monkeypatch):
    """Test get_kernel_display_limit returns 0 when the environment variable is not set."""
    monkeypatch.delenv('EB_JUPYTER_KERNEL_LIMIT', raising=False)
    assert get_kernel_display_limit() == DEFAULT_DISPLAY_LIMIT

def test_get_kernel_display_limit_wrong(monkeypatch):
    """Test get_kernel_display_limit returns 0 when the environment variable is set to a non-integer value."""
    monkeypatch.setenv('EB_JUPYTER_KERNEL_LIMIT', 'not_an_integer')
    assert get_kernel_display_limit() == DEFAULT_DISPLAY_LIMIT

def test_get_kernel_display_limit_valid(monkeypatch):
    """Test get_kernel_display_limit returns the correct integer when the environment variable is set to a
    valid integer."""
    value = 5
    monkeypatch.setenv('EB_JUPYTER_KERNEL_LIMIT', str(value))
    assert get_kernel_display_limit() == 5

def test_get_display_prefix_none(monkeypatch):
    """Test get_display_prefix returns the default value when the environment variable is not set."""
    monkeypatch.delenv('EB_JUPYTER_KERNEL_DISPLAY_PREFIX', raising=False)
    assert get_display_prefix() == DEFAULT_DISPLAY_PREFIX


async def test_kernel_display_limit_integration1(monkeypatch, jp_fetch, jupyter_server_module1, jupyter_server_module2):
    """Integration test display_limit environment variable: checks that the launcher_version takes precedence."""
    monkeypatch.setenv('EB_JUPYTER_KERNEL_LIMIT', '1')

    kernelspecs = kernelspec_response_common(await jp_fetch('api/kernelspecs'))

    if LooseVersion(jupyter_server_module1.pyver) >= LooseVersion(jupyter_server_module2.pyver):
        raise ValueError('modules 2 should have a higher luancher version than module 1 for this test.')
    module = jupyter_server_module2

    expected_kernel_name = f"{module.kname}__{module.version}"
    kernel = kernelspecs.pop(expected_kernel_name, None)
    assert kernel is not None, f"{expected_kernel_name} kernel not found in kernelspecs {kernelspecs}"

    # Only the expected kernels should be present, no additional kernels from modules
    assert len(kernelspecs) == 0

async def test_kernel_display_limit_integration2(monkeypatch, jp_fetch, jupyter_server_module2, jupyter_server_module3):
    """Integration test display_limit environment variable: checks that the launcher_versions takes precedence over
    module version."""
    monkeypatch.setenv('EB_JUPYTER_KERNEL_LIMIT', '1')

    kernelspecs = kernelspec_response_common(await jp_fetch('api/kernelspecs'))

    if LooseVersion(jupyter_server_module3.pyver) >= LooseVersion(jupyter_server_module2.pyver):
        raise ValueError('modules 2 should have a higher luancher version than module 3 for this test.')
    if jupyter_server_module3.version <= jupyter_server_module2.version:
        raise ValueError('modules 3 should have a higher version than module 2 for this test.')
    module = jupyter_server_module2

    expected_kernel_name = f"{module.kname}__{module.version}"
    kernel = kernelspecs.pop(expected_kernel_name, None)
    assert kernel is not None, f"{expected_kernel_name} kernel not found in kernelspecs {kernelspecs}"

    # Only the expected kernels should be present, no additional kernels from modules
    assert len(kernelspecs) == 0

async def test_kernel_display_limit_integration3(monkeypatch, jp_fetch, jupyter_server_module3, jupyter_server_module1):
    """Integration test display_limit environment variable: checks that the module version is considered  when
    the launcher_version is the same (default ascending from module avail)."""
    monkeypatch.setenv('EB_JUPYTER_KERNEL_LIMIT', '1')

    kernelspecs = kernelspec_response_common(await jp_fetch('api/kernelspecs'))

    if LooseVersion(jupyter_server_module1.pyver) != LooseVersion(jupyter_server_module3.pyver):
        raise ValueError('modules 1 should have the same launcher version as module 3 for this test.')
    if jupyter_server_module3.version <= jupyter_server_module1.version:
        raise ValueError('modules 3 should have a higher version than module 1 for this test.')
    module = jupyter_server_module1

    expected_kernel_name = f"{module.kname}__{module.version}"
    kernel = kernelspecs.pop(expected_kernel_name, None)
    assert kernel is not None, f"{expected_kernel_name} kernel not found in kernelspecs {kernelspecs}"

    # Only the expected kernels should be present, no additional kernels from modules
    assert len(kernelspecs) == 0
