"""Tests for checking if the custom kernelspec manager finds the expected kernels from EasyBuild's `jupyter-server`
modules."""
from dataclasses import asdict

from commons import ModuleInfo, kernelspec_response_common

from easybuild_jupyter_kernels import environment as env
from easybuild_jupyter_kernels.kernelspec import CLING_CPP_STDS, MODULE_KERNEL_MAP, KernelData


def compare_dicts(dct1, dct2):
    """Compare two dictionaries and return True if they are equal, False otherwise."""
    if dct1.keys() != dct2.keys():
        return False
    for k in dct1.keys():
        v1 = dct1[k]
        v2 = dct2[k]
        if isinstance(v1, dict) and isinstance(v2, dict):
            if not compare_dicts(v1, v2):
                return False
        elif v1 != v2:
            return False
    return True

def _test_expected_kernels(kernelspecs: dict, expected_modules: list[ModuleInfo], check_empty: bool = True):
    """Test that the kernelspecs contain the expected kernels from the expected modules."""
    for module in expected_modules:
        expected_kernel_name = f"{module.kname}__{module.version}"
        kernel = kernelspecs.pop(expected_kernel_name, None)
        assert kernel is not None, f"{expected_kernel_name} kernel not found in kernelspecs"

    if check_empty:
        # Only the expected kernels should be present, no additional kernels from modules
        assert len(kernelspecs) == 0

def test_kernel_data_cache(monkeypatch, jupyter_server_module1):
    """Test that the kernel data cache is populated correctly."""
    import subprocess  # pylint: disable=import-outside-toplevel

    # Save the original subprocess.check_output function and replace it with a mock that sets `called` to True
    called = False
    monkeypatch.setattr(subprocess, '_check_output', subprocess.check_output, raising=False)
    def mock_check_output(*args, **kwargs):
        nonlocal called
        called = True
        return subprocess._check_output(*args, **kwargs)  # pylint: disable=protected-access,no-member
    monkeypatch.setattr(subprocess, 'check_output', mock_check_output)

    info_map = MODULE_KERNEL_MAP.get(jupyter_server_module1.kname, None)

    module = f'{jupyter_server_module1.name}/{jupyter_server_module1.version}'

    data1 = KernelData.from_env_module(module, info_map=info_map)
    assert called, 'subprocess.check_output was not called'
    called = False
    data2 = KernelData.from_env_module(module, info_map=info_map)
    assert not called, 'subprocess.check_output was called again, cache not used'
    assert data1 is data2, 'KernelData instances are not the same, cache not used'

    called = False
    KernelData.from_env_module.cache_clear()
    data3 = KernelData.from_env_module(module, info_map=info_map)
    assert called, 'subprocess.check_output was not called after cache clear'
    assert data1 is not data3, 'KernelData instances are the same after cache clear, cache not cleared'

    dct1 = asdict(data1)
    dct3 = asdict(data3)

    assert compare_dicts(asdict(data1), asdict(data3)), \
        f"KernelData instances are not equal after cache clear: {dct1} != {dct3}"

async def test_kernels_endpoint_bare(jp_fetch, lmod_environment):
    """Test the /api/kernelspecs endpoint without any modules available.

    Tests that the custom EBKernelSpecManager still finds the default kernels (echo and python3).
    """
    kernelspecs = kernelspec_response_common(await jp_fetch('api/kernelspecs'))

    # Only the expected kernels should be present, no additional kernels from modules
    assert len(kernelspecs) == 0

async def test_kernels_endpoint_one_module(jp_fetch, jupyter_server_module1):
    """Test the /api/kernelspecs endpoint with one jupyter-server module available."""
    kernelspecs = kernelspec_response_common(await jp_fetch('api/kernelspecs'))
    _test_expected_kernels(kernelspecs, [jupyter_server_module1])

async def test_kernels_endpoint_multiple_module(jp_fetch, jupyter_server_module1, jupyter_server_module2):
    """Test the /api/kernelspecs endpoint with one jupyter-server module available."""
    kernelspecs = kernelspec_response_common(await jp_fetch('api/kernelspecs'))
    _test_expected_kernels(kernelspecs, [jupyter_server_module1, jupyter_server_module2])

async def test_kernels_endpoint_version_filter(jp_fetch, ijulia_module1, ijulia_module2):
    """Test the /api/kernelspecs endpoint with 2 kernels of the same module but different version filters."""
    kernelspecs = kernelspec_response_common(await jp_fetch('api/kernelspecs'))

    assert (
        (ijulia_module1.name == ijulia_module2.name) and
        (ijulia_module1.kname != ijulia_module2.kname)
    ), 'Test requires 2 kernels using the same module but different kernel names'

    _test_expected_kernels(kernelspecs, [ijulia_module1, ijulia_module2])

async def test_kernels_endpoint_launcher_args_env(jp_fetch, ijulia_module1, ijulia_module3):
    """Test the /api/kernelspecs endpoint to check that 2 kernels that require overwritng the launcher arg
    do not reuse the same value from the first found.
    Specifically test changes in 0bedd3bc0b86c1ba4429e58226678c490578da38"""
    kernelspecs = kernelspec_response_common(await jp_fetch('api/kernelspecs'))

    assert (
        (ijulia_module1.name == ijulia_module3.name) and
        (ijulia_module1.kname == ijulia_module3.kname)
    ), 'Test requires 2 kernels using the same module and same kernel name'

    for module in [ijulia_module1, ijulia_module3]:
        expected_kernel_name = f"{module.kname}__{module.version}"
        kernel = kernelspecs.pop(expected_kernel_name, None)
        assert kernel is not None, f"{expected_kernel_name} kernel not found in kernelspecs"

        argv = ' '.join(kernel['spec']['argv'])
        assert module.root_path in argv, f"{module.root_path} not found in argv for {expected_kernel_name} kernel"

    # Only the expected kernels should be present, no additional kernels from modules
    assert len(kernelspecs) == 0

async def test_kernels_endpoint_preloaded_python(
        monkeypatch,
        jp_fetch, jupyter_server_module1, jupyter_server_module2, jupyter_server_module3
    ):
    """Test the /api/kernelspecs endpoint returns only kernels compatible with a pre-loaded python module that
    sets the EBVERSIONPYTHON environment variable."""
    expected_pyver = '3.8'
    monkeypatch.setenv('EBVERSIONPYTHON', expected_pyver)

    kernelspecs = kernelspec_response_common(await jp_fetch('api/kernelspecs'))
    for module in [jupyter_server_module1, jupyter_server_module2, jupyter_server_module3]:
        if module.pyver == expected_pyver:
            expected_kernel_name = f"{module.kname}__{module.version}"
            m1_kernel = kernelspecs.pop(expected_kernel_name, None)
            assert m1_kernel is not None, f"{expected_kernel_name} kernel not found in kernelspecs"

    # Only the expected kernels should be present, no additional kernels from modules
    assert len(kernelspecs) == 0

async def test_kernels_endpoint_preloaded_kernel(monkeypatch, jp_fetch, octave_module1):
    """Test the /api/kernelspecs endpoint returns only kernels compatible with a pre-loaded modules for the same kernel
    """
    monkeypatch.setenv('EBVERSIONOCTAVE', octave_module1.version + 'someotherstring')

    kernelspecs = kernelspec_response_common(await jp_fetch('api/kernelspecs'))

    # No kernel should be visible since we are preloading a module for a kernel not compatible with the only
    # octave-kernel module exposed to the system
    assert len(kernelspecs) == 0

async def test_kernels_display_env_var(mock_display_prefix, jp_fetch, jupyter_server_module1):
    """Test the /api/kernelspecs endpoint with one jupyter-server module available."""
    kernelspecs = kernelspec_response_common(await jp_fetch('api/kernelspecs'))

    for module in [jupyter_server_module1]:
        expected_kernel_name = f"{module.kname}__{module.version}"
        kernel = kernelspecs.pop(expected_kernel_name, None)
        assert kernel is not None, f"{expected_kernel_name} kernel not found in kernelspecs"
        spec = kernel.get('spec')
        assert spec is not None, f"spec for {expected_kernel_name} kernel not found"
        display_name = spec.get('display_name', '')
        assert display_name.startswith(mock_display_prefix), \
            f"display_name for {expected_kernel_name} '{display_name}' kernel does not start with {mock_display_prefix}"

    # Only the expected kernels should be present, no additional kernels from modules
    assert len(kernelspecs) == 0

async def test_kernel_cling(jp_fetch, cling_module1, mock_jupyter_cling_kernel):
    """Test the /api/kernelspecs endpoint with one of every module type."""
    kernelspecs = kernelspec_response_common(await jp_fetch('api/kernelspecs'))
    for module in [cling_module1]:
        for std in CLING_CPP_STDS:
            expected_kernel_name = f"{module.kname}-{std}__{module.version}"
            kernel = kernelspecs.pop(expected_kernel_name, None)
            assert kernel is not None, f"{expected_kernel_name} kernel not found in kernelspecs {kernelspecs}"

    # Only the expected kernels should be present, no additional kernels from modules
    assert len(kernelspecs) == 0

async def test_kernel_all(
        jp_fetch, jupyter_server_module1,
        ijulia_module1, ijulia_module2,
        octave_module1, rootkernel_module1, irkernel_module1,
        jpk_bash_module1
    ):
    """Test the /api/kernelspecs endpoint with one of every module type."""
    kernelspecs = kernelspec_response_common(await jp_fetch('api/kernelspecs'))
    _test_expected_kernels(kernelspecs, [
        jupyter_server_module1,
        ijulia_module1, ijulia_module2,
        octave_module1, rootkernel_module1, irkernel_module1, jpk_bash_module1
    ])

async def test_kernel_submodules_not_loaded(jp_fetch, submodule_environment1, jupyter_server_module_sub1):
    """Test that even if a submodule is available, it is not detected if the INIT_MODULES_ENV_NAME is not set"""
    kernelspecs = kernelspec_response_common(await jp_fetch('api/kernelspecs'))
    assert len(kernelspecs) == 0

async def test_kernel_submodules1(monkeypatch, jp_fetch, submodule_environment1, jupyter_server_module_sub1):
    """Test that kernels in submodule 1 are correctly detected when using it as an init module"""
    _, info = submodule_environment1
    module = f"{info.name}/{info.version}"
    monkeypatch.setenv(env.INIT_MODULES_ENV_NAME, module)

    kernelspecs = kernelspec_response_common(await jp_fetch('api/kernelspecs'))
    _test_expected_kernels(kernelspecs, [jupyter_server_module_sub1])

async def test_kernel_submodules2(monkeypatch, jp_fetch, submodule_environment2, jupyter_server_module_sub2):
    """Test that kernels in submodule 1 are correctly detected when using it as an init module"""
    _, info = submodule_environment2
    module = f"{info.name}/{info.version}"
    monkeypatch.setenv(env.INIT_MODULES_ENV_NAME, module)

    kernelspecs = kernelspec_response_common(await jp_fetch('api/kernelspecs'))
    _test_expected_kernels(kernelspecs, [jupyter_server_module_sub2])

async def test_kernel_submodules_all(
        monkeypatch, jp_fetch,
        submodule_environment1, jupyter_server_module_sub1,
        submodule_environment2, jupyter_server_module_sub2,
    ):
    """Test that kernels in submodule 1 and 2 are correctly detected when using it as an init module"""
    # Add the submodule environment 1 to the INIT_MODULES_ENV_NAME and check that one expected kernel is found
    _, info1 = submodule_environment1
    _, info2 = submodule_environment2

    # Test that only module 1 is detected even if both submodules are available, when INIT is set to only load submod 1
    module1 = f"{info1.name}/{info1.version}"
    monkeypatch.setenv(env.INIT_MODULES_ENV_NAME, module1)
    kernelspecs = kernelspec_response_common(await jp_fetch('api/kernelspecs'))
    _test_expected_kernels(kernelspecs, [jupyter_server_module_sub1])

    # Test that only module 2 is detected even if both submodules are available, when INIT is set to only load submod 2
    module2 = f"{info2.name}/{info2.version}"
    monkeypatch.setenv(env.INIT_MODULES_ENV_NAME, module2)
    kernelspecs = kernelspec_response_common(await jp_fetch('api/kernelspecs'))
    _test_expected_kernels(kernelspecs, [jupyter_server_module_sub2])

    module_all = f"{module1},{module2}"
    monkeypatch.setenv(env.INIT_MODULES_ENV_NAME, module_all)
    kernelspecs = kernelspec_response_common(await jp_fetch('api/kernelspecs'))
    _test_expected_kernels(kernelspecs, [jupyter_server_module_sub1, jupyter_server_module_sub2])
