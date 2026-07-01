"""Tests to check that the the kernels are started with the correct environment variables"""
import os

from commons import get_kernel_execution_result
from jupyter_client.asynchronous.client import AsyncKernelClient


async def test_kernel_env_no_module(jp_start_kernel):
    """Test that the kernel is started with the correct environment variables when no module is loaded."""
    _, kclient = await jp_start_kernel()
    kclient: AsyncKernelClient

    for envvar in ['EBPYTHONPREFIXES', 'PYTHONPATH', 'LD_LIBRARY_PATH']:
        kernel_env_value = await get_kernel_execution_result(
            kclient,
            f"import os; print(os.environ.get('{envvar}'))"
        )
        expected_env_value = str(os.environ.get(envvar))
        assert kernel_env_value == expected_env_value, \
            f"Expected {envvar} to be {expected_env_value}, but got {kernel_env_value}"

async def test_kernel_env_with_module(eb_async_kernel_manager, jp_start_kernel, jupyter_server_module1):
    """Test that the kernel is started with the module prefix in the environment variables."""
    # monkeypatch.setattr(manager, 'AsyncKernelManager', EBKernelSpecManager)
    kernel_name = f"{jupyter_server_module1.name}__{jupyter_server_module1.version}"
    _, kclient = await jp_start_kernel(kernel_name=kernel_name)

    for envvar in ['EBPYTHONPREFIXES', 'PYTHONPATH', 'LD_LIBRARY_PATH']:
        kernel_env_value = await get_kernel_execution_result(
            kclient,
            f"import os; print(os.environ.get('{envvar}'))"
        )

        expected_env_value = str(jupyter_server_module1.root_path)
        assert jupyter_server_module1.root_path in kernel_env_value, \
            f"Expected {envvar} to be {expected_env_value}, but got {kernel_env_value}"
