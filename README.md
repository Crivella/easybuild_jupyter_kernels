# PoC of implementing a custom jupyter kernel manager for EasyBuild-installed python versions

## Usage

Install package

```bash
cd PROJECT_DIRECOTRY
pip install jupyterlab
pip install .
```

Launch jupyter lab

```bash
jupyter lab --ServerApp.kernel_spec_manager_class=easybuild_jupyter_kernels.kernelspec.EBKernelSpecManager
```

## TODO

- [ ] Add a configuration file
