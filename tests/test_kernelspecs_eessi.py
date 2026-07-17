"""Tests for checking if the custom kernelspec manager finds the expected kernels from EasyBuild's `jupyter-server`
modules."""
import pytest
from commons import EESSI_PREFIX, kernelspec_response_common

from easybuild_jupyter_kernels import environment as env


@pytest.mark.skipif(EESSI_PREFIX is None, reason='EESSI environment not detected')
async def test_eessi_kernels_endpoint(jp_fetch):
    """Test the /api/kernelspecs endpoint within EESSI.
    `jupyter-server` modules should be found and all non-default kernels should derive from them.

    Tests that the custom EBKernelSpecManager still finds the default kernels (echo and python3).
    """
    kernelspecs = kernelspec_response_common(await jp_fetch('api/kernelspecs', request_timeout=120))

    assert len(kernelspecs) > 0, 'No kernelspecs found from jupyter-server modules in EESSI'

    assert all(_['spec']['argv'][0].startswith(EESSI_PREFIX) for _ in kernelspecs.values()), \
        'Not all kernelspecs are from jupyter-server modules' + str(list(kernelspecs.keys()))

@pytest.mark.skipif(EESSI_PREFIX is None, reason='EESSI environment not detected')
async def test_eessi_kernels_init_2023(monkeypatch, jp_fetch):
    """Test the /api/kernelspecs endpoint within EESSI using EB_JUPYTER_KERNEL_INIT_MODULES.
    Setting init to 2023.06 should only find kernels from the 2023.06 stack
    """
    monkeypatch.setenv(env.INIT_MODULES_ENV_NAME, 'EESSI/2023.06')
    kernelspecs = kernelspec_response_common(await jp_fetch('api/kernelspecs', request_timeout=120))

    assert len(kernelspecs) > 0, 'No kernelspecs found from jupyter-server modules in EESSI 2023.06'

    prefix = '/cvmfs/software.eessi.io/versions/2023.06'
    assert all(_['spec']['argv'][0].startswith(prefix) for _ in kernelspecs.values()), \
        'Not all kernelspecs are from jupyter-server modules' + str(list(kernelspecs.keys()))

@pytest.mark.skipif(EESSI_PREFIX is None, reason='EESSI environment not detected')
async def test_eessi_kernels_init_2025(monkeypatch, jp_fetch):
    """Test the /api/kernelspecs endpoint within EESSI using EB_JUPYTER_KERNEL_INIT_MODULES.
    Setting init to 2025.06 should only find kernels from the 2025.06 stack
    """
    monkeypatch.setenv(env.INIT_MODULES_ENV_NAME, 'EESSI/2025.06')
    kernelspecs = kernelspec_response_common(await jp_fetch('api/kernelspecs', request_timeout=120))

    assert len(kernelspecs) > 0, 'No kernelspecs found from jupyter-server modules in EESSI 2025.06'

    prefix = '/cvmfs/software.eessi.io/versions/2025.06'
    assert all(_['spec']['argv'][0].startswith(prefix) for _ in kernelspecs.values()), \
        'Not all kernelspecs are from jupyter-server modules' + str(list(kernelspecs.keys()))

@pytest.mark.skipif(EESSI_PREFIX is None, reason='EESSI environment not detected')
async def test_eessi_kernels_init_2023_2025(monkeypatch, jp_fetch):
    """Test the /api/kernelspecs endpoint within EESSI using EB_JUPYTER_KERNEL_INIT_MODULES.
    Setting init to both 2023.06 and 2025.06 should find kernels from both stack
    """
    monkeypatch.setenv(env.INIT_MODULES_ENV_NAME, 'EESSI/2023.06,EESSI/2025.06')
    kernelspecs = kernelspec_response_common(await jp_fetch('api/kernelspecs', request_timeout=120))

    assert len(kernelspecs) > 0, 'No kernelspecs found from jupyter-server modules in EESSI 2025.06'

    prefix = '/cvmfs/software.eessi.io/versions/2023.06'
    found_2023 = any(_['spec']['argv'][0].startswith(prefix) for _ in kernelspecs.values())
    assert found_2023, 'No kernelspecs found from jupyter-server modules in EESSI 2023.06'

    prefix = '/cvmfs/software.eessi.io/versions/2025.06'
    found_2025 = any(_['spec']['argv'][0].startswith(prefix) for _ in kernelspecs.values())
    assert found_2025, 'No kernelspecs found from jupyter-server modules in EESSI 2025.06'
