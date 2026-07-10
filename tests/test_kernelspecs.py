"""Tests for checking if the custom kernelspec manager finds the expected kernels from EasyBuild's `jupyter-server`
modules."""
from dataclasses import asdict

from commons import kernelspec_response_common

from easybuild_jupyter_kernels.kernelspec import (
    CLING_CPP_STDS, MODULE_KERNEL_MAP, KernelData,
)


def compare_dicts(dct1, dct2):
    """Compare two dictionaries and return True if they are equal, False otherwise."""
    if dct1.keys() != dct2.keys():
        return False
    for k in dct1.keys():
        v1 = dct1[k]
        v2 = dct2[k]
        if isinstance(v1, dict) and isinstance(v2, dict):
            if not compare_dicts(v1, v2):
                return False
        elif v1 != v2:
            return False
    return True


def test_kernel_data_cache(monkeypatch, jupyter_server_module1):
    """Test that the kernel data cache is populated correctly."""
    import subprocess  # pylint: disable=import-outside-toplevel

    # Save the original subprocess.check_output function and replace it with a mock that sets `called` to True
    called = False
    monkeypatch.setattr(subprocess, '_check_output', subprocess.check_output, raising=False)
    def mock_check_output(*args, **kwargs):
        nonlocal called
        called = True
        return subprocess._check_output(*args, **kwargs)  # pylint: disable=protected-access,no-member
    monkeypatch.setattr(subprocess, 'check_output', mock_check_output)

    info_map = MODULE_KERNEL_MAP.get(jupyter_server_module1.kname, None)

    module = f'{jupyter_server_module1.name}/{jupyter_server_module1.version}'

    data1 = KernelData.from_env_module(module, info_map=info_map)
    assert called, 'subprocess.check_output was not called'
    called = False
    data2 = KernelData.from_env_module(module, info_map=info_map)
    assert not called, 'subprocess.check_output was called again, cache not used'
    assert data1 is data2, 'KernelData instances are not the same, cache not used'

    called = False
    KernelData.from_env_module.cache_clear()
    data3 = KernelData.from_env_module(module, info_map=info_map)
    assert called, 'subprocess.check_output was not called after cache clear'
    assert data1 is not data3, 'KernelData instances are the same after cache clear, cache not cleared'

    dct1 = asdict(data1)
    dct3 = asdict(data3)

    assert compare_dicts(asdict(data1), asdict(data3)), \
        f"KernelData instances are not equal after cache clear: {dct1} != {dct3}"

async def test_kernels_endpoint_bare(jp_fetch, lmod_environment):
    """Test the /api/kernelspecs endpoint without any modules available.

    Tests that the custom EBKernelSpecManager still finds the default kernels (echo and python3).
    """
    kernelspecs = kernelspec_response_common(await jp_fetch('api/kernelspecs'))

    # Only the expected kernels should be present, no additional kernels from modules
    assert len(kernelspecs) == 0

async def test_kernels_endpoint_one_module(jp_fetch, jupyter_server_module1):
    """Test the /api/kernelspecs endpoint with one jupyter-server module available."""
    kernelspecs = kernelspec_response_common(await jp_fetch('api/kernelspecs'))

    for module in [jupyter_server_module1]:
        expected_kernel_name = f"{module.kname}__{module.version}"
        kernel = kernelspecs.pop(expected_kernel_name, None)
        assert kernel is not None, f"{expected_kernel_name} kernel not found in kernelspecs"

    # Only the expected kernels should be present, no additional kernels from modules
    assert len(kernelspecs) == 0

async def test_kernels_endpoint_multiple_module(jp_fetch, jupyter_server_module1, jupyter_server_module2):
    """Test the /api/kernelspecs endpoint with one jupyter-server module available."""
    kernelspecs = kernelspec_response_common(await jp_fetch('api/kernelspecs'))

    for module in [jupyter_server_module1, jupyter_server_module2]:
        expected_kernel_name = f"{module.kname}__{module.version}"
        kernel = kernelspecs.pop(expected_kernel_name, None)
        assert kernel is not None, f"{expected_kernel_name} kernel not found in kernelspecs"

    # Only the expected kernels should be present, no additional kernels from modules
    assert len(kernelspecs) == 0

async def test_kernels_endpoint_preloaded_python(
        monkeypatch,
        jp_fetch, jupyter_server_module1, jupyter_server_module2, jupyter_server_module3
    ):
    """Test the /api/kernelspecs endpoint returns only kernels compatible with a pre-loaded python module that
    sets the EBVERSIONPYTHON environment variable."""
    expected_pyver = '3.8'
    monkeypatch.setenv('EBVERSIONPYTHON', expected_pyver)

    kernelspecs = kernelspec_response_common(await jp_fetch('api/kernelspecs'))

    for module in [jupyter_server_module1, jupyter_server_module2, jupyter_server_module3]:
        if module.pyver == expected_pyver:
            expected_kernel_name = f"{module.kname}__{module.version}"
            m1_kernel = kernelspecs.pop(expected_kernel_name, None)
            assert m1_kernel is not None, f"{expected_kernel_name} kernel not found in kernelspecs"

    # Only the expected kernels should be present, no additional kernels from modules
    assert len(kernelspecs) == 0

async def test_kernels_endpoint_preloaded_kernel(monkeypatch, jp_fetch, octave_module1):
    """Test the /api/kernelspecs endpoint returns only kernels compatible with a pre-loaded modules for the same kernel
    """
    monkeypatch.setenv('EBVERSIONOCTAVE', octave_module1.version + 'someotherstring')

    kernelspecs = kernelspec_response_common(await jp_fetch('api/kernelspecs'))

    # No kernel should be visible since we are preloading a module for a kernel not compatible with the only
    # octave-kernel module exposed to the system
    assert len(kernelspecs) == 0

async def test_kernels_display_env_var(mock_display_prefix, jp_fetch, jupyter_server_module1):
    """Test the /api/kernelspecs endpoint with one jupyter-server module available."""
    kernelspecs = kernelspec_response_common(await jp_fetch('api/kernelspecs'))

    for module in [jupyter_server_module1]:
        expected_kernel_name = f"{module.kname}__{module.version}"
        kernel = kernelspecs.pop(expected_kernel_name, None)
        assert kernel is not None, f"{expected_kernel_name} kernel not found in kernelspecs"
        spec = kernel.get('spec')
        assert spec is not None, f"spec for {expected_kernel_name} kernel not found"
        display_name = spec.get('display_name', '')
        assert display_name.startswith(mock_display_prefix), \
            f"display_name for {expected_kernel_name} '{display_name}' kernel does not start with {mock_display_prefix}"

    # Only the expected kernels should be present, no additional kernels from modules
    assert len(kernelspecs) == 0

async def test_kernel_cling(jp_fetch, cling_module1, mock_jupyter_cling_kernel):
    """Test the /api/kernelspecs endpoint with one of every module type."""
    kernelspecs = kernelspec_response_common(await jp_fetch('api/kernelspecs'))

    for module in [cling_module1]:
        for std in CLING_CPP_STDS:
            expected_kernel_name = f"{module.kname}-{std}__{module.version}"
            kernel = kernelspecs.pop(expected_kernel_name, None)
            assert kernel is not None, f"{expected_kernel_name} kernel not found in kernelspecs {kernelspecs}"

    # Only the expected kernels should be present, no additional kernels from modules
    assert len(kernelspecs) == 0


async def test_kernel_all(
        jp_fetch, jupyter_server_module1, ijulia_module1, octave_module1, rootkernel_module1, irkernel_module1,
        jpk_bash_module1
    ):
    """Test the /api/kernelspecs endpoint with one of every module type."""
    kernelspecs = kernelspec_response_common(await jp_fetch('api/kernelspecs'))

    for module in [
            jupyter_server_module1, ijulia_module1, octave_module1, rootkernel_module1, irkernel_module1,
            jpk_bash_module1
        ]:
        expected_kernel_name = f"{module.kname}__{module.version}"
        kernel = kernelspecs.pop(expected_kernel_name, None)
        assert kernel is not None, f"{expected_kernel_name} kernel not found in kernelspecs {kernelspecs}"

    # Only the expected kernels should be present, no additional kernels from modules
    assert len(kernelspecs) == 0
