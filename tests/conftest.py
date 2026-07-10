"""Fixtures for the tests."""
import importlib
import os
import shutil
from collections.abc import Generator
from dataclasses import dataclass
from typing import Callable, Tuple

import pytest
from jupyter_client import manager
from jupyter_client.manager import AsyncKernelManager

from easybuild_jupyter_kernels import kernelspec
from easybuild_jupyter_kernels.kernelspec import (
    CLING_CPP_STDS, EBKernelSpecManager,
)

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

ROOTCPP_MODULE_TEMPLATE_LUA = """
setenv("EBROOTROOT", "{prefix}")
setenv("EBVERSIONPYTHON", "{py_version}")
setenv("EBVERSIONROOT", "{root_version}")
prepend_path("PYTHONPATH", "{prefix}/lib/python{py_version}/site-packages")
prepend_path("EBPYTHONPREFIXES", "{prefix}")
prepend_path("LD_LIBRARY_PATH", "{prefix}/lib")
"""

IRKERNEL_MODULE_TEMPLATE_LUA = """
setenv("EBVERSIONR", "{r_version}")
setenv("EBROOTIRKERNEL", "{prefix}")
prepend_path("R_LIBS_SITE", "{prefix}/lib/R/site-library")
"""

CLING_KERNEL_MODULE_TEMPLATE_LUA = """
setenv("EBVERSIONCLING", "{cling_version}")
setenv("EBROOTCLINGMINKERNEL", "{prefix}")
"""

JUPYTER_BASH_KERNEL_TEMPLATE_LUA = """
setenv("EBVERSIONPYTHON", "{py_version}")
setenv("EBROOTJUPYTERMINBASHMINKERNEL", "{prefix}")
setenv("EBVERSIONJUPYTERMINBASHMINKERNEL", "{jpk_bash_version}")
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
    kname: str = None
    pyver: str = None

    def __post_init__(self):
        if not self.kname:
            self.kname = self.name


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

def mock_exec(monkeypatch, tmpdir, name):
    """Helper function to create a mock executable in a temporary directory."""
    bindir = tmpdir.ensure(f'bin_{name}', dir=True)
    exec_path = bindir.ensure(name, dir=False)
    exec_path.chmod(0o755)

    path = [str(bindir)] + os.environ.get('PATH', '').split(os.pathsep)
    monkeypatch.setenv('PATH', os.pathsep.join(path))

@pytest.fixture
def mock_julia(monkeypatch, tmpdir):
    """Fixture to mock the Julia executable for testing."""
    mock_exec(monkeypatch, tmpdir, 'julia')

@pytest.fixture
def mock_r(monkeypatch, tmpdir):
    """Fixture to mock the R executable for testing."""
    mock_exec(monkeypatch, tmpdir, 'R')

@pytest.fixture
def mock_jupyter_cling_kernel(monkeypatch, tmpdir):
    """Fixture to mock the cling kernel executable for testing."""
    mock_exec(monkeypatch, tmpdir, 'jupyter-cling-kernel')

@pytest.fixture
def module_factory(tmpdir, lmod_environment) -> Callable[[str, str, str, list[str], dict[str, str]], tuple[str, str]]:
    """Factory fixture to create mock Jupyter server modules for testing."""
    def create_module(
            mod_name: str, mod_ver: str, template: str, prefix_dirs: list[str],
            format_dct: dict[str, str]
        ) -> Tuple[str, str]:
        """Helper function to create a mock module

        Parameters:
            mod_name (str): Name of the module.
            mod_ver (str): Version of the module.
            template (str): Template for the modulefile content.
            prefix_dirs (list[str]): List of directories to create/expected to exists under the module's root path.
            format_dct (dict[str, str]): Dictionary of values to format the template with.
        """
        root_path = tmpdir.ensure(f"{mod_name}-{mod_ver}", dir=True)
        for rel_pth in prefix_dirs:
            root_path.ensure(rel_pth, dir=True)
        format_dct['prefix'] = str(root_path)
        modulefile_content = template.format(**format_dct)

        modulefile_path = lmod_environment.ensure(mod_name, dir=True).join(f"{mod_ver}.lua")
        modulefile_path.write(modulefile_content)

        return modulefile_path, root_path
    return create_module

@pytest.fixture(autouse=True)
def clear_kernel_data_cache(monkeypatch):
    """Clear the lru_cache used to generate KernelData from a module-ModuleKernelMapping combo to avoid re-using a
    module loaded from a previous test"""
    kernelspec.KernelData.from_env_module.cache_clear()

@pytest.fixture
def jupyter_server_module1(module_factory) -> Generator[ModuleInfo, None, None]:
    """Add a mock Jupyter server module to the MODULEPATH."""
    mod_name, mod_ver, py_ver = 'jupyter-server', '1', '3.8'
    modulefile_path, root_path = module_factory(
        mod_name, mod_ver, JUPYTER_SERVER_MODULE_TEMPLATE_LUA,
        ['share/jupyter/kernels/python3'],
        {'py_version': py_ver}
    )

    yield ModuleInfo(
        name=mod_name,
        version=mod_ver,
        mod_path=str(modulefile_path),
        root_path=str(root_path),
        pyver=py_ver,
    )

    print('MODULEPATH:', os.getenv('MODULEPATH'))

    modulefile_path.remove()
    root_path.remove()

@pytest.fixture
def jupyter_server_module2(module_factory) -> Generator[ModuleInfo, None, None]:
    """Add a mock Jupyter server module to the MODULEPATH."""
    mod_name, mod_ver, py_ver = 'jupyter-server', '2', '3.9'
    modulefile_path, root_path = module_factory(
        mod_name, mod_ver, JUPYTER_SERVER_MODULE_TEMPLATE_LUA,
        ['share/jupyter/kernels/python3'],
        {'py_version': py_ver}
    )

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
def jupyter_server_module3(module_factory) -> Generator[ModuleInfo, None, None]:
    """Add a mock Jupyter server module to the MODULEPATH."""
    mod_name, mod_ver, py_ver = 'jupyter-server', '3', '3.8'
    modulefile_path, root_path = module_factory(
        mod_name, mod_ver, JUPYTER_SERVER_MODULE_TEMPLATE_LUA,
        ['share/jupyter/kernels/python3'],
        {'py_version': py_ver}
    )

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
def ijulia_module1(module_factory, mock_julia) -> Generator[ModuleInfo, None, None]:
    """Add a mock IJulia module to the MODULEPATH."""
    mod_name, ijulia_ver, julia_ver = 'IJulia', '0.3', '1.6'
    modulefile_path, root_path = module_factory(
        mod_name, ijulia_ver, JULIA_MODULE_TEMPLATE_LUA,
        [f'jupyter/kernels/julia-{julia_ver}'],
        {'ijulia_version': ijulia_ver, 'julia_version': julia_ver}
    )

    yield ModuleInfo(
        name=mod_name,
        version=ijulia_ver,
        mod_path=str(modulefile_path),
        root_path=str(root_path),
    )

    modulefile_path.remove()
    root_path.remove()

@pytest.fixture
def octave_module1(module_factory) -> Generator[ModuleInfo, None, None]:
    """Add a mock Octave module to the MODULEPATH."""
    mod_name, mod_ver, octave_ver, py_ver = 'octave-kernel', '1', '6.4', '3.8'
    modulefile_path, root_path = module_factory(
        mod_name, mod_ver, OCTAVE_MODULE_TEMPLATE_LUA,
        ['share/jupyter/kernels/octave/images'],
        {'octave_version': octave_ver, 'py_version': py_ver}
    )

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
def rootkernel_module1(module_factory) -> Generator[ModuleInfo, None, None]:
    """Add a mock root-kernel module to the MODULEPATH."""
    mod_name, mod_ver, root_ver, py_ver = 'root-kernel', '1', '6.26', '3.8'
    modulefile_path, root_path = module_factory(
        mod_name, mod_ver, ROOTCPP_MODULE_TEMPLATE_LUA,
        ['etc/notebook/kernels/root/'],
        {'root_version': root_ver, 'py_version': py_ver}
    )

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
def irkernel_module1(module_factory, mock_r) -> Generator[ModuleInfo, None, None]:
    """Add a mock IRkernel module to the MODULEPATH."""
    mod_name, mod_ver, r_ver = 'IRkernel', '1', '4.2'
    modulefile_path, root_path = module_factory(
        mod_name, mod_ver, IRKERNEL_MODULE_TEMPLATE_LUA,
        ['IRkernel/kernelspec/'],
        {'r_version': r_ver}
    )

    yield ModuleInfo(
        name=mod_name,
        version=mod_ver,
        mod_path=str(modulefile_path),
        root_path=str(root_path),
    )

    modulefile_path.remove()
    root_path.remove()

@pytest.fixture
def cling_module1(module_factory) -> Generator[ModuleInfo, None, None]:
    """Add a mock cling module to the MODULEPATH."""
    mod_name, mod_ver, cling_ver = 'cling-kernel', '1', '1.2.3'
    modulefile_path, root_path = module_factory(
        mod_name, mod_ver, CLING_KERNEL_MODULE_TEMPLATE_LUA,
        [f'share/jupyter/kernels/cling-cpp{std}/' for std in CLING_CPP_STDS],
        {'cling_version': cling_ver}
    )

    yield ModuleInfo(
        name=mod_name,
        kname='cling',
        version=mod_ver,
        mod_path=str(modulefile_path),
        root_path=str(root_path),
    )

    modulefile_path.remove()
    root_path.remove()

@pytest.fixture
def jpk_bash_module1(module_factory) -> Generator[ModuleInfo, None, None]:
    """Add a mock jpk-bash module to the MODULEPATH."""
    mod_name, mod_ver, py_ver = 'jupyter-bash-kernel', '1', '3.8'
    modulefile_path, root_path = module_factory(
        mod_name, mod_ver, JUPYTER_BASH_KERNEL_TEMPLATE_LUA,
        ['share/jupyter/kernels/bash'],
        {'py_version': py_ver, 'jpk_bash_version': mod_ver}
    )

    yield ModuleInfo(
        name=mod_name,
        kname='bash',
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
