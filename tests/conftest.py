"""Fixtures for the tests."""
import os
import shutil
from dataclasses import dataclass
from typing import Callable, Tuple

import pytest
from jupyter_client import manager
from jupyter_client.manager import AsyncKernelManager

from easybuild_jupyter_kernels.kernelspec import EBKernelSpecManager

pytest_plugins = ['pytest_jupyter.jupyter_server', 'pytest_jupyter.jupyter_client']

JUPYTER_SERVER_MODULE_TEMPLATE_LUA = """
setenv("EBVERSIONPYTHON", "{py_version}")
prepend_path("PYTHONPATH", "{prefix}/lib/python{py_version}/site-packages")
prepend_path("EBPYTHONPREFIXES", "{prefix}")
prepend_path("LD_LIBRARY_PATH", "{prefix}/lib")
"""

def has_lmod():
    """Check if Lmod is available in the environment."""
    lmod_cmd = os.environ.get('LMOD_CMD')

    if not lmod_cmd:
        lmod_cmd = shutil.which('lmod')

    return bool(lmod_cmd)

@dataclass
class ModuleInfo:
    """Data class to hold information about a mock module created for testing."""
    name: str
    version: str
    mod_path: str
    root_path: str
    pyver: str


@pytest.fixture
def jp_server_config():
    """Configure the test server to use EBKernelSpecManager as the kernel manager."""
    return {
        'ServerApp': {
            'kernel_spec_manager_class': 'easybuild_jupyter_kernels.kernelspec.EBKernelSpecManager',
        },
    }


@pytest.fixture(scope='session', autouse=True)
def lmod_environment(tmpdir_factory):
    """Set up a mock Lmod environment for testing."""
    # Create a temporary directory to simulate the Lmod environment
    lmod_dir = tmpdir_factory.mktemp('lmod')

    previous_modulepath = os.environ.get('MODULEPATH', '')
    os.environ['MODULEPATH'] = str(lmod_dir)

    yield lmod_dir

    os.environ['MODULEPATH'] = previous_modulepath


@pytest.fixture
def jupyter_server_module_factory(tmpdir, lmod_environment) -> Callable[[str, str], tuple[str, str]]:
    """Factory fixture to create mock Jupyter server modules for testing."""
    def create_module(mod_ver: str, py_ver: str = '3.8') -> Tuple[str, str]:
        modulename = 'jupyter-server'
        root_path = tmpdir.ensure(f"jupyter-server-{mod_ver}", dir=True)
        modulefile_content = JUPYTER_SERVER_MODULE_TEMPLATE_LUA.format(
            py_version=py_ver,
            prefix=str(root_path)
        )
        modulefile_path = lmod_environment.ensure(modulename, dir=True).join(f"{mod_ver}.lua")

        modulefile_path.write(modulefile_content)

        return modulefile_path, root_path
    return create_module

@pytest.fixture
def jupyter_server_module1(jupyter_server_module_factory) -> ModuleInfo:
    """Add a mock Jupyter server module to the MODULEPATH."""
    mod_name, mod_ver, py_ver = 'jupyter-server', '1', '3.8'
    modulefile_path, root_path = jupyter_server_module_factory(mod_ver, py_ver)

    yield ModuleInfo(
        name=mod_name,
        version=mod_ver,
        mod_path=str(modulefile_path),
        root_path=str(root_path),
        pyver=py_ver,
    )

    modulefile_path.remove()
    root_path.remove()

@pytest.fixture
def jupyter_server_module2(jupyter_server_module_factory) -> ModuleInfo:
    """Add a mock Jupyter server module to the MODULEPATH."""
    mod_name, mod_ver, py_ver = 'jupyter-server', '2', '3.9'
    modulefile_path, root_path = jupyter_server_module_factory(mod_ver, py_ver)

    yield ModuleInfo(
        name=mod_name,
        version=mod_ver,
        mod_path=str(modulefile_path),
        root_path=str(root_path),
        pyver=py_ver,
    )

    modulefile_path.remove()
    root_path.remove()

@pytest.fixture
def jupyter_server_module3(jupyter_server_module_factory) -> ModuleInfo:
    """Add a mock Jupyter server module to the MODULEPATH."""
    mod_name, mod_ver, py_ver = 'jupyter-server', '3', '3.8'
    modulefile_path, root_path = jupyter_server_module_factory(mod_ver, py_ver)

    yield ModuleInfo(
        name=mod_name,
        version=mod_ver,
        mod_path=str(modulefile_path),
        root_path=str(root_path),
        pyver=py_ver,
    )

    modulefile_path.remove()
    root_path.remove()

@pytest.fixture
def eb_async_kernel_manager(monkeypatch):
    """A fixture that returns an AsyncKernelManager instance configured to use EBKernelSpecManager."""
    class CustomAsyncKernelManager(AsyncKernelManager):
        """Custom AsyncKernelManager that uses EBKernelSpecManager for kernel spec management."""
        def _kernel_spec_manager_default(self):
            return EBKernelSpecManager(parent=self)

    # Inject the custom AsyncKernelManager into the jupyter_client.manager module
    monkeypatch.setattr(manager, 'AsyncKernelManager', CustomAsyncKernelManager)

    return CustomAsyncKernelManager
