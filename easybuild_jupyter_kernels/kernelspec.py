"""Implement a custom KernelSpecManager that finds kernels from EasyBuild's `jupyter-server` modules."""
import os
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field, fields
from functools import lru_cache

from jupyter_client.kernelspec import (KernelSpec, KernelSpecManager,
                                       NoSuchKernel)

DISPLAY_PREFIX = os.getenv('EB_JUPYTER_KERNEL_DISPLAY_PREFIX', 'EasyBuild\'s')


@dataclass
class ModuleKernelMapping(Mapping):
    """Data class to hold information about a kernel spec derived from an EasyBuild module."""
    kernel_display_name: str = field(metadata={
        'help': 'Display name of the kernel (e.g., Python 3)',
    })
    kernel_language: str = field(metadata={
        'help': 'Language of the kernel (e.g., python)',
    })
    kernel_path: str = field(metadata={
        'help': 'SH echo-able string that resolves to the path to the kernel spec directory',
    })
    launcher_exec: str = field(metadata={
        'help': 'Executable used to launch the kernel (e.g., python)',
    })
    launcher_args: list[str] = field(metadata={
        'help': 'Arguments to pass to the launcher executable',
    })
    launcher_version_env_var: str = field(metadata={
        'help': 'Environment variable that contains the launcher version to check from compatible loaded modules',
    })
    kernel_version_env_var: str = field(metadata={
        'help': 'Environment variable that contains the kernel version to be displayed',
    })
    launcher_args_env_vars: list[str] = field(default_factory=list, metadata={
        'help': 'Environment variables needed to resolve the launcher arguments (e.g., EBROOTIJULIA for IJulia)',
    })
    kernel_resource_dir: str = field(default='', metadata={
        'help': 'Path to the kernel resource directory relative to the kernel spec directory',
    })

    def __getitem__(self, key):
        """Allow dictionary-like access to the attributes of the dataclass."""
        return getattr(self, key)

    def __iter__(self):
        """Return an iterator over the attribute names of the dataclass."""
        return iter(asdict(self))

    def __len__(self):
        """Return the number of attributes in the dataclass."""
        return len(asdict(self))

    def items(self):
        """Return a dictionary of the attributes of the dataclass."""
        return asdict(self).items()


# Map a module name to the kernel spec information. This is used to determine how to extract the necessary information
# from the environment module.
MODULE_KERNEL_MAP: dict[str, ModuleKernelMapping] = {
    'jupyter-server': ModuleKernelMapping(
        kernel_display_name=f'{DISPLAY_PREFIX} Python',
        kernel_language='python',
        kernel_path='$EBROOTJUPYTERMINSERVER/share/jupyter/kernels/python3',
        launcher_exec='python',
        launcher_args=['-m', 'ipykernel_launcher', '-f', '{connection_file}'],
        launcher_version_env_var='EBVERSIONPYTHON',
        kernel_version_env_var='EBVERSIONPYTHON',
    ),
    'octave-kernel': ModuleKernelMapping(
        kernel_display_name=f'{DISPLAY_PREFIX} Octave',
        kernel_language='octave',
        kernel_path='$EBROOTOCTAVEMINKERNEL/share/jupyter/kernels/octave',
        launcher_exec='python',
        launcher_args=['-m', 'octave_kernel', '-f', '{connection_file}'],
        launcher_version_env_var='EBVERSIONPYTHON',
        kernel_version_env_var='EBVERSIONOCTAVE',
        kernel_resource_dir='images',
    ),
    # 'Cling': ModuleKernelMapping(
    #     kernel_display_name=f'{DISPLAY_PREFIX} C++ (Cling)',
    #     kernel_language='C++',
    #     kernel_path='$EBROOTCLING/share/jupyter/kernels/cling',
    #     launcher_exec='jupyter-cling-kernel',
    #     launcher_args=['-f', '{connection_file}', '--std=c++20'],
    #     launcher_version_env_var='EBVERSIONCLING',
    #     kernel_version_env_var='EBVERSIONCLING',
    # ),
    'IJulia': ModuleKernelMapping(
        kernel_display_name=f'{DISPLAY_PREFIX} Julia',
        kernel_language='julia',
        kernel_path='$EBROOTIJULIA/jupyter/kernels/julia-*',
        launcher_exec='julia',
        # launcher_args=[
        #     '-i', '--color=yes', '--project=@.', '-e', 'import IJulia; IJulia.run_kernel()', '{connection_file}'
        # ],
        launcher_args=[
            '-i', '--color=yes', '--project=@.', '$EBROOTIJULIA/packages/IJulia/src/kernel.jl', '{connection_file}'
        ],
        launcher_args_env_vars=['EBROOTIJULIA'],
        launcher_version_env_var='EBVERSIONJULIA',
        kernel_version_env_var='EBVERSIONJULIA',
    ),
}

@dataclass
class KernelData:
    """Data class to hold information about a kernel spec derived from an EasyBuild `jupyter-server` module.
    The metadata for each field includes an help and an optional getcmd key, which is a shell command to retrieve the
    value of the field."""
    mod_name: str = field(metadata={
        'help': 'Module name',
    })
    mod_version: str = field(metadata={
        'help': 'Module version',
    })
    kernel_path: str = field(metadata={
        'help': 'Path to the kernel spec directory',
        'getcmd': 'realpath {kernel_path}'
    })
    kernel_version: str = field(metadata={
        'help': 'Kernel version',
        'getcmd': 'echo ${kernel_version_env_var}'
    })
    launcher_exe: str = field(metadata={
        'help': 'Path to the Python executable',
        'getcmd': 'which {launcher_exec}'
    })
    launcher_version: str = field(metadata={
        'help': 'Python version',
        'getcmd': 'echo ${launcher_version_env_var}'
    })
    path: str = field(default='', metadata={
        'help': 'PATH environment variable',
        'getcmd': 'echo $PATH'
    })
    pythonpath: str = field(default='', metadata={
        'help': 'PYTHONPATH environment variable',
        'getcmd': 'echo $PYTHONPATH'
    })
    eb_pythonprefixes: str = field(default='', metadata={
        'help': 'EBPYTHONPREFIXES environment variable',
        'getcmd': 'echo $EBPYTHONPREFIXES'
    })
    ld_library_path: str = field(default='', metadata={
        'help': 'LD_LIBRARY_PATH environment variable',
        'getcmd': 'echo $LD_LIBRARY_PATH'
    })
    eb_julia_depot_path: str = field(default='', metadata={
        'help': 'EBJULIA_DEPOT_PATH environment variable',
        'getcmd': 'echo $EBJULIA_DEPOT_PATH'
    })
    eb_julia_load_path: str = field(default='', metadata={
        'help': 'EBJULIA_LOAD_PATH environment variable',
        'getcmd': 'echo $EBJULIA_LOAD_PATH'
    })

    @classmethod
    @lru_cache(maxsize=None)
    def from_env_module(cls, module: str) -> 'KernelData':
        """Create a KernelData instance from an environment module."""
        mod_name, mod_ver = module.split('/')

        info_map = MODULE_KERNEL_MAP.get(mod_name)

        cmds = [f"module load {module} > /dev/null 2>&1"]
        field_names = []
        for field_info in fields(cls):
            field_name = field_info.name
            getcmd = field_info.metadata.get('getcmd')
            if getcmd:
                getcmd = getcmd.format(**info_map)
                cmds.append(getcmd)
                field_names.append(field_name)

        # Extra vars that should not be used to populate the KernelData fields
        extra_vars = list(info_map.launcher_args_env_vars)
        # Extra vars needed to resolve the launcher args
        for var in extra_vars:
            cmds.append(f"echo ${var}")

        cmd = ' && '.join(cmds)
        try:
            output = subprocess.check_output(
                cmd,
                shell=True, executable='/bin/bash',
                stderr=subprocess.STDOUT
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to load module {module}: {e.output.decode('utf-8')}") from e


        output_lines = output.decode('utf-8').splitlines()
        data_dct = {}
        extra_vars_dct = {}
        try:
            while field_names:
                data_dct[field_names.pop(0)] = output_lines.pop(0)
            while extra_vars:
                extra_vars_dct[extra_vars.pop(0).lower()] = output_lines.pop(0)
        except IndexError as exc:
            raise RuntimeError(
                f"Failed to parse output for module {module}: not enough output lines:\n{output}"
            ) from exc

        for var in info_map.launcher_args_env_vars:
            value = extra_vars_dct.get(var.lower())
            if value is None:
                raise RuntimeError(f"Failed to get value for {var} from resolving launcher args for module {module}")
            info_map.launcher_args = [arg.replace(f"${var}", value) for arg in info_map.launcher_args]

        return cls(mod_name=mod_name, mod_version=mod_ver, **data_dct)


class EBKernelSpecManager(KernelSpecManager):
    """Custom KernelSpecManager that finds kernels from EasyBuild modules."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.found_specs: dict[str, KernelData] = {}

    def _find_jupyter_server_modules(self):
        """Use module avail to find available kenrnel-shipping modules."""
        res = []

        for module_name, _ in MODULE_KERNEL_MAP.items():
            try:
                output = subprocess.check_output(
                    f'module --terse avail {module_name}/',
                    shell=True, executable='/bin/bash',
                    stderr=subprocess.STDOUT
                )
                modules = output.decode('utf-8').splitlines()
                res += [line.strip() for line in modules if line.strip()]
                # return [line.strip() for line in modules if line.strip()]
            except subprocess.CalledProcessError as e:
                self.log.warning(f"Failed to find {module_name} from environment modules: {e.output.decode('utf-8')}")
                # return []

        return res

    def find_kernel_specs(self):
        """Use the original method to find kernel specs, and then add any `jupyter-server` module kernels.
        (In Easybuild `ipykernel` is installed in the `jupyter-server` bundle)
        """
        specs = super().find_kernel_specs()

        server_modules = self._find_jupyter_server_modules()
        for mod in server_modules:
            if mod.startswith('/'):
                continue
            data = KernelData.from_env_module(mod)

            info_map = MODULE_KERNEL_MAP[data.mod_name]
            current_launcher_version = os.getenv(info_map.launcher_version_env_var, None)
            resource_dir  = os.path.join(data.kernel_path, info_map.kernel_resource_dir)

            # If another Easybuild Python is already loaded in the environment, with potentially other modules on top
            # of it (eg SciPy stack), avoid exposing kernels that would be incompatible with it
            if current_launcher_version and data.launcher_version != current_launcher_version:
                self.log.debug(
                    f"Skipping kernel spec for {mod} (Python {data.launcher_version}) as it does not match current "
                    f"externally loaded Python version {current_launcher_version}"
                )
                continue
            # name = f"python{data.py_version}"
            name = mod.replace('/', '__')
            specs[name] = resource_dir
            self.found_specs[name] = data
            self.log.debug(f"Found kernel spec for {name}: {data.kernel_path} (Python {data.launcher_version})")

        return specs

    def _get_kernel_spec(self, kernel_name) -> KernelSpec:
        """Get the kernel spec for a given kernel name, using the found_specs dictionary.

        Args:
            kernel_name (str): The name of the kernel to retrieve the spec for.

        Returns:
            KernelSpec: The kernel spec object for the specified kernel name.
        """
        if not self.found_specs:
            self.log.warning('No found_specs available, calling find_kernel_specs()')
            self.find_kernel_specs()

        kernel_data = self.found_specs.get(kernel_name)
        if not kernel_data:
            self.log.error(f"Kernel data for {kernel_name} not found in found_specs")
            raise ValueError(f"Kernel data for {kernel_name} not found in found_specs")

        info_map = MODULE_KERNEL_MAP[kernel_data.mod_name]

        launcher_args = info_map.launcher_args
        display_name = info_map.kernel_display_name
        language = info_map.kernel_language
        resource_dir  = os.path.join(kernel_data.kernel_path, info_map.kernel_resource_dir)

        existing_ppath = os.getenv('PYTHONPATH', '').split(os.pathsep)
        # Ensure the pythonpath required for the kernel to work is added first
        ppath = kernel_data.pythonpath.split(os.pathsep)
        # Extend the pythonpath with any existing paths that are not already included
        ppath += [p for p in existing_ppath if p not in ppath]
        # Add additional paths that could've already been injected into sys.path by sitecustomize.py / jupyterlmod or
        # other mechanisms, but are not in PYTHONPATH or the kernel's pythonpath.
        ppath += [p for p in sys.path if p not in ppath and os.path.isdir(p)]
        ppath = list(filter(
            lambda p:
                # Avoid adding host system paths
                not p.startswith('/usr') and
                # Avoid adding paths from the current Python environment (e.g., virtualenv or conda)
                not p.startswith(sys.prefix),
            ppath
        ))
        ppath = os.pathsep.join(filter(None, ppath))

        # Make sure to also include any existing EBPYTHONPREFIXES that are not already in the kernel's EBPYTHONPREFIXES
        existing_prefixes = os.getenv('EBPYTHONPREFIXES', '').split(os.pathsep)
        prefixes = kernel_data.eb_pythonprefixes.split(os.pathsep)
        prefixes += [p for p in existing_prefixes if p not in prefixes]
        prefixes = os.pathsep.join(filter(None, prefixes))

        existing_depot_path = os.getenv('EBJULIA_DEPOT_PATH', '').split(os.pathsep)
        depot_path = kernel_data.eb_julia_depot_path.split(os.pathsep)
        depot_path += [p for p in existing_depot_path if p not in depot_path]
        depot_path = os.pathsep.join(filter(None, depot_path))

        existing_load_path = os.getenv('EBJULIA_LOAD_PATH', '').split(os.pathsep)
        load_path = kernel_data.eb_julia_load_path.split(os.pathsep)
        load_path += [p for p in existing_load_path if p not in load_path]
        load_path = os.pathsep.join(filter(None, load_path))


        kernel_dct = {
            'argv': [kernel_data.launcher_exe] + launcher_args,
            'display_name': f"{display_name} ({kernel_data.kernel_version})",
            'resource_dir': resource_dir,
            'language': language,
            'env': {
                'PATH': kernel_data.path,
                'PYTHONPATH': ppath,
                'EBPYTHONPREFIXES': prefixes,
                # "EBPYTHONPREFIXES_DEBUG": "1",
                'LD_LIBRARY_PATH': kernel_data.ld_library_path,
                'EBJULIA_DEPOT_PATH': depot_path,
                'EBJULIA_LOAD_PATH': load_path,
            }
        }

        self.log.debug(f"Creating KernelSpec for {kernel_name}: {kernel_dct}")

        res = KernelSpec(**kernel_dct)

        return res

    def get_kernel_spec(self, kernel_name) -> KernelSpec:
        """Get the kernel spec for a given kernel name, trying both the superclass method and the custom method."""
        try:
            spec = super().get_kernel_spec(kernel_name)
        except Exception:
            try:
                spec = self._get_kernel_spec(kernel_name)
            except Exception as e:
                self.log.error(f"Failed to get kernel spec for {kernel_name}: {e}")
                raise NoSuchKernel(kernel_name) from e

        return spec
