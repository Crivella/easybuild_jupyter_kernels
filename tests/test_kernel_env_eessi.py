"""Tests to check that the the kernels are started with the correct environment variables"""
import pytest
from commons import EESSI_PREFIX, get_kernel_execution_result
from jupyter_client.asynchronous.client import AsyncKernelClient


@pytest.mark.skipif(EESSI_PREFIX is None, reason='EESSI environment not detected')
async def test_eessi_kernel_env(eb_async_kernel_manager, jp_start_kernel):
    """Test that the kernel is started with the correct environment variables in EESSI"""
    if '2023.06' in EESSI_PREFIX:
        kernel_name = 'jupyter-server__2.14.0-GCCcore-13.2.0'
    elif '2025.06' in EESSI_PREFIX:
        kernel_name = 'jupyter-server__2.17.0-GCCcore-14.3.0'
    else:
        raise ValueError('Unsupported version of EESSI')

    _, kclient = await jp_start_kernel(kernel_name=kernel_name)
    kclient: AsyncKernelClient

    for envvar in ['EBPYTHONPREFIXES', 'PYTHONPATH', 'LD_LIBRARY_PATH']:
        kernel_env_value = await get_kernel_execution_result(
            kclient,
            f"import os; print(os.environ.get('{envvar}'))"
        )
        if EESSI_PREFIX in kernel_env_value:
            break
    else:
        raise AssertionError(f"EESSI_PREFIX {EESSI_PREFIX} not found in kernel environment variables")
