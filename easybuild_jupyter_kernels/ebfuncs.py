"""Functions specific to EasyBuild's default module naming scheme and toolchain families."""
GCC_2022B = '12.2.0'
GCC_2023A = '12.3.0'
GCC_2023B = '13.2.0'
GCC_2024A = '13.3.0'
GCC_2025A = '14.2.0'
GCC_2025B = '14.3.0'
GCC_2026_1 = '15.2.0'

GCC_MAP = {
    '2022b': GCC_2022B,
    '2023a': GCC_2023A,
    '2023b': GCC_2023B,
    '2024a': GCC_2024A,
    '2025a': GCC_2025A,
    '2025b': GCC_2025B,
    '2026.1': GCC_2026_1,
}

EB_TC_FAMILIES = []
# EB_TC_FAMILY_MAP = {}
for _family, _gcc_version in GCC_MAP.items():
    EB_TC_FAMILIES.append([
        ('foss', _family), ('gompi', _family), ('gfbf', _family), ('GCC', _gcc_version), ('GCCcore', _gcc_version)
    ])

    # EB_TC_FAMILY_MAP[('foss', _family)] = [
    #     ('foss', _family), ('gompi', _family), ('GCC', _gcc_version), ('GCCcore', _gcc_version)
    # ]
    # EB_TC_FAMILY_MAP[('gompi', _family)] = [
    #     ('gompi', _family), ('GCC', _gcc_version), ('GCCcore', _gcc_version)
    # ]
    # EB_TC_FAMILY_MAP[('gfbf', _family)] = [
    #     ('gfbf', _family), ('GCC', _gcc_version), ('GCCcore', _gcc_version)
    # ]

def get_toolchain_family(module_name: str) -> list[tuple[str, str]]:
    """Given a module name, return the corresponding toolchain family."""
    for family in EB_TC_FAMILIES:
        if any(f'{mod_name}-{mod_version}' in module_name for mod_name, mod_version in family):
            return family
    return []

def get_compatible_module(module_list: list[str], compatible_family: list[tuple[str, str]]) -> str:
    """Given a list of module names and a compatible family, return the first module that matches the family."""
    for mod in module_list:
        if any(f'{mod_name}-{mod_version}' in mod for mod_name, mod_version in compatible_family):
            return mod
    return None
