"""Fixtures for the tests."""
import importlib
import os
import shutil
from dataclasses import dataclass
from typing import Callable, Tuple

import pytest
from jupyter_client import manager
from jupyter_client.manager import AsyncKernelManager

from easybuild_jupyter_kernels import kernelspec
from easybuild_jupyter_kernels.kernelspec import EBKernelSpecManager

pytest_plugins = ['pytest_jupyter.jupyter_server', 'pytest_jupyter.jupyter_client']

JUPYTER_SERVER_MODULE_TEMPLATE_LUA = """
setenv("EBVERSIONPYTHON", "{py_version}")
setenv("EBROOTJUPYTERMINSERVER", "{prefix}")
prepend_path("PYTHONPATH", "{prefix}/lib/python{py_version}/site-packages")
prepend_path("EBPYTHONPREFIXES", "{prefix}")
prepend_path("LD_LIBRARY_PATH", "{prefix}/lib")
"""

JULIA_MODULE_TEMPLATE_LUA = """
setenv("EBROOTIJULIA", "{prefix}")
setenv("EBVERSIONJULIA", "{julia_version}")
setenv("EBVERSIONIJULIA", "{ijulia_version}")
setenv("JULIA_DEPOT_PATH", "{prefix}/julia_depot")
setenv("JULIA_LOAD_PATH", "{prefix}/julia_load")
"""

OCTAVE_MODULE_TEMPLATE_LUA = """
setenv("EBROOTOCTAVEMINKERNEL", "{prefix}")
setenv("EBVERSIONPYTHON", "{py_version}")
setenv("EBVERSIONOCTAVE", "{octave_version}")
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

@pytest.fixture
def mock_display_prefix(monkeypatch) -> str:
    """Fixture to mock the EB_JUPYTER_KERNEL_DISPLAY_PREFIX environment variable."""
    prefix = 'TEST_ABC'
    monkeypatch.setenv('EB_JUPYTER_KERNEL_DISPLAY_PREFIX', prefix)
    importlib.reload(kernelspec)  # Reload the kernelspec module to apply the new environment variable
    return prefix

@pytest.fixture
def lmod_environment(monkeypatch, tmpdir):
    """Set up a mock Lmod environment for testing."""
    # Create a temporary directory to simulate the Lmod environment
    lmod_dir = tmpdir.ensure('lmod', dir=True)

    monkeypatch.setenv('MODULEPATH', str(lmod_dir))

    return lmod_dir

@pytest.fixture
def mock_julia(monkeypatch, tmpdir):
    """Fixture to mock the Julia executable for testing."""
    bindir = tmpdir.ensure('bin_julia', dir=True)
    julia_path = bindir.ensure('julia', dir=False)
    julia_path.chmod(0o755)

    path = [str(bindir)] + os.environ.get('PATH', '').split(os.pathsep)
    monkeypatch.setenv('PATH', os.pathsep.join(path))

@pytest.fixture
def mock_octave(monkeypatch, tmpdir):
    """Fixture to mock the Octave executable for testing."""
    bindir = tmpdir.ensure('bin_octave', dir=True)
    octave_path = bindir.ensure('octave', dir=False)
    octave_path.chmod(0o755)

    path = [str(bindir)] + os.environ.get('PATH', '').split(os.pathsep)
    monkeypatch.setenv('PATH', os.pathsep.join(path))

@pytest.fixture
def jupyter_server_module_factory(tmpdir, lmod_environment) -> Callable[[str, str], tuple[str, str]]:
    """Factory fixture to create mock Jupyter server modules for testing."""
    def create_module(mod_ver: str, py_ver: str = '3.8') -> Tuple[str, str]:
        modulename = 'jupyter-server'
        root_path = tmpdir.ensure(f"jupyter-server-{mod_ver}", dir=True)
        root_path.ensure('share/jupyter/kernels/python3', dir=True)
        modulefile_content = JUPYTER_SERVER_MODULE_TEMPLATE_LUA.format(
            py_version=py_ver,
            prefix=str(root_path)
        )
        modulefile_path = lmod_environment.ensure(modulename, dir=True).join(f"{mod_ver}.lua")

        modulefile_path.write(modulefile_content)

        return modulefile_path, root_path
    return create_module

@pytest.fixture
def ijulia_module_factory(tmpdir, lmod_environment, mock_julia) -> Callable[[str, str], tuple[str, str]]:
    """Factory fixture to create mock IJulia modules for testing."""
    def create_module(ijulia_ver: str, julia_ver: str = '1.6') -> Tuple[str, str]:
        modulename = 'IJulia'
        root_path = tmpdir.ensure(f"ijulia-{ijulia_ver}", dir=True)
        root_path.ensure(f"jupyter/kernels/julia-{julia_ver}", dir=True)
        modulefile_content = JULIA_MODULE_TEMPLATE_LUA.format(
            ijulia_version=ijulia_ver,
            julia_version=julia_ver,
            prefix=str(root_path)
        )
        modulefile_path = lmod_environment.ensure(modulename, dir=True).join(f"{ijulia_ver}.lua")

        modulefile_path.write(modulefile_content)

        return modulefile_path, root_path
    return create_module

@pytest.fixture
def octave_module_factory(tmpdir, lmod_environment, mock_octave) -> Callable[[str], tuple[str, str]]:
    """Factory fixture to create mock Octave modules for testing."""
    def create_module(mod_ver: str, octave_ver: str, py_ver: str = '3.8') -> Tuple[str, str]:
        modulename = 'octave-kernel'
        root_path = tmpdir.ensure(f"octave-kernel-{mod_ver}", dir=True)
        root_path.ensure('share/jupyter/kernels/octave', dir=True)
        modulefile_content = OCTAVE_MODULE_TEMPLATE_LUA.format(
            py_version=py_ver,
            octave_version=octave_ver,
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
def ijulia_module1(ijulia_module_factory) -> ModuleInfo:
    """Add a mock IJulia module to the MODULEPATH."""
    mod_name, ijulia_ver, julia_ver = 'IJulia', '0.3', '1.6'
    modulefile_path, root_path = ijulia_module_factory(ijulia_ver, julia_ver)

    yield ModuleInfo(
        name=mod_name,
        version=ijulia_ver,
        mod_path=str(modulefile_path),
        root_path=str(root_path),
        pyver=julia_ver,
    )

    modulefile_path.remove()
    root_path.remove()

@pytest.fixture
def octave_module1(octave_module_factory) -> ModuleInfo:
    """Add a mock Octave module to the MODULEPATH."""
    mod_name, mod_ver, octave_ver, py_ver = 'octave-kernel', '1', '6.4', '3.8'
    modulefile_path, root_path = octave_module_factory(mod_ver, octave_ver, py_ver)

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
