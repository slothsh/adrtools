#!/usr/bin/env python3.11
from debug.console import eprint
from pft import normalised_script
from utils import file_names, get_ext_files, group_items, validate_directory
import os
import sys
import argparse
import math
import multiprocessing as mp
from termcolor import colored
from chrono import timeregion_make_subsequences, TimeRegion, IDEAL_SECONDS, MAX_SECONDS
import pandas as pd

PROGRAM_NAME = "mergecues"


def process(paths, ideal_duration, max_duration, ext, out, prefix, dry_run):
    for data_path in paths:
        all_lines = None
        sorted_cues = []

        try:
            print(f"{PROGRAM_NAME}: [{colored('-', 'yellow')}] processing file @ {data_path}")
            all_lines = pd.read_csv(data_path, delimiter='\t')
            character_column = all_lines.columns.get_loc("character")
            casting_column = all_lines.columns.get_loc("casting")
            line_column = all_lines.columns.get_loc("line")
            tc_start_column = all_lines.columns.get_loc("tc_start")
            tc_end_column = all_lines.columns.get_loc("tc_end")


            characters = {c[character_column]: [] for (_, c) in all_lines.iterrows()}

            for (k, v) in characters.items():
                cues = timeregion_make_subsequences(sorted([{
                                                        'age': x[casting_column],
                                                        'character': k,
                                                        'line': x[line_column].replace(f"[{k}]", ""),
                                                        'region': TimeRegion.from_timecode_strings(x[tc_start_column], x[tc_end_column])
                                                    } for (_, x) in all_lines.iterrows() if k == x[character_column]], key=lambda x: x["region"]._start), ["UNKNOWN"],
                                                    ideal_duration,
                                                    max_duration)
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
        file_name = os.path.join(out, f'{out_tokens[0].upper()}_{out_tokens[1].upper()}.merged.TAB')
        if not dry_run:
            with open(file_name, 'w') as file:
                file.write("#\ttcin\ttcout\tcharacter\tactor\tline\n")
                for i, line in enumerate(sorted_cues):
                    file.write(f"{i}\t{line['start']}\t{line['end']}\t{line['character']}\t{line['actor']}\t[{line['character']}] {line['line']}\n")
                file.close()
            # all_lines.clear()
        else:
            print('')
            for line in sorted_cues:
                print(f"{line['start']}\t{line['end']}\t{line['character']}\t{line['actor']}\t[{line['character']}] {line['line']}")

        print(f"{PROGRAM_NAME}: [{colored('+', 'green')}] completed file @ {data_path}")


def main():
    parser = argparse.ArgumentParser(description='Merge ADR cue lines by factor')
    parser.add_argument('paths', type=str, nargs='+', default='',
                        help='source file paths containing tab seperated files')
    parser.add_argument('--ext', type=str, nargs='?', default='csv',
                        help='specific files to process')
    parser.add_argument('--ideal-duration', type=int, nargs='?', default=IDEAL_SECONDS,
                        help='ideal duration of merged line')
    parser.add_argument('--max-duration', type=int, nargs='?', default=MAX_SECONDS,
                        help='maximum duration of merged line')
    parser.add_argument('--out', type=str, nargs='?', default='.',
                        help='path to output directory for destination file')
    parser.add_argument('--process-count', type=int, nargs='?', default=4,
                        help='total processes to spawn in pool; cannot be higher than system total')
    parser.add_argument('--dry-run', action='store_true',
                        help='perform a dry run')
    args = parser.parse_args()

    errors = []
    valid_out_path, out_path = validate_directory(args.out)
    if not valid_out_path:
        errors.append(f'Please specify a valid output path\nspecified path: {out_path}')

    if len(errors) > 0:
        for msg in errors:
            eprint(msg)
        sys.exit(1)

    max_proc = min(max(1, args.process_count), os.cpu_count())

    all_paths = get_ext_files(args.paths, args.ext)
    group_size = math.ceil(len(all_paths) / max_proc)
    grouped_paths = group_items(all_paths, group_size)

    print(f'total cpus: {os.cpu_count()}, user selected: {max_proc}')
    print(f'group size: {group_size}')

    pool = []
    for i, p in enumerate(grouped_paths):
        proc = mp.Process(target=process, args=(p,
                                                args.ideal_duration,
                                                args.max_duration,
                                                args.ext,
                                                out_path,
                                                f'cpu{i}',
                                                args.dry_run))
        proc.start()
        pool.append(proc)

    for p in pool:
        p.join()


if __name__ == '__main__':
    main()
