#!/usr/bin/env python3

import os
import re
import argparse
from utils import validate_directory, get_ext_files, group_items
from pft import script_to_list
from debug.console import eprint


def main():
    parser = argparse.ArgumentParser(description="Finds locations of lines for specified characters in PFT script document")
    parser.add_argument("path", nargs="+", default=".",
                        help="path to folder containing .docx PFT scripts")
    parser.add_argument("-l", "--limit", nargs=1, default=5, type=int, dest="limit",
                        help="comma seperated list of characters to find line examples for")
    parser.add_argument('--schema', type=str, required=True,
                        help='path to schema file for selecting headers and validating tables')
    parser.add_argument('--ext', type=str, nargs='?', default='docx',
                        help='specific files to process')
    parser.add_argument("-c", "--characters", nargs="+", required=True, default=[], dest="characters",
                        help="comma seperated list of characters to find line examples for")

    args = parser.parse_args()

    files_path = os.path.abspath(args.path[0])
    if os.path.isdir(files_path) is not True:
        eprint("error: the path that was provided to positional argument <path> is not valid")
        eprint(f"path: {files_path}")
        exit(1)

    if len(args.characters) == 0:
        eprint("error: please specify at least one name for a character in positional argument <characters>")
        exit(1)

    all_paths = get_ext_files(args.path, args.ext)

    characters = dict.fromkeys(args.characters, [])

    for path in all_paths:
        incomplete_searches = [{x[0]: x[1]} for x in dict.items(characters) if len(x[1]) < args.limit]
        if len(incomplete_searches) > 0:
            script_list = script_to_list(path, args.schema)
            for s in incomplete_searches:
                s_list = tuple(dict.keys(s))
                k = s_list[0]

                for entry in script_list:
                    if len(characters[k]) >= args.limit:
                        break

                    tcin = entry[1][1]
                    tcout = entry[2][1]
                    speaker = entry[3][1].lower().strip()
                    line = entry[4][1].lower().strip()

                    if re.match(f"^{k.lower()} to", speaker):
                        characters[k].append({
                                                 "file": path,
                                                 "tcin": tcin,
                                                 "tcout": tcout,
                                                 "line": line,
                                             })
        else:
            break

    for k, v in dict.items(characters):
        for entry in characters[k]:
            clean_line = re.sub("\n", " ", entry["line"])
            print(f"{entry['file']}\t{k}:\ttcin: {entry['tcin']}\ttcout: {entry['tcout']}\t{clean_line}")


if __name__ == "__main__":
    main()
