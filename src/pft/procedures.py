from statistics import mean, mode
from fuzzywuzzy import fuzz as fzw
import re
import json
from docx import Document
import os
from utils import round_nearest, tbl_contains_all_fields


# ----+----+----+----+----+----+----+----+----+----+----+----+----+----+----+
#  @SECTION: Globals
# ----+----+----+----+----+----+----+----+----+----+----+----+----+----+----+


SPEAKER_CASTING_DEFAULT = 'CAST ME'
LEVENSHTEIN_DT_DEFAULT = 80
SPEAKER_NAME_DEFAULT = 'UNKNOWN'
SPEAKER_VARIATION_WORDS = [
    '\'s +voice',
    ' +voice',
    ' +on +phone',
    ' +over +the +phone',
    ' +over +phone',
    ' +over +call',
    ' +on +call',
    ' +thinking',
    ' +in +head',
    '\'s +inside +voice',
    ' +inside +voice',
    '\'s +mind +voice',
    ' +mind +voice',
    ' +reading'
]

# ----+----+----+----+----+----+----+----+----+----+----+----+----+----+----+
#  @SECTION: Characters & Castings
# ----+----+----+----+----+----+----+----+----+----+----+----+----+----+----+


def aggregate_castings(data):
    aggregated = []
    for d in data:
        character = d[0]
        if len(d[3]) > 0:
            mode_gender = mode([x[0] for x in d[3]])
            avg_lo = round_nearest(mean([x[1] for x in d[3]]), 5)
            avg_hi = round_nearest(mean([x[2] for x in d[3]]), 5)
            if avg_lo >= avg_hi:
                age_dt = 5 if (mode_gender.upper() == 'M' or mode_gender.upper() == 'F') else 3
                avg_lo = avg_hi - age_dt
            aggregated.append((character, list.copy(d[1]), list.copy(d[2]), mode_gender.upper(), int(avg_lo), int(avg_hi)))

    return aggregated


def extract_variation_word(speaker):
    cleaned_speaker = speaker.lower().strip()

    for v in SPEAKER_VARIATION_WORDS:
        if re.search(f"{v}", cleaned_speaker) is not None:
            return v

    return None


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


def is_globbed_speaker(speaker):
    cleaned_speaker = speaker.lower().strip()
    return re.search("everyone|multiple|multiple +voice|multiple +voices", cleaned_speaker) is not None


def is_variation_of_speaker(speaker):
    cleaned_speaker = speaker.lower().strip()

    for v in SPEAKER_VARIATION_WORDS:
        if re.search(f"{v}", cleaned_speaker) is not None:
            return True

    return False


def is_regular_speaker(speaker):
    cleaned_speaker = speaker.lower().strip()
    return not is_globbed_speaker(cleaned_speaker) and not is_variation_of_speaker(cleaned_speaker)


def map_characters_to_castings(characters, castings):
    list.sort(castings)
    mapping = []
    for ch in characters:
        collect = []
        names = ch.split("\t")
        ignore_names = []
        valid_names = ch.split("\t")[0].split(":")
        if len(names) > 1:
            ignore_names = names[1].split(":")

        for casting in castings:
            split_casting = casting.split('\t')
            if valid_names[0].strip().lower() == split_casting[0].strip().lower():
                casting_range = split_casting[1].split('-')
                gender = casting_range[0][0].strip()
                lo = int(casting_range[0][1:].strip())
                hi = int(casting_range[1].strip())
                collect.append((gender, lo, hi))
        mapping.append((valid_names[0].strip(), list.copy([x.strip() for x in valid_names[1:]]), list.copy([x.strip() for x in ignore_names]), list.copy(collect)))
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
        fuzzed_name = fuzzed_names[0][0]
        fuzzed_age = fuzzed_names[0][2]
        # ignore = [x.lower() for x in cfg_data[speaker]['ignore']]
        ignore = [[y.lower() for y in x["ignore"] if x["name"] == speaker] for x in cfg_data]
        if fuzzed_name.lower() in ignore:
            fuzzed_name = speaker
            fuzzed_age = age_casting

        return fuzzed_name, fuzzed_age

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
        raise e

    collect = []
    additional = {}
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
                characters_raw = [SPEAKER_NAME_DEFAULT] if value.strip() == '' else [x.replace("\n", " ") for x in value.split(',') if x.strip() != '']
                for c in characters_raw:
                    names = c[0].lower().strip() if c.strip() == '' else c.lower().split(' to ')[0].strip()
                    additional['start'] = prev_start
                    additional['end'] = prev_end

                    canonical_speaker = names
                    if is_variation_of_speaker(names):
                        variation_word = extract_variation_word(names)

                        if variation_word is None:
                            raise Exception("variation word could not be found")

                        canonical_speaker = re.sub(variation_word.lower(), "", names.lower()).strip()

                    corrected_speaker, age_range = speaker_to_casting(canonical_speaker.strip(), config)
                    additional['character'] = corrected_speaker.upper()
                    additional['age'] = age_range
                    additional['line'] = ''
                    collect.append(dict.copy(additional))
                    additional.clear()

            if title == 'line':
                lines_raw = value.split('- ')
                li = 0
                glob_character_index = 0
                for ll in lines_raw:
                    collect_index = min(li, len(collect) - 1)
                    current_speaker = collect[collect_index]['character']
                    existing_line = collect[collect_index]['line']
                    # stripped = ll.strip().replace('\n', ' ').replace("'", "").replace('"', '')
                    stripped = "".join([x for x in ll.strip() if x not in "'\""]).replace("\n", " ")

                    if existing_line == '':
                        collect[collect_index]['line'] = f'[{current_speaker}] {stripped}'
                    else:
                        if is_globbed_speaker(current_speaker):
                            collect[glob_character_index]['line'] += f' - {stripped}'
                        else:
                            collect.append({
                                               'start': collect[collect_index]['start'],
                                               'end': collect[collect_index]['end'],
                                               'character': SPEAKER_NAME_DEFAULT,
                                               'age': SPEAKER_CASTING_DEFAULT,
                                               'line': f'[{SPEAKER_NAME_DEFAULT}] {stripped}'
                                           })

                    li += 1
                    if is_globbed_speaker(current_speaker):
                        glob_character_index = collect_index

                if li < len(collect):
                    for ii in range(li, len(collect)):
                        collect[ii]['line'] = f'[{collect[ii]["character"]}] (NO LINE)'

        id_start = len(parsed_lines)
        offset = 0
        for i, c in enumerate(collect):
            if re.search("\(NO LINE\)", c['line']) is not None:
                offset -= 1
            else:
                parsed_lines.append({ 'id': str(id_start + i + offset), **dict.copy(c) })

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
        raise e

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
