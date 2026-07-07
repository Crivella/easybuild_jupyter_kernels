# Custom jupyter kernel manager for EasyBuild-installed packages

This package provides a custom `KernelSpecManager` that automatically exposes all kernels installed via [EasyBuild](https://easybuild.io/) and
currently visible in the module environment.

## Usage

Install package

```bash
cd PROJECT_DIRECOTRY
pip install .
```

Launch jupyter lab

```bash
jupyter lab --ServerApp.kernel_spec_manager_class=easybuild_jupyter_kernels.kernelspec.EBKernelSpecManager
```

## How does this look

Images generated using a `jupyter lab` server started with the [jupyterlmod](https://github.com/cmd-ntrf/jupyter-lmod) extension

![JupyterLab launcher](images/look.png)
