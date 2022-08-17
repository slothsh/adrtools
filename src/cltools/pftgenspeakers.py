from pft import map_characters_to_castings, aggregate_castings, find_speaker_aliases
from debug import eprint
import argparse
import os
import sys
import json


def main():
    parser = argparse.ArgumentParser(description='Calculate average age range for characters')
    parser.add_argument('--characters', type=str, required=True,
                        help='path to text file with target names of characters')
    parser.add_argument('--castings', type=str, required=True,
                        help='path to text file with age ranges for characters')
    parser.add_argument('--aliases', type=str, required=True,
                        help='path to text file with all aliases for all characters')
    parser.add_argument('--ratio', type=int, required=True,
                        help='lowest ratio for fuzzy-matching to pass an alias for a target name')
    args = parser.parse_args()

    characters_path = os.path.abspath(args.characters)
    castings_path = os.path.abspath(args.castings)
    aliases_path = os.path.abspath(args.aliases)

    if os.path.isfile(characters_path) is False:
        eprint(f'error: invalid path to file: {characters_path}')
        sys.exit(1)
    if os.path.isfile(castings_path) is False:
        eprint(f'error: invalid path to file: {castings_path}')
        sys.exit(1)
    if os.path.isfile(aliases_path) is False:
        eprint(f'error: invalid path to file: {aliases_path}')
        sys.exit(1)

    characters = None
    castings = None
    aliases = None
    try:
        characters = set(open(characters_path, 'r').readlines())
        castings = open(castings_path, 'r').readlines()
        aliases = open(aliases_path, 'r').readlines()
    except Exception as e:
        eprint(e)

    if len(characters) == 0:
        eprint(f'error: no characters available in file: {characters_path}')
        sys.exit(1)
    if len(castings) == 0:
        eprint(f'error: no ages available in file: {castings_path}')
        sys.exit(1)
    if len(aliases) == 0:
        eprint(f'error: no names available in file: {aliases_path}')
        sys.exit(1)

    data = map_characters_to_castings(characters, castings)
    aggregated = aggregate_castings(data)
    sorted_aliases = find_speaker_aliases([x[0] for x in aggregated], [x.strip() for x in aliases], args.ratio)
    results = [
            {
                'name': v[0],
                'nicknames': v[1],
                'casting': v[2],
                'aliases': v[3]
            } for v in [x for x in zip([x[0] for x in aggregated],
                                       [x[1] for x in aggregated],
                                       [{'gender': x[2], 'lo': x[3], 'hi': x[4]} for x in aggregated],
                                       [[{'ratio': y[0], 'alias': y[1]} for y in x[1]] for x in sorted_aliases])]
    ]

    results_json = json.dumps({'speakers': sorted(results, key=lambda c: c['name'])}, indent=4)
    print(results_json)


if __name__ == "__main__":
    main()
