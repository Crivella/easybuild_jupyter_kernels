"""Fixtures for the tests."""
import os
import shutil
from collections.abc import Generator
from typing import Callable, Tuple

import module_templates as mod_tpl
import pytest
from commons import ModuleInfo
from jupyter_client import manager
from jupyter_client.manager import AsyncKernelManager

from easybuild_jupyter_kernels import kernelspec
from easybuild_jupyter_kernels.kernelspec import CLING_CPP_STDS, EBKernelSpecManager

pytest_plugins = ['pytest_jupyter.jupyter_server', 'pytest_jupyter.jupyter_client']

def has_lmod():
    """Check if Lmod is available in the environment."""
    lmod_cmd = os.environ.get('LMOD_CMD')

    if not lmod_cmd:
        lmod_cmd = shutil.which('lmod')

    return bool(lmod_cmd)

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
    return prefix

@pytest.fixture
def lmod_environment(monkeypatch, tmpdir):
    """Set up a mock Lmod environment with the proper MODULEPATH for testing."""
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
def module_factory(
        tmpdir
    ) -> Generator[Callable[[str, str, str, list[str], dict[str, str]], tuple[str, str]], None, None]:
    """Factory fixture to create mock Jupyter server modules for testing."""
    cleanup_dirs = []
    def create_module(
            lmod_dir,
            mod_name: str, mod_ver: str, template: str, prefix_dirs: list[str] = None,
            format_dct: dict[str, str] = None
        ) -> Tuple[str, str]:
        """Helper function to create a mock module

        Parameters:
            mod_name (str): Name of the module.
            mod_ver (str): Version of the module.
            template (str): Template for the modulefile content.
            prefix_dirs (list[str]): List of directories to create/expected to exists under the module's root path.
            format_dct (dict[str, str]): Dictionary of values to format the template with.
        """
        prefix_dirs = prefix_dirs or []
        format_dct = format_dct or {}

        root_path = tmpdir.ensure(f"{mod_name}-{mod_ver}", dir=True)
        for rel_pth in prefix_dirs:
            root_path.ensure(rel_pth, dir=True)
        format_dct['prefix'] = str(root_path)
        modulefile_content = template.format(**format_dct)

        modulefile_path = lmod_dir.ensure(mod_name, dir=True).join(f"{mod_ver}.lua")
        modulefile_path.write(modulefile_content)

        cleanup_dirs.append(root_path)
        cleanup_dirs.append(modulefile_path)

        return modulefile_path, root_path

    yield create_module

    for dir_path in cleanup_dirs:
        if dir_path.exists():
            dir_path.remove()

@pytest.fixture(autouse=True)
def clear_kernel_data_cache(monkeypatch):
    """Clear the lru_cache used to generate KernelData from a module-ModuleKernelMapping combo to avoid re-using a
    module loaded from a previous test"""
    kernelspec.KernelData.from_env_module.cache_clear()

@pytest.fixture
def submodule_environment1(module_factory, lmod_environment) -> tuple[str, ModuleInfo]:
    """Simulate a hierarchical module scheme where submodule has to be loaded before other modules can be seen"""
    mod_name, mod_ver = 'submodule', '1'
    modulefile_path, root_path = module_factory(lmod_environment, mod_name, mod_ver, mod_tpl.SUBMODULE_TEMPLATE_LUA,)

    info = ModuleInfo(
        name=mod_name,
        version=mod_ver,
        mod_path=str(modulefile_path),
        root_path=str(root_path),
    )

    return root_path, info

@pytest.fixture
def submodule_environment2(module_factory, lmod_environment) -> tuple[str, ModuleInfo]:
    """Simulate a hierarchical module scheme where submodule has to be loaded before other modules can be seen"""
    mod_name, mod_ver = 'submodule', '2'
    modulefile_path, root_path = module_factory(lmod_environment, mod_name, mod_ver, mod_tpl.SUBMODULE_TEMPLATE_LUA,)

    info = ModuleInfo(
        name=mod_name,
        version=mod_ver,
        mod_path=str(modulefile_path),
        root_path=str(root_path),
    )

    return root_path, info


@pytest.fixture
def jupyter_server_module1(module_factory, lmod_environment) -> ModuleInfo:
    """Add a mock Jupyter server module to the MODULEPATH"""
    mod_name, mod_ver, py_ver = 'jupyter-server', '1', '3.8'
    modulefile_path, root_path = module_factory(
        lmod_environment,
        mod_name, mod_ver, mod_tpl.JUPYTER_SERVER_MODULE_TEMPLATE_LUA,
        ['share/jupyter/kernels/python3'],
        {'py_version': py_ver}
    )

    return ModuleInfo(
        name=mod_name,
        version=mod_ver,
        mod_path=str(modulefile_path),
        root_path=str(root_path),
        pyver=py_ver,
    )

@pytest.fixture
def jupyter_server_module2(module_factory, lmod_environment) -> ModuleInfo:
    """Add a mock Jupyter server module to the MODULEPATH with LOWER launcher semver than 1"""
    mod_name, mod_ver, py_ver = 'jupyter-server', '2', '3.71'
    modulefile_path, root_path = module_factory(
        lmod_environment,
        mod_name, mod_ver, mod_tpl.JUPYTER_SERVER_MODULE_TEMPLATE_LUA,
        ['share/jupyter/kernels/python3'],
        {'py_version': py_ver}
    )

    return ModuleInfo(
        name=mod_name,
        version=mod_ver,
        mod_path=str(modulefile_path),
        root_path=str(root_path),
        pyver=py_ver,
    )

@pytest.fixture
def jupyter_server_module3(module_factory, lmod_environment) -> ModuleInfo:
    """Add a mock Jupyter server module to the MODULEPATH with same launcher semver as 1 but different kernel version"""
    mod_name, mod_ver, py_ver = 'jupyter-server', '3', '3.8'
    modulefile_path, root_path = module_factory(
        lmod_environment,
        mod_name, mod_ver, mod_tpl.JUPYTER_SERVER_MODULE_TEMPLATE_LUA,
        ['share/jupyter/kernels/python3'],
        {'py_version': py_ver}
    )

    return ModuleInfo(
        name=mod_name,
        version=mod_ver,
        mod_path=str(modulefile_path),
        root_path=str(root_path),
        pyver=py_ver,
    )

@pytest.fixture
def jupyter_server_module_sub1(module_factory, submodule_environment1) -> ModuleInfo:
    """Add a mock Jupyter server to the module environment without adding it to the MODULEPATH."""
    mod_name, mod_ver, py_ver = 'jupyter-server', '4', '3.8'
    lmod_dir, _ = submodule_environment1
    modulefile_path, root_path = module_factory(
        lmod_dir,
        mod_name, mod_ver, mod_tpl.JUPYTER_SERVER_MODULE_TEMPLATE_LUA,
        ['share/jupyter/kernels/python3'],
        {'py_version': py_ver}
    )

    return ModuleInfo(
        name=mod_name,
        version=mod_ver,
        mod_path=str(modulefile_path),
        root_path=str(root_path),
        pyver=py_ver,
    )

@pytest.fixture
def jupyter_server_module_sub2(module_factory, submodule_environment2) -> ModuleInfo:
    """Add a mock Jupyter server to the module environment without adding it to the MODULEPATH."""
    mod_name, mod_ver, py_ver = 'jupyter-server', '5', '3.8'
    lmod_dir, _ = submodule_environment2
    modulefile_path, root_path = module_factory(
        lmod_dir,
        mod_name, mod_ver, mod_tpl.JUPYTER_SERVER_MODULE_TEMPLATE_LUA,
        ['share/jupyter/kernels/python3'],
        {'py_version': py_ver}
    )

    return ModuleInfo(
        name=mod_name,
        version=mod_ver,
        mod_path=str(modulefile_path),
        root_path=str(root_path),
        pyver=py_ver,
    )

@pytest.fixture
def ijulia_module1(module_factory, lmod_environment, mock_julia) -> ModuleInfo:
    """Add a mock IJulia module to the MODULEPATH."""
    mod_name, ijulia_ver, julia_ver = 'IJulia', '0.3', '1.10.6'
    modulefile_path, root_path = module_factory(
        lmod_environment,
        mod_name, ijulia_ver, mod_tpl.JULIA_MODULE_TEMPLATE_LUA,
        [f'jupyter/kernels/julia-{julia_ver}'],
        {'ijulia_version': ijulia_ver, 'julia_version': julia_ver}
    )

    return ModuleInfo(
        name=mod_name,
        kname='IJulia_old',
        version=ijulia_ver,
        mod_path=str(modulefile_path),
        root_path=str(root_path),
    )

@pytest.fixture
def ijulia_module2(module_factory, lmod_environment, mock_julia) -> ModuleInfo:
    """Add a mock IJulia module to the MODULEPATH."""
    mod_name, ijulia_ver, julia_ver = 'IJulia', '0.4', '1.11.6'
    modulefile_path, root_path = module_factory(
        lmod_environment,
        mod_name, ijulia_ver, mod_tpl.JULIA_MODULE_TEMPLATE_LUA,
        [f'jupyter/kernels/julia-{julia_ver}'],
        {'ijulia_version': ijulia_ver, 'julia_version': julia_ver}
    )

    return ModuleInfo(
        name=mod_name,
        kname='IJulia_new',
        version=ijulia_ver,
        mod_path=str(modulefile_path),
        root_path=str(root_path),
    )

@pytest.fixture
def ijulia_module3(module_factory, lmod_environment, mock_julia) -> ModuleInfo:
    """Add a mock IJulia module to the MODULEPATH."""
    mod_name, ijulia_ver, julia_ver = 'IJulia', '0.2', '1.9.6'
    modulefile_path, root_path = module_factory(
        lmod_environment,
        mod_name, ijulia_ver, mod_tpl.JULIA_MODULE_TEMPLATE_LUA,
        [f'jupyter/kernels/julia-{julia_ver}'],
        {'ijulia_version': ijulia_ver, 'julia_version': julia_ver}
    )

    return ModuleInfo(
        name=mod_name,
        kname='IJulia_old',
        version=ijulia_ver,
        mod_path=str(modulefile_path),
        root_path=str(root_path),
    )

@pytest.fixture
def octave_module1(module_factory, lmod_environment) -> ModuleInfo:
    """Add a mock Octave module to the MODULEPATH."""
    mod_name, mod_ver, octave_ver, py_ver = 'octave-kernel', '1', '6.4', '3.8'
    modulefile_path, root_path = module_factory(
        lmod_environment,
        mod_name, mod_ver, mod_tpl.OCTAVE_MODULE_TEMPLATE_LUA,
        ['share/jupyter/kernels/octave/images'],
        {'octave_version': octave_ver, 'py_version': py_ver}
    )

    return ModuleInfo(
        name=mod_name,
        version=mod_ver,
        mod_path=str(modulefile_path),
        root_path=str(root_path),
        pyver=py_ver,
    )

@pytest.fixture
def rootkernel_module1(module_factory, lmod_environment) -> ModuleInfo:
    """Add a mock root-kernel module to the MODULEPATH."""
    mod_name, mod_ver, root_ver, py_ver = 'root-kernel', '1', '6.26', '3.8'
    modulefile_path, root_path = module_factory(
        lmod_environment,
        mod_name, mod_ver, mod_tpl.ROOTCPP_MODULE_TEMPLATE_LUA,
        ['etc/notebook/kernels/root/'],
        {'root_version': root_ver, 'py_version': py_ver}
    )

    return ModuleInfo(
        name=mod_name,
        version=mod_ver,
        mod_path=str(modulefile_path),
        root_path=str(root_path),
        pyver=py_ver,
    )

@pytest.fixture
def irkernel_module1(module_factory, lmod_environment, mock_r) -> ModuleInfo:
    """Add a mock IRkernel module to the MODULEPATH."""
    mod_name, mod_ver, r_ver = 'IRkernel', '1', '4.2'
    modulefile_path, root_path = module_factory(
        lmod_environment,
        mod_name, mod_ver, mod_tpl.IRKERNEL_MODULE_TEMPLATE_LUA,
        ['IRkernel/kernelspec/'],
        {'r_version': r_ver}
    )

    return ModuleInfo(
        name=mod_name,
        version=mod_ver,
        mod_path=str(modulefile_path),
        root_path=str(root_path),
    )

@pytest.fixture
def cling_module1(module_factory, lmod_environment) -> ModuleInfo:
    """Add a mock cling module to the MODULEPATH."""
    mod_name, mod_ver, cling_ver = 'cling-kernel', '1', '1.2.3'
    modulefile_path, root_path = module_factory(
        lmod_environment,
        mod_name, mod_ver, mod_tpl.CLING_KERNEL_MODULE_TEMPLATE_LUA,
        [f'share/jupyter/kernels/cling-cpp{std}/' for std in CLING_CPP_STDS],
        {'cling_version': cling_ver}
    )

    return ModuleInfo(
        name=mod_name,
        kname='cling',
        version=mod_ver,
        mod_path=str(modulefile_path),
        root_path=str(root_path),
    )

@pytest.fixture
def jpk_bash_module1(module_factory, lmod_environment) -> ModuleInfo:
    """Add a mock jpk-bash module to the MODULEPATH."""
    mod_name, mod_ver, py_ver = 'jupyter-bash-kernel', '1', '3.8'
    modulefile_path, root_path = module_factory(
        lmod_environment,
        mod_name, mod_ver, mod_tpl.JUPYTER_BASH_KERNEL_TEMPLATE_LUA,
        ['share/jupyter/kernels/bash'],
        {'py_version': py_ver, 'jpk_bash_version': mod_ver}
    )

    return ModuleInfo(
        name=mod_name,
        kname='bash',
        version=mod_ver,
        mod_path=str(modulefile_path),
        root_path=str(root_path),
        pyver=py_ver,
    )

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
