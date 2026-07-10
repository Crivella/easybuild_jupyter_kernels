"""Common utilities for testing Jupyter kernel execution."""
import asyncio
import json
import os

from jupyter_client.asynchronous.client import AsyncKernelClient

DEFAULT_KERNELS = ['echo', 'python3']

EESSI_PREFIX = os.environ.get('EESSI_PREFIX', None)


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
