"""Tests for checking if the custom kernelspec manager finds the expected kernels from EasyBuild's `jupyter-server`
modules."""

import json

DEFAULT_KERNELS = ['echo', 'python3']


async def test_kernels_endpoint_bare(jp_fetch):
    """Test the /api/kernelspecs endpoint without any modules available.

    Tests that the custom EBKernelSpecManager still finds the default kernels (echo and python3).
    """
    response = await jp_fetch('api/kernelspecs')

    assert response.code == 200

    response_dct = json.loads(response.body.decode())

    kernelspecs = response_dct.pop('kernelspecs', None)
    assert kernelspecs is not None, 'kernelspecs key not found in response'

    for kernel_name in DEFAULT_KERNELS:
        kernel = kernelspecs.pop(kernel_name, None)
        assert kernel is not None, f"{kernel_name} kernel not found in kernelspecs"

    # Only the expected kernels should be present, no additional kernels from modules
    assert len(kernelspecs) == 0

async def test_kernels_endpoint_one_module(jp_fetch, jupyter_server_module1):
    """Test the /api/kernelspecs endpoint with one jupyter-server module available."""
    response = await jp_fetch('api/kernelspecs')

    assert response.code == 200

    response_dct = json.loads(response.body.decode())

    kernelspecs = response_dct.pop('kernelspecs', None)
    assert kernelspecs is not None, 'kernelspecs key not found in response'

    for kernel_name in DEFAULT_KERNELS:
        kernel = kernelspecs.pop(kernel_name, None)
        assert kernel is not None, f"{kernel_name} kernel not found in kernelspecs"

    for module in [jupyter_server_module1]:
        expected_kernel_name = f"{module.name}__{module.version}"
        kernel = kernelspecs.pop(expected_kernel_name, None)
        assert kernel is not None, f"{expected_kernel_name} kernel not found in kernelspecs"

    # Only the expected kernels should be present, no additional kernels from modules
    assert len(kernelspecs) == 0

async def test_kernels_endpoint_multiple_module(jp_fetch, jupyter_server_module1, jupyter_server_module2):
    """Test the /api/kernelspecs endpoint with one jupyter-server module available."""
    response = await jp_fetch('api/kernelspecs')

    assert response.code == 200

    response_dct = json.loads(response.body.decode())

    kernelspecs = response_dct.pop('kernelspecs', None)
    assert kernelspecs is not None

    echo_kernel = kernelspecs.pop('echo', None)
    assert echo_kernel is not None

    py3_kernel = kernelspecs.pop('python3', None)
    assert py3_kernel is not None


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

    response = await jp_fetch('api/kernelspecs')

    assert response.code == 200

    response_dct = json.loads(response.body.decode())

    kernelspecs = response_dct.pop('kernelspecs', None)
    assert kernelspecs is not None

    echo_kernel = kernelspecs.pop('echo', None)
    assert echo_kernel is not None

    py3_kernel = kernelspecs.pop('python3', None)
    assert py3_kernel is not None

    for module in [jupyter_server_module1, jupyter_server_module2, jupyter_server_module3]:
        if module.pyver == expected_pyver:
            expected_kernel_name = f"{module.name}__{module.version}"
            m1_kernel = kernelspecs.pop(expected_kernel_name, None)
            assert m1_kernel is not None, f"{expected_kernel_name} kernel not found in kernelspecs"

    # Only the expected kernels should be present, no additional kernels from modules
    assert len(kernelspecs) == 0
