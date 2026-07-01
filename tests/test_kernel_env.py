"""Tests to check that the the kernels are started with the correct environment variables"""
import asyncio
import os

from jupyter_client.asynchronous.client import AsyncKernelClient


async def get_kernel_execution_result(kclient: AsyncKernelClient, code: str, timeout: float = 10.0) -> str:
    """Execute code in the kernel and return the result."""
    msg_id = kclient.execute(code, reply=False)

    res = []

    start_time = asyncio.get_event_loop().time()

    while True:
        remaining_time = timeout - (asyncio.get_event_loop().time() - start_time)
        if remaining_time <= 0:
            raise TimeoutError(f"Timeout while waiting for kernel execution result for code: {code}")

        msg = await kclient.get_iopub_msg(timeout=remaining_time)
        if msg['parent_header'].get('msg_id') != msg_id:
            continue

        msg_type = msg['header']['msg_type']
        content = msg['content']

        # stdout/stderr
        if msg_type == 'stream':
            res.append(content['text'])

        # value of last expression
        elif msg_type == 'execute_result':
            res.append(content['data']['text/plain'])

        # rich display output
        elif msg_type == 'display_data':
            res.append(content['data'])

        # error
        elif msg_type == 'error':
            res.append('\n'.join(content['traceback']))

        elif msg_type == 'status' and content['execution_state'] == 'idle':
            break

    return ''.join(res).strip()


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
