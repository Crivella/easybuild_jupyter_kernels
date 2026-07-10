"""Module to handle environment variables for EasyBuild Jupyter kernels."""

import os

DEFAULT_DISPLAY_LIMIT = 0  # 0 means no limit
DEFAULT_DISPLAY_PREFIX = "EasyBuild's"
DISPLAT_PREFIX_ENV_NAME = 'EB_JUPYTER_KERNEL_DISPLAY_PREFIX'
DISPLAY_LIMIT_ENV_NAME = 'EB_JUPYTER_KERNEL_LIMIT'


def get_display_prefix() -> str:
    """Get the display prefix for kernel names from the environment variable."""
    return os.getenv(DISPLAT_PREFIX_ENV_NAME, DEFAULT_DISPLAY_PREFIX)

def get_kernel_display_limit() -> int:
    """Get the kernel display limit from the environment variable."""
    try:
        return int(os.getenv(DISPLAY_LIMIT_ENV_NAME, str(DEFAULT_DISPLAY_LIMIT)))
    except ValueError:
        return DEFAULT_DISPLAY_LIMIT
