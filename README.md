# PoC of implementing a custom jupyter kernel manager for EasyBuild-installed python versions

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
