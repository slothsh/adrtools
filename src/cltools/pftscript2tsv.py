from debug.console import eprint
from pft import normalised_script
from utils import file_names, get_ext_files, group_items, validate_directory
import os
import sys
import argparse
import math
import multiprocessing as mp
from termcolor import colored
from chrono import timeregion_make_subsequences, TimeRegion

PROGRAM_NAME = "script2tsv"


def process(paths, schema, cfg_path, ratio, ext, out, prefix, dry_run):
    for data_path in paths:
        all_lines = None
        sorted_cues = []

        try:
            print(f"{PROGRAM_NAME}: [{colored('-', 'yellow')}] processing file @ {data_path}")
            all_lines = normalised_script(data_path, schema, cfg_path, ratio)
            all_lines.pop(0)

            characters = {c['character']: [] for c in all_lines}

            for (k, v) in characters.items():
                cues = timeregion_make_subsequences(sorted([{
                                                        'age': x['age'],
                                                        'character': k,
                                                        'line': x['line'].replace(f"[{k}]", ""),
                                                        'region': TimeRegion.from_timecode_strings(x['start'], x['end'])
                                                    } for x in all_lines if k == x['character']], key=lambda x: x["region"]._start), ["UNKNOWN"])
                characters[k] = cues

            flattened_cues = []
            for k, v in characters.items():
                for e in v:
                    flattened_cues.append({
                                              'start': str(e['region']._start),
                                              'end': str(e['region']._end),
                                              'actor': e['age'],
                                              'character': k,
                                              'line': e['line'],
                                          })

            sorted_cues = sorted(flattened_cues, key=lambda x: x['start'])

        except Exception as e:
            print(f"{PROGRAM_NAME}: [{colored('!', 'red')}] exception was raised for file @ {data_path}")
            print(f"{PROGRAM_NAME}: [{colored('!', 'red')}] reason: {e}")
            continue

        out_tokens = file_names(data_path)
        file_name = os.path.join(out, f'{out_tokens[0].upper()}_{out_tokens[1].upper()}.gen.TAB')
        if not dry_run:
            with open(file_name, 'w') as file:
                file.write("#\ttcin\ttcout\tcharacter\tactor\tline\n")
                for i, line in enumerate(sorted_cues):
                    file.write(f"{i}\t{line['start']}\t{line['end']}\t{line['character']}\t{line['actor']}\t[{line['character']}] {line['line']}\n")
                file.close()
            all_lines.clear()
        else:
            print('')
            for line in sorted_cues:
                print(f"{line['start']}\t{line['end']}\t{line['character']}\t{line['actor']}\t[{line['character']}] {line['line']}")

        print(f"{PROGRAM_NAME}: [{colored('+', 'green')}] completed file @ {data_path}")


def main():
    parser = argparse.ArgumentParser(description='PFT Script Un-fucker')
    parser.add_argument('paths', type=str, nargs='+', default='',
                        help='files to un-fuck')
    parser.add_argument('--ext', type=str, nargs='?', default='docx',
                        help='specific files to process')
    parser.add_argument('--schema', type=str, nargs=1, required=True,
                        help='path to schema file to validate table data')
    parser.add_argument('--speaker-cfg', type=str, nargs=1, required=True,
                        help='path to speaker configuration file to cross-reference names')
    parser.add_argument('--ratio', type=int, nargs=1, default=75,
                        help='lowest ratio for fuzzy-matching to pass an alias for a target name')
    parser.add_argument('--out', type=str, nargs='?', default='.',
                        help='path to output directory to save files containing collected names')
    parser.add_argument('--write-type', type=str, nargs='?', default='a',
                        help='write to file can be a or w')
    parser.add_argument('--process-count', type=int, nargs='?', default=4,
                        help='total processes to spawn in pool; cannot be higher than system total')
    parser.add_argument('--dry-run', action='store_true',
                        help='perform a dry run')
    args = parser.parse_args()

    errors = []
    cfg_path = os.path.abspath(args.speaker_cfg[0])
    if os.path.isfile(cfg_path) is False:
        errors.append(f'error: path to speaker configuration is invalid at {cfg_path}')

    table_schema = os.path.abspath(args.schema[0])
    if os.path.isfile(table_schema) is False:
        errors.append(f'error: path to table schema file is invalid at {table_schema}')

    valid_out_path, out_path = validate_directory(args.out)
    if not valid_out_path:
        errors.append(f'Please specify a valid output path\nspecified path: {out_path}')

    if len(errors) > 0:
        for msg in errors:
            eprint(msg)
        sys.exit(1)

    write_type = args.write_type.lower()
    valid_write_types = ['a', 'w', 'ab', 'wb']
    if write_type not in valid_write_types:
        write_type = 'a'

    max_proc = min(max(1, args.process_count), os.cpu_count())

    all_paths = get_ext_files(args.paths, args.ext)
    group_size = math.ceil(len(all_paths) / max_proc)
    grouped_paths = group_items(all_paths, group_size)

    print(f'total cpus: {os.cpu_count()}, user selected: {max_proc}')
    print(f'group size: {group_size}')

    pool = []
    for i, p in enumerate(grouped_paths):
        proc = mp.Process(target=process, args=(p,
                                                table_schema,
                                                cfg_path,
                                                args.ratio,
                                                args.ext,
                                                out_path,
                                                f'cpu{i}',
                                                args.dry_run))
        pool.append(proc)

    for p in pool:
        p.start()

    keep_alive = True
    while keep_alive:
        prev = False
        for p in pool:
            keep_alive = prev or p.is_alive()


if __name__ == '__main__':
    main()
