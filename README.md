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
jupyter lab --ServerApp.kernel_spec_manager_class=easybuild_jupyter_kernels.EBKernelSpecManager
```

## How does this look

Images generated using a `jupyter lab` server started with the [jupyterlmod](https://github.com/cmd-ntrf/jupyter-lmod) extension

![JupyterLab launcher](images/look.png)

## Environment variables

<!-- MODULE_SORTING_ENV_NAME = 'EB_JUPYTER_KERNEL_MODULE_SORTING'
DISPLAT_PREFIX_ENV_NAME = 'EB_JUPYTER_KERNEL_DISPLAY_PREFIX'
DISPLAY_LIMIT_ENV_NAME = 'EB_JUPYTER_KERNEL_LIMIT'
INIT_MODULES_ENV_NAME = 'EB_JUPYTER_KERNEL_INIT_MODULES' -->

List of environment variables that can be used to configure the behavior of the kernel manager:

| Variable | Description | Allowed | Default |
|----------|-------------|-------------|---------|
| `EB_JUPYTER_KERNEL_LIMIT` | Limit the number of kernels displayed in the launcher **per kernel type** | int | `"0"` (no limit) |
| `EB_JUPYTER_KERNEL_MODULE_SORTING` | Sort kernels in descending/ascending order based on the semantic version of the kernel launcher. **Only for the purpose of limiting the number of kernel displayed per type**. | `asc`/`desc` | `desc` (Kernels with greater launcher version are prioritized) |
| `EB_JUPYTER_KERNEL_DISPLAY_PREFIX` | Prefix used in the displayed kernel names | str | `"EasyBuild's"` |
| `EB_JUPYTER_KERNEL_INIT_MODULES` | Comma-separated list of modules used to detect kernels across hierarchical module schemes | str | `""` (find kernel without loading any extra module) |
