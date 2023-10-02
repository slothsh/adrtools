#!/usr/bin/env python3.11
from debug.console import eprint
from utils import file_names, get_ext_files, group_items, validate_directory
import os
import sys
import argparse
import math
import multiprocessing as mp
from termcolor import colored
from chrono import timecode_to_frames
import pandas as pd

PROGRAM_NAME = "cuedensity"


def cue_weight(window_start, window_end, cue_start, cue_end):
    cue_length = cue_end - cue_start
    window_length = window_end - window_start

    if cue_start + cue_length >= window_start and cue_end - cue_length <= window_end:
        mn = max(cue_start, window_start)
        mx = min(cue_end, window_end)
        return 1 - ((cue_length - (mx - mn)) / cue_length)

    return 0.0


def get_largest_timecode(data_frame, fps):
    sorted_data_frame = data_frame.sort_values(by=["id"], ascending=False)
    return timecode_to_frames(sorted_data_frame.iloc[0].loc["tcout"], fps)


def process(paths, run_time_seconds, frame_rate, ext, out, prefix, dry_run):
    for data_path in paths:
        try:
            print(f"{PROGRAM_NAME}: [{colored('-', 'yellow')}] processing file @ {data_path}")

            all_lines = pd.read_csv(data_path, delimiter='\t')
            total_program_frames = run_time_seconds * frame_rate if run_time_seconds > 0 else get_largest_timecode(all_lines, frame_rate) * frame_rate
            timeline_window_size = 100
            program_window_size = total_program_frames // timeline_window_size
            empty_timeline = [[x, x * program_window_size, 0.0] for x in range(timeline_window_size)]

            tc_start_column = all_lines.columns.get_loc("tcin")
            tc_end_column = all_lines.columns.get_loc("tcout")

            for i, (_, line) in enumerate(all_lines.iterrows()):
                frames_start = timecode_to_frames(line[tc_start_column], frame_rate)
                frames_end = timecode_to_frames(line[tc_end_column], frame_rate)
                window_start = (frames_start // program_window_size)
                window_end = (frames_end // program_window_size) + 1

                for sample_frame in empty_timeline[window_start:window_end]:
                    current_cue_weight = cue_weight(sample_frame[0] * program_window_size,
                                                    (sample_frame[0] * program_window_size) + program_window_size,
                                                    frames_start,
                                                    frames_end)

                    sample_frame[2] += current_cue_weight

        except Exception as e:
            print(f"{PROGRAM_NAME}: [{colored('!', 'red')}] exception was raised for file @ {data_path}")
            print(f"{PROGRAM_NAME}: [{colored('!', 'red')}] reason: {e}")
            continue

    out_tokens = file_names(data_path)
    file_name = os.path.join(out, f'{out_tokens[0].upper()}_{out_tokens[1].upper()}.cuedensity.csv')
    if not dry_run:
        with open(file_name, 'w') as file:
            for i, title in enumerate(["frame", "frame_start", "value"]):
                file.write(f"{title}")
                for j, sample_frame in enumerate(empty_timeline):
                    file.write(f"\t{sample_frame[i]}")
                file.write("\n")
            file.close()
    else:
        pass

    print(f"{PROGRAM_NAME}: [{colored('+', 'green')}] completed file @ {data_path}")


def main():
    parser = argparse.ArgumentParser(description='compute cue density data')
    parser.add_argument('paths', type=str, nargs='+', default='',
                        help='path to CSV file containing dub cues')
    parser.add_argument('--ext', type=str, nargs='?', default='csv',
                        help='specific files to process')
    parser.add_argument('--frame-rate', type=int, nargs='?', default=25,
                        help='frame rate of data in source file')
    parser.add_argument('--run-time', type=int, nargs='?', default=0,
                        help='total run time in seconds of source file program')
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
                                                args.run_time,
                                                args.frame_rate,
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
