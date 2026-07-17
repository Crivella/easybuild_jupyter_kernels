"""Module to handle environment variables for EasyBuild Jupyter kernels."""

import enum
import os


class ModuleSorting(enum.Enum):
    """Enum for module sorting order."""
    ASCENDING = 'asc'
    DESCENDING = 'desc'

DEFAULT_DISPLAY_LIMIT = 0  # 0 means no limit
DEFAULT_DISPLAY_PREFIX = "EasyBuild's"
DEFAULT_MODULE_SORTING = ModuleSorting.DESCENDING.value

MODULE_SORTING_ENV_NAME = 'EB_JUPYTER_KERNEL_MODULE_SORTING'
DISPLAT_PREFIX_ENV_NAME = 'EB_JUPYTER_KERNEL_DISPLAY_PREFIX'
DISPLAY_LIMIT_ENV_NAME = 'EB_JUPYTER_KERNEL_LIMIT'


def get_display_prefix() -> str:
    """Get the display prefix for kernel names from the environment variable."""
    return os.getenv(DISPLAT_PREFIX_ENV_NAME, DEFAULT_DISPLAY_PREFIX)

def get_kernel_display_limit() -> int:
    """Get the kernel display limit from the environment variable."""
    try:
        return int(os.getenv(DISPLAY_LIMIT_ENV_NAME, str(DEFAULT_DISPLAY_LIMIT)))
    except ValueError as exc:
        raise ValueError(
            f"Invalid value for {DISPLAY_LIMIT_ENV_NAME}: {os.getenv(DISPLAY_LIMIT_ENV_NAME)}. Must be an integer."
        ) from exc

def get_module_sorting() -> ModuleSorting:
    """Get the module sorting order from the environment variable."""
    res = os.getenv(MODULE_SORTING_ENV_NAME, DEFAULT_MODULE_SORTING)
    try:
        res = ModuleSorting(res)
    except ValueError as exc:
        allowed = [_.value for _ in ModuleSorting]
        raise ValueError(
            f"Invalid value for {MODULE_SORTING_ENV_NAME}: {res}. Allowed values are: {allowed}"
        ) from exc
    return res
