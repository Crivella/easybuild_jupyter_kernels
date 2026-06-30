"""Implement a custom KernelSpecManager that finds kernels from EasyBuild's `jupyter-server` modules."""
import os
import subprocess
import sys
from dataclasses import dataclass, field, fields
from functools import lru_cache

from jupyter_client.kernelspec import (KernelSpec, KernelSpecManager,
                                       NoSuchKernel)


@dataclass
class KernelData:
    """Data class to hold information about a kernel spec derived from an EasyBuild `jupyter-server` module.
    The metadata for each field includes an help and an optional getcmd key, which is a shell command to retrieve the
    value of the field."""
    name: str = field(metadata={
        'help': 'Module name',
    })
    version: str = field(metadata={
        'help': 'Module version',
    })
    kernel_path: str = field(metadata={
        'help': 'Path to the kernel spec directory',
        'getcmd': 'echo $EBROOTJUPYTERMINSERVER/share/jupyter/kernels/python3'
    })
    py_exe: str = field(metadata={
        'help': 'Path to the Python executable',
        'getcmd': 'which python'
    })
    py_version: str = field(metadata={
        'help': 'Python version',
        'getcmd': 'echo $EBVERSIONPYTHON'
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

    @classmethod
    @lru_cache(maxsize=None)
    def from_env_module(cls, module: str) -> 'KernelData':
        """Create a KernelData instance from an environment module."""
        mod_name, mod_ver = module.split('/')

        cmds = [f"module load {module} > /dev/null 2>&1"]
        field_names = []
        for field_info in fields(cls):
            getcmd = field_info.metadata.get('getcmd')
            if getcmd:
                cmds.append(getcmd)
                field_names.append(field_info.name)

        cmd = ' && '.join(cmds)
        try:
            output = subprocess.check_output(
                cmd,
                shell=True, executable='/bin/bash',
                stderr=subprocess.STDOUT
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to load module {module}: {e.output.decode('utf-8')}") from e

        data_dct = {}
        for name, value in zip(field_names, output.decode('utf-8').splitlines()):
            data_dct[name] = value
        return cls(name=mod_name, version=mod_ver, **data_dct)


class EBKernelSpecManager(KernelSpecManager):
    """Custom KernelSpecManager that finds kernels from EasyBuild's `jupyter-server` modules."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.found_specs: dict[str, KernelData] = {}

    def _find_jupyter_server_modules(self):
        """Use module avail to find available Jupyter server modules."""
        try:
            output = subprocess.check_output(
                'module --terse avail jupyter-server/',
                shell=True, executable='/bin/bash',
                stderr=subprocess.STDOUT
            )
            modules = output.decode('utf-8').splitlines()
            return [line.strip() for line in modules if line.strip()]
        except subprocess.CalledProcessError as e:
            self.log.warning(f"Failed to find Jupyter  from environment modules: {e.output.decode('utf-8')}")
            return []

    def find_kernel_specs(self):
        """Use the original method to find kernel specs, and then add any `jupyter-server` module kernels.
        (In Easybuild `ipykernel` is installed in the `jupyter-server` bundle)
        """
        specs = super().find_kernel_specs()

        current_eb_python = os.getenv('EBVERSIONPYTHON', None)

        server_modules = self._find_jupyter_server_modules()
        for mod in server_modules:
            if mod.startswith('/'):
                continue
            data = KernelData.from_env_module(mod)
            # If another Easybuild Python is already loaded in the environment, with potentially other modules on top
            # of it (eg SciPy stack), avoid exposing kernels that would be incompatible with it
            if current_eb_python and data.py_version != current_eb_python:
                self.log.debug(
                    f"Skipping kernel spec for {mod} (Python {data.py_version}) as it does not match current externally"
                    f" loaded Python version {current_eb_python}"
                )
                continue
            # name = f"python{data.py_version}"
            name = mod.replace('/', '__')
            specs[name] = data.kernel_path
            self.found_specs[name] = data
            self.log.debug(f"Found kernel spec for {name}: {data.kernel_path} (Python {data.py_version})")

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

        existing_ppath = os.getenv('PYTHONPATH', '').split(os.pathsep)
        # Ensure the pythonpath required for the kernel to work is added first
        ppath = kernel_data.pythonpath.split(os.pathsep)
        # Extend the pythonpath with any existing paths that are not already included
        ppath += [p for p in existing_ppath if p not in ppath]
        # Add additional paths that could've already been injected into sys.path by sitecustomize.py / jupyterlmod or
        # other mechanisms, but are not in PYTHONPATH or the kernel's pythonpath.
        ppath += [
            p for p in sys.path if
                p not in ppath and
                os.path.isdir(p) and
                # Avoid adding host system paths
                not p.startswith('/usr') and
                # Avoid adding paths from the current Python environment (e.g., virtualenv or conda)
                not p.startswith(sys.prefix)
        ]
        ppath = os.pathsep.join(filter(None, ppath))

        # Make sure to also include any existing EBPYTHONPREFIXES that are not already in the kernel's EBPYTHONPREFIXES
        existing_prefixes = os.getenv('EBPYTHONPREFIXES', '').split(os.pathsep)
        prefixes = kernel_data.eb_pythonprefixes.split(os.pathsep)
        prefixes += [p for p in existing_prefixes if p not in prefixes]
        prefixes = os.pathsep.join(filter(None, prefixes))

        kernel_dct = {
            'argv': [
                kernel_data.py_exe, '-m', 'ipykernel_launcher', '-f', '{connection_file}'
            ],
            'display_name': f"EasyBuilds' Python {kernel_data.py_version}",
            'language': 'python',
            'env': {
                'PYTHONPATH': ppath,
                'EBPYTHONPREFIXES': prefixes,
                # "EBPYTHONPREFIXES_DEBUG": "1",
                'LD_LIBRARY_PATH': kernel_data.ld_library_path
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
