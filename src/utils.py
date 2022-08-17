import os

# ----+----+----+----+----+----+----+----+----+----+----+----+----+----+----+
#  @SECTION: Math
# ----+----+----+----+----+----+----+----+----+----+----+----+----+----+----+


def round_nearest(x, base=10):
    return base * round(x/base)


# ----+----+----+----+----+----+----+----+----+----+----+----+----+----+----+
#  @SECTION: tableschema Wrappers
# ----+----+----+----+----+----+----+----+----+----+----+----+----+----+----+


def match_tblheaders(header, key, synonyms=[]):
    for i, c in enumerate(header.cells):
        for s in synonyms:
            if c.text == s:
                return True, i
    return False, 0


def tbl_contains_all_fields(table, field_list):
    indexes = []
    first_row = table.rows[0].cells
    for fields in field_list:
        for field in fields[1]:
            for i, c in enumerate(first_row):
                if field.lower() == c.text.lower():
                    indexes.append((fields[0], i))

    return indexes


def tbl_get_fields(table, fields):
    indexes = []
    first_row = table.rows[0].cells
    for i, c in enumerate(first_row):
        if c.text in fields:
            indexes.append(i)

    return indexes


# ----+----+----+----+----+----+----+----+----+----+----+----+----+----+----+
#  @SECTION: Path/Directory
# ----+----+----+----+----+----+----+----+----+----+----+----+----+----+----+


def file_names(path):
    if os.path.isfile(path):
        name = os.path.splitext(os.path.basename(os.path.abspath(path)))
        codes = str.split(name[0], sep='_', )
        return (codes[0], codes[1])
    return ('DEFAULT', 'PROD')


def get_ext_files(paths, ext):
    validated_paths = []
    for p in paths:
        if validate_ext(p, ext):
            f_abs = os.path.abspath(p)
            validated_paths.append(f_abs)
        elif os.path.isdir(p):
            p_abs = os.path.abspath(p)
            files_ls = os.listdir(p)
            for ff in files_ls:
                ff_abs = os.path.join(p_abs, ff)
                if validate_ext(ff_abs, ext):
                    validated_paths.append(ff_abs)

    return validated_paths


def validate_directory(path):
    path_abs = os.path.abspath(path)
    is_valid = os.path.isdir(path_abs)
    return is_valid, path_abs


def validate_ext(file, ext):
    absolute = os.path.abspath(file)
    type = os.path.splitext(os.path.basename(absolute))
    if (os.path.isfile(absolute) and type[1] == f'.{ext}'):
        return True
    return False


# ----+----+----+----+----+----+----+----+----+----+----+----+----+----+----+
#  @SECTION: Algorithms
# ----+----+----+----+----+----+----+----+----+----+----+----+----+----+----+


def group_items(items, size):
    groups = []
    group = []
    assert len(items) >= size
    n = 0
    reverse_n = len(items) - 1
    for i, item in enumerate(items):
        group.append(item)

        if n == size - 1 or reverse_n == 0:
            groups.append(list.copy(group))
            group.clear()
            n = 0
        else:
            n += 1
        reverse_n -= 1

    return groups
