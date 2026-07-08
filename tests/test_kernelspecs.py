"""Tests for checking if the custom kernelspec manager finds the expected kernels from EasyBuild's `jupyter-server`
modules."""
import json

from commons import DEFAULT_KERNELS


def kernelspec_response_common(response):
    """Common checks for the /api/kernelspecs endpoint response."""
    assert response.code == 200

    response_dct = json.loads(response.body.decode())

    kernelspecs = response_dct.pop('kernelspecs', None)
    assert kernelspecs is not None, 'kernelspecs key not found in response'

    for kernel_name in DEFAULT_KERNELS:
        kernel = kernelspecs.pop(kernel_name, None)
        assert kernel is not None, f"{kernel_name} kernel not found in kernelspecs"

    return kernelspecs

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
        expected_kernel_name = f"{module.name}__{module.version}"
        kernel = kernelspecs.pop(expected_kernel_name, None)
        assert kernel is not None, f"{expected_kernel_name} kernel not found in kernelspecs"

    # Only the expected kernels should be present, no additional kernels from modules
    assert len(kernelspecs) == 0

async def test_kernels_endpoint_multiple_module(jp_fetch, jupyter_server_module1, jupyter_server_module2):
    """Test the /api/kernelspecs endpoint with one jupyter-server module available."""
    kernelspecs = kernelspec_response_common(await jp_fetch('api/kernelspecs'))

    for module in [jupyter_server_module1, jupyter_server_module2]:
        expected_kernel_name = f"{module.name}__{module.version}"
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
            expected_kernel_name = f"{module.name}__{module.version}"
            m1_kernel = kernelspecs.pop(expected_kernel_name, None)
            assert m1_kernel is not None, f"{expected_kernel_name} kernel not found in kernelspecs"

    # Only the expected kernels should be present, no additional kernels from modules
    assert len(kernelspecs) == 0

async def test_kernels_display_env_var(mock_display_prefix, jp_fetch, jupyter_server_module1):
    """Test the /api/kernelspecs endpoint with one jupyter-server module available."""
    kernelspecs = kernelspec_response_common(await jp_fetch('api/kernelspecs'))

    for module in [jupyter_server_module1]:
        expected_kernel_name = f"{module.name}__{module.version}"
        kernel = kernelspecs.pop(expected_kernel_name, None)
        assert kernel is not None, f"{expected_kernel_name} kernel not found in kernelspecs"
        spec = kernel.get('spec')
        assert spec is not None, f"spec for {expected_kernel_name} kernel not found"
        display_name = spec.get('display_name', '')
        assert display_name.startswith(mock_display_prefix), \
            f"display_name for {expected_kernel_name} '{display_name}' kernel does not start with {mock_display_prefix}"

    # Only the expected kernels should be present, no additional kernels from modules
    assert len(kernelspecs) == 0

async def test_kernel_all(
        jp_fetch, jupyter_server_module1, ijulia_module1, octave_module1, rootkernel_module1, irkernel_module1
    ):
    """Test the /api/kernelspecs endpoint with one of every module type."""
    kernelspecs = kernelspec_response_common(await jp_fetch('api/kernelspecs'))

    for module in [jupyter_server_module1, ijulia_module1, octave_module1, rootkernel_module1, irkernel_module1]:
        expected_kernel_name = f"{module.name}__{module.version}"
        kernel = kernelspecs.pop(expected_kernel_name, None)
        assert kernel is not None, f"{expected_kernel_name} kernel not found in kernelspecs"

    # Only the expected kernels should be present, no additional kernels from modules
    assert len(kernelspecs) == 0
