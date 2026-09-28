"""Tempaltes for Lua module files"""

SUBMODULE_TEMPLATE_LUA = """
prepend_path("MODULEPATH", "{prefix}")
"""

JUPYTER_SERVER_MODULE_TEMPLATE_LUA = """
setenv("EBVERSIONPYTHON", "{py_version}")
setenv("EBROOTJUPYTERMINSERVER", "{prefix}")
prepend_path("PYTHONPATH", "{prefix}/lib/python{py_version}/site-packages")
prepend_path("EBPYTHONPREFIXES", "{prefix}")
prepend_path("LD_LIBRARY_PATH", "{prefix}/lib")
"""

JULIA_MODULE_TEMPLATE_LUA = """
setenv("EBROOTIJULIA", "{prefix}")
setenv("EBVERSIONJULIA", "{julia_version}")
setenv("EBVERSIONIJULIA", "{ijulia_version}")
setenv("JULIA_DEPOT_PATH", "{prefix}/julia_depot")
setenv("JULIA_LOAD_PATH", "{prefix}/julia_load")
"""

OCTAVE_MODULE_TEMPLATE_LUA = """
setenv("EBROOTOCTAVEMINKERNEL", "{prefix}")
setenv("EBVERSIONPYTHON", "{py_version}")
setenv("EBVERSIONOCTAVE", "{octave_version}")
prepend_path("PYTHONPATH", "{prefix}/lib/python{py_version}/site-packages")
prepend_path("EBPYTHONPREFIXES", "{prefix}")
prepend_path("LD_LIBRARY_PATH", "{prefix}/lib")
"""

ROOTCPP_MODULE_TEMPLATE_LUA = """
setenv("EBROOTROOT", "{prefix}")
setenv("EBVERSIONPYTHON", "{py_version}")
setenv("EBVERSIONROOT", "{root_version}")
prepend_path("PYTHONPATH", "{prefix}/lib/python{py_version}/site-packages")
prepend_path("EBPYTHONPREFIXES", "{prefix}")
prepend_path("LD_LIBRARY_PATH", "{prefix}/lib")
"""

IRKERNEL_MODULE_TEMPLATE_LUA = """
setenv("EBVERSIONR", "{r_version}")
setenv("EBROOTIRKERNEL", "{prefix}")
prepend_path("R_LIBS_SITE", "{prefix}/lib/R/site-library")
"""

CLING_KERNEL_MODULE_TEMPLATE_LUA = """
setenv("EBVERSIONCLING", "{cling_version}")
setenv("EBROOTCLINGMINKERNEL", "{prefix}")
"""

JUPYTER_BASH_KERNEL_TEMPLATE_LUA = """
setenv("EBVERSIONPYTHON", "{py_version}")
setenv("EBROOTJUPYTERMINBASHMINKERNEL", "{prefix}")
setenv("EBVERSIONJUPYTERMINBASHMINKERNEL", "{jpk_bash_version}")
"""
