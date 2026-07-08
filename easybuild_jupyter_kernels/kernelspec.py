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
try:
    KERNEL_DISPLAY_LIMIT = int(os.getenv('EB_JUPYTER_KERNEL_LIMIT', '0'))  # 0 means no limit
except ValueError:
    KERNEL_DISPLAY_LIMIT = 0

# MODULE_SORTING = os.getenv('EB_JUPYTER_MODULE_SORTING', 'version_desc')
# if MODULE_SORTING not in ['version_asc', 'version_desc']:
#     raise ValueError(f"Invalid MODULE_SORTING value: {MODULE_SORTING}. Must be 'version' or 'name'.")

def normalize_module(module: str) -> str:
    """Normalizes a module name+version (eg `XXX/1.2.3`) to a kernel name (eg `XXX__1.2.3`)"""
    return module.replace('/', '__')


def module_avail(module_name: str) -> list[str]:
    """Return a list of available modules for a given module name using `module avail`."""
    try:
        output = subprocess.check_output(
            f'module --terse avail {module_name}/',
            shell=True, executable='/bin/bash',
            stderr=subprocess.STDOUT
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to find {module_name} from environment modules: {e.output.decode('utf-8')}") from e
    modules = output.decode('utf-8').splitlines()
    res = [line.strip() for line in modules if line.strip()]
    res = list(filter(lambda module: not module.startswith('/'), res))

    # if MODULE_SORTING == 'version_asc':
    #     res.sort(key=lambda module: tuple(map(int, module.split('/')[1].split('.'))))
    # elif MODULE_SORTING == 'version_desc':
    #     res.sort(key=lambda module: tuple(map(int, module.split('/')[1].split('.'))), reverse=True)

    return res

@dataclass
class ModuleKernelMapping(Mapping):
    """Map that hold information needed to build a `KernelData` instance from a specific module."""
    mod_name: str = field(metadata={
        'help': 'Name of the module (e.g., jupyter-server)',
    })
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

    def __post_init__(self):
        self._hash = None  # Cache the hash value for performance

    def __getitem__(self, key):
        """Allow dictionary-like access to the attributes of the dataclass."""
        return getattr(self, key)

    def __iter__(self):
        """Return an iterator over the attribute names of the dataclass."""
        return iter(asdict(self))

    def __len__(self):
        """Return the number of attributes in the dataclass."""
        return len(asdict(self))

    def __hash__(self):
        if self._hash is None:
            dct = asdict(self)
            dct = {k:tuple(v) if isinstance(v, list) else v for k,v in dct.items()}
            self._hash = hash(tuple(sorted(dct.items())))
        return self._hash

    def items(self):
        """Return a dictionary of the attributes of the dataclass."""
        return asdict(self).items()


# Map a module name to the kernel spec information. This is used to determine how to extract the necessary information
# from the environment module.
MODULE_KERNEL_MAP: dict[str, ModuleKernelMapping] = {
    'jupyter-server': ModuleKernelMapping(
        mod_name='jupyter-server',
        kernel_display_name=f'{DISPLAY_PREFIX} Python',
        kernel_language='python',
        kernel_path='$EBROOTJUPYTERMINSERVER/share/jupyter/kernels/python3',
        launcher_exec='python',
        launcher_args=['-m', 'ipykernel_launcher', '-f', '{connection_file}'],
        launcher_version_env_var='EBVERSIONPYTHON',
        kernel_version_env_var='EBVERSIONPYTHON',
    ),
    'octave-kernel': ModuleKernelMapping(
        mod_name='octave-kernel',
        kernel_display_name=f'{DISPLAY_PREFIX} Octave',
        kernel_language='octave',
        kernel_path='$EBROOTOCTAVEMINKERNEL/share/jupyter/kernels/octave/images',
        launcher_exec='python',
        launcher_args=['-m', 'octave_kernel', '-f', '{connection_file}'],
        launcher_version_env_var='EBVERSIONPYTHON',
        kernel_version_env_var='EBVERSIONOCTAVE',
    ),
    'IJulia': ModuleKernelMapping(
        mod_name='IJulia',
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
    'root-kernel': ModuleKernelMapping(
        mod_name='root-kernel',
        kernel_display_name=f'{DISPLAY_PREFIX} ROOT C++',
        kernel_language='c++',
        kernel_path='$EBROOTROOT/etc/notebook/kernels/root/',
        launcher_exec='python',
        launcher_args=['-m', 'JupyROOT.kernel.rootkernel', '-f', '{connection_file}'],
        launcher_version_env_var='EBVERSIONPYTHON',
        kernel_version_env_var='EBVERSIONROOT',
    ),
    'IRkernel': ModuleKernelMapping(
        mod_name='IRkernel',
        kernel_display_name=f'{DISPLAY_PREFIX} R',
        kernel_language='R',
        kernel_path='$EBROOTIRKERNEL/IRkernel/kernelspec/',
        launcher_exec='R',
        launcher_args=['--slave', '-e', 'IRkernel::main()', '--args', '{connection_file}'],
        launcher_version_env_var='EBVERSIONR',
        kernel_version_env_var='EBVERSIONR',
    ),
}

CLING_CPP_STDS = ['11', '14', '17', '20', '2b', '1z']

MODULE_KERNEL_MAP.update({
    f'cling-{std}': ModuleKernelMapping(
        mod_name='cling-kernel',
        kernel_display_name=f'{DISPLAY_PREFIX} C++{std} (Cling)',
        kernel_language='C++',
        kernel_path=f'$EBROOTCLINGMINKERNEL/share/jupyter/kernels/cling-cpp{std}',
        launcher_exec='jupyter-cling-kernel',
        launcher_args=['-f', '{connection_file}', f'--std=c++{std}'],
        launcher_version_env_var='EBVERSIONCLING',
        kernel_version_env_var='EBVERSIONCLING',
    ) for std in CLING_CPP_STDS
})

@dataclass
class KernelData:
    """Data class to hold information about a kernel spec derived from an EasyBuild module.
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
    ld_library_path: str = field(default='', metadata={
        'help': 'LD_LIBRARY_PATH environment variable',
        'getcmd': 'echo $LD_LIBRARY_PATH'
    })
    r_libs_site: str = field(default='', metadata={
        'help': 'R_LIBS_SITE environment variable',
        'getcmd': 'echo $R_LIBS_SITE'
    })
    eb_pythonprefixes: str = field(default='', metadata={
        'help': 'EBPYTHONPREFIXES environment variable',
        'getcmd': 'echo $EBPYTHONPREFIXES'
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
    def from_env_module(cls, module: str, info_map: ModuleKernelMapping) -> 'KernelData':
        """Create a KernelData instance from an environment module and a Mapping on how to extract its information."""
        mod_name, mod_ver = module.split('/')

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
        self.found_infos: dict[str, ModuleKernelMapping] = {}

    def find_kernel_specs(self):
        """Use the original method to find kernel specs, and then add any `jupyter-server` module kernels.
        (In Easybuild `ipykernel` is installed in the `jupyter-server` bundle)
        """
        specs = super().find_kernel_specs()

        for kernel_name, info_map in MODULE_KERNEL_MAP.items():
            mod_name = info_map.mod_name

            kernels = []
            for module in module_avail(mod_name):
                found_name, found_ver = module.split('/')
                if found_name != mod_name:
                    raise RuntimeError(f"Unexpected module name {found_name} for {mod_name} in module_avail() output")
                kernel_id = f'{kernel_name}__{found_ver}'

                data = KernelData.from_env_module(module, info_map)

                current_launcher_version = os.getenv(info_map.launcher_version_env_var, None)
                current_kernel_version = os.getenv(info_map.kernel_version_env_var, None)

                # Avoid conflicts for launcher with other externally loaded modules
                if current_launcher_version and data.launcher_version != current_launcher_version:
                    self.log.debug(
                        f"Skipping kernel spec for {module} (Python {data.launcher_version}) as it does not match "
                        f"current externally loaded Python version {current_launcher_version}"
                    )
                    continue
                # Avoid conflicts for kernel with other externally loaded modules
                if current_kernel_version and data.kernel_version != current_kernel_version:
                    self.log.debug(
                        f"Skipping kernel spec for {module} (Kernel version {data.kernel_version}) as it does not "
                        f"match current externally loaded kernel version {current_kernel_version}"
                    )
                    continue
                kernels.append((kernel_id, data, info_map))

            kernel_specs = list(sorted(kernels, key=lambda x: x[1].launcher_version, reverse=True))
            if KERNEL_DISPLAY_LIMIT:
                kernel_specs = kernel_specs[:KERNEL_DISPLAY_LIMIT]
            for kernel_id, data, info_map in kernel_specs:
                specs[kernel_id] = data.kernel_path
                self.found_specs[kernel_id] = data
                self.found_infos[kernel_id] = info_map

        return specs

    def _get_kernel_spec(self, kernel_id) -> KernelSpec:
        """Get the kernel spec for a given kernel name, using the found_specs dictionary.

        Args:
            kernel_name (str): The name of the kernel to retrieve the spec for.

        Returns:
            KernelSpec: The kernel spec object for the specified kernel name.
        """
        if not self.found_specs:
            self.log.warning('No found_specs available, calling find_kernel_specs()')
            self.find_kernel_specs()

        kernel_data = self.found_specs[kernel_id]
        info_map = self.found_infos[kernel_id]

        launcher_args = info_map.launcher_args
        display_name = info_map.kernel_display_name
        language = info_map.kernel_language

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

        env = {
            'PATH': kernel_data.path,
            'LD_LIBRARY_PATH': kernel_data.ld_library_path,
            'PYTHONPATH': ppath,
        }

        var_map = {
            'EBPYTHONPREFIXES': 'eb_pythonprefixes',
            'EBJULIA_DEPOT_PATH': 'eb_julia_depot_path',
            'EBJULIA_LOAD_PATH': 'eb_julia_load_path',
            'R_LIBS_SITE': 'r_libs_site',
        }

        # Make sure to also include any existing environment variables that might be set by an outside module/env
        # manager such as jupyterlmod
        for var, data_field in var_map.items():
            existing = os.getenv(var, '').split(os.pathsep)
            value = getattr(kernel_data, data_field).split(os.pathsep)
            value += [p for p in existing if p not in value]
            value = os.pathsep.join(filter(None, value))
            env[var] = value

        kernel_dct = {
            'argv': [kernel_data.launcher_exe] + launcher_args,
            'display_name': f"{display_name} ({kernel_data.kernel_version})",
            'resource_dir': kernel_data.kernel_path,
            'language': language,
            'env': env
        }

        self.log.debug(f"Creating KernelSpec for {kernel_id}: {kernel_dct}")

        return KernelSpec(**kernel_dct)

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
