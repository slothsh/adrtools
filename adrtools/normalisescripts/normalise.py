#!/usr/bin/env python3

import argparse
import adr
from adr import eprint
import os


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
    args = parser.parse_args()

    all_data = adr.get_ext_files(args.paths, args.ext)
    cfg_path = os.path.abspath(args.speaker_cfg[0])
    if os.path.isfile(cfg_path) is False:
        eprint(f'error: path to speaker configuration is invalid at {cfg_path}')

    for data_path in all_data:
        all_lines = adr.normalised_script(data_path, os.path.abspath(args.schema[0]), cfg_path, args.ratio)
        out_tokens = adr.file_names(data_path)
        file_name = f'{out_tokens[0].upper()}_{out_tokens[1].upper()}.gen.TAB'
        with open(file_name, 'w') as file:
            for line in all_lines:
                for k, v in line.items():
                    file.write(v)
                    file.write('\t')
                file.write('\n')
            file.close()
        all_lines.clear()


if __name__ == '__main__':
    main()
