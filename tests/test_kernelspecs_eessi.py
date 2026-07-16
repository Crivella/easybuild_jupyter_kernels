"""Tests for checking if the custom kernelspec manager finds the expected kernels from EasyBuild's `jupyter-server`
modules."""
import json

import pytest
from commons import DEFAULT_KERNELS, EESSI_PREFIX


@pytest.mark.skipif(EESSI_PREFIX is None, reason='EESSI environment not detected')
async def test_eessi_kernels_endpoint(jp_fetch):
    """Test the /api/kernelspecs endpoint within EESSI.
    `jupyter-server` modules should be found and all non-default kernels should derive from them.

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

    assert len(kernelspecs) > 0, 'No kernelspecs found from jupyter-server modules in EESSI'

    assert all(_['spec']['argv'][0].startswith(EESSI_PREFIX) for _ in kernelspecs.values()), \
        'Not all kernelspecs are from jupyter-server modules' + str(kernelspecs.keys())
