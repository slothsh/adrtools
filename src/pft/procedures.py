from statistics import mean, mode
from fuzzywuzzy import fuzz as fzw
import json
from docx import Document
import os
from utils import round_nearest, tbl_contains_all_fields


# ----+----+----+----+----+----+----+----+----+----+----+----+----+----+----+
#  @SECTION: Globals
# ----+----+----+----+----+----+----+----+----+----+----+----+----+----+----+


SPEAKER_CASTING_DEFAULT = 'CAST ME'
LEVENSHTEIN_DT_DEFAULT = 75
SPEAKER_NAME_DEFAULT = 'UNKNOWN'


# ----+----+----+----+----+----+----+----+----+----+----+----+----+----+----+
#  @SECTION: Characters & Castings
# ----+----+----+----+----+----+----+----+----+----+----+----+----+----+----+


def aggregate_castings(data):
    aggregated = []
    for d in data:
        character = d[0]
        if len(d[2]) > 0:
            mode_gender = mode([x[0] for x in d[2]])
            avg_lo = round_nearest(mean([x[1] for x in d[2]]), 5)
            avg_hi = round_nearest(mean([x[2] for x in d[2]]), 5)
            if avg_lo >= avg_hi:
                age_dt = 5 if (mode_gender.upper() == 'M' or mode_gender.upper() == 'F') else 3
                avg_lo = avg_hi - age_dt
            aggregated.append((character, list.copy(d[1]), mode_gender.upper(), int(avg_lo), int(avg_hi)))

    return aggregated


def find_speaker_aliases(targets, names_list, ratio=LEVENSHTEIN_DT_DEFAULT):
    data = []
    for t in targets:
        collect = []
        used = []
        for n in names_list:
            alias_not_used = len([x for x in used if x.lower() == n.lower()]) == 0
            current_ratio = fzw.ratio(t.lower(), n.lower())

            gte_ratio = current_ratio >= ratio
            ne_current_name = t.lower() != n.lower()

            if gte_ratio and ne_current_name and alias_not_used:
                collect.append((current_ratio, n.lower()))
                used.append(n.lower())

        data.append((t.lower(), list.copy(collect)))

    return data


def fix_tc_frame_rate(tc, fps):
    chunks = tc.split(":")
    if chunks[3] == fps:
        chunks[3] = str(int(chunks[3]) - 1)

    return f'{chunks[0]}:{chunks[1]}:{chunks[2]}:{chunks[3]}'


def map_characters_to_castings(characters, castings):
    list.sort(castings)
    mapping = []
    for ch in characters:
        collect = []
        names = ch.split('\t')
        for casting in castings:
            split_casting = casting.split('\t')
            if names[0].strip().lower() == split_casting[0].strip().lower():
                casting_range = split_casting[1].split('-')
                gender = casting_range[0][0].strip()
                lo = int(casting_range[0][1:].strip())
                hi = int(casting_range[1].strip())
                collect.append((gender, lo, hi))
        mapping.append((names[0].strip(), list.copy([x.strip() for x in names[1:]]), list.copy(collect)))
        collect.clear()

    return mapping


def speaker_to_casting(speaker, config, ratio=LEVENSHTEIN_DT_DEFAULT):
    assert len(speaker) > 0, speaker
    assert 'speakers' in config

    cfg_data = [x for x in config['speakers']]

    age_casting = SPEAKER_CASTING_DEFAULT
    for entry in cfg_data:
        gender = entry['casting']['gender']
        lo = str(entry['casting']['lo']).rjust(2, '0')
        hi = str(entry['casting']['hi']).rjust(2, '0')

        nicknames = [x.lower() for x in entry['nicknames']]
        if speaker.lower() == entry['name'].lower() or speaker.lower() in nicknames:
            return entry['name'], f'{gender}{lo}-{hi}'

    fuzzed_names = sorted([(x["name"],
                            fzw.ratio(speaker, x["name"]),
                            f'{x["casting"]["gender"]}{str(x["casting"]["lo"]).rjust(2, "0")}-{str(x["casting"]["hi"]).rjust(2, "0")}') for x in cfg_data if fzw.ratio(speaker, x["name"]) > ratio],
                          reverse=True, key=lambda x: x[1])

    if len(fuzzed_names) > 0:
        return fuzzed_names[0][0], fuzzed_names[0][2]

    return speaker, age_casting


# ----+----+----+----+----+----+----+----+----+----+----+----+----+----+----+
#  @SECTION: Dubbing/ADR Script Parsing
# ----+----+----+----+----+----+----+----+----+----+----+----+----+----+----+


def normalised_script(path, schema_path, speaker_config_path, ratio=LEVENSHTEIN_DT_DEFAULT):
    parsed_lines = [{'id': '#',
                     'start': 'Time IN',
                     'end': 'Time OUT',
                     'character': 'Character',
                     'age': 'Actor Name',
                     'line': 'English Subtitle'}]

    data = None
    config = None
    try:
        data = script_to_list(path, schema_path)
        config = json.load(open(speaker_config_path, 'r'))
    except Exception as e:
        print(e)

    collect = []
    additional = {}
    id = 0
    prev_start = ''
    prev_end = ''

    data.pop(0)

    for j, line in enumerate(data):
        for title, value in line:
            if title == 'tcin':
                prev_start = fix_tc_frame_rate(value.strip(), '25')

            if title == 'tcout':
                prev_end = fix_tc_frame_rate(value.strip(), '25')

            if title == 'speaker':
                characters_raw = [SPEAKER_NAME_DEFAULT] if value.strip() == '' else [x for x in value.split(',') if x.strip() != '']
                increment = len(characters_raw) - 1
                for c in characters_raw:
                    names = c[0] if c.strip() == '' else c.lower().split(' to ')[0]
                    additional['id'] = str(id)
                    if len(characters_raw) > 1 and increment != 0:
                        id += 1
                        increment -= 1
                    additional['start'] = prev_start
                    additional['end'] = prev_end
                    corrected_speaker, age_range = speaker_to_casting(names.strip(), config)
                    additional['character'] = corrected_speaker.upper()
                    additional['age'] = age_range
                    collect.append(dict.copy(additional))
                    additional.clear()

            if title == 'line':
                lines_raw = value.split('- ')
                li = 0
                for ll in lines_raw:
                    collect_index = min(li, len(collect) - 1)
                    current_speaker = collect[collect_index]['character']
                    stripped = ll.strip().replace('\n', ' ')
                    collect[collect_index]['line'] = f'[{current_speaker}] {stripped}'
                    li += 1
                if li < len(collect):
                    for ii in range(li, len(collect)):
                        collect[ii]['line'] = f'[{collect[ii]["character"]}] (NO LINE)'

        id += 1

        for c in collect:
            parsed_lines.append(dict.copy(c))

        collect.clear()
        additional.clear()

    return parsed_lines


def script_to_list(path, schema_path):
    absolute_path = os.path.abspath(path).replace('\\', '/')
    absolute_schema = os.path.abspath(schema_path).replace('\\', '/')
    assert os.path.isfile(absolute_path), 'error: invalid path to .docx file: path is not a file'
    assert os.path.isfile(absolute_schema), 'error: invalid path to schema file: schema_path is not a file'

    data = []

    headers = None
    try:
        with open(absolute_schema, 'r') as file:
            headers = json.load(file)
    except Exception as e:
        print(e)

    all_tables = Document(absolute_path).tables
    flattened_schema = [(x['key'], x['synonyms']) for x in headers['header_fields']]

    collect_tables = []
    for tbl in all_tables:
        indexes = tbl_contains_all_fields(tbl, flattened_schema)
        if len(indexes) > 0:
            collect_rows = []
            for r in tbl.rows:
                collect_cols = []
                for c in r.cells:
                    collect_cols.append(c.text)
                collect_rows.append(list.copy(collect_cols))
            collect_tables.append((indexes, list.copy(collect_rows)))

    collect = []
    for item in collect_tables:
        for r in item[1]:
            for i in item[0]:
                collect.append((i[0], r[i[1]]))
            data.append(list.copy(collect))
            collect.clear()

    return data


def tbl_column_by_index(path, index, schema_path):
    data = script_to_list(path, schema_path)
    if len(data) == 0:
        return []

    data.pop(0)

    collect = []
    for line in data:
        k, v = line.items()
        for i, e in enumerate(line):
            if i == index:
                collect.append(v)

    return collect


def tbl_column_by_name(path, name):
    data = script_to_list(path)
    if len(data) == 0:
        return []

    header = data.pop(0)
    index = -1
    for i, c in enumerate(header):
        if c == name:
            index = i

    if index < 0:
        return []

    collect = []
    for line in data:
        k, v = line.items()
        for i, c in enumerate(line):
            if i == index:
                collect.append(v)

    return collect
