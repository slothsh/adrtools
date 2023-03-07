#!/usr/bin/env python3

import argparse
import re
import sys
from enum import Enum, IntEnum, unique, auto


@unique
class EntityRawTypes(Enum):
    SPEAKER_RESOLUTE = auto()
    SPEAKER_GLOBBED = auto()
    LISTENER_RESOLUTE = auto()
    LISTENER_GLOBBED = auto()
    EMPTY = auto()


@unique
class EntityParsedExpressionIndexes(IntEnum):
    ENTITIES = 0
    REST = 1


class EntityNode:
    _next = None
    _type = EntityRawTypes.EMPTY
    _speakers = []
    _listeners = []

    def __init__(self, expression=''):
        results = EntityNode.parse_speaker_expression(expression)

        self._speakers = results[EntityParsedExpressionIndexes.ENTITIES][0]
        self._listeners = results[EntityParsedExpressionIndexes.ENTITIES][1]

        if len(self._speakers) > 0:
            self._type = EntityRawTypes.SPEAKER_RESOLUTE
        elif len(self._listeners) > 0:
            self._type = EntityRawTypes.LISTENER_RESOLUTE

        if len(results[EntityParsedExpressionIndexes.REST].strip()) > 0:
            self._next = EntityNode(results[EntityParsedExpressionIndexes.REST])


    @staticmethod
    def parse_speaker_expression(expression: str):
        # pre-conditions
        delimiter_save = ''
        transfer = ''
        find_listeners = False
        found_delimiter = False
        stop_index = 0

        speakers = []
        listeners = []

        for i, c in enumerate(expression):
            # first stop word case
            if found_delimiter is True and find_listeners is False:
                if transfer.strip()[-3:] == ' to':
                    transfer = transfer.strip()[0:-3]
                speakers.append(transfer.strip())
                transfer = ''
                find_listeners = True
                stop_index = i

            # second stop word case
            if found_delimiter is True and find_listeners is True and len(listeners) > 0:
                break

            if (c.lower() == ',' and find_listeners is True):
                listeners.append(transfer.strip())
                stop_index = i
                transfer = ''

            # multiple speakers case
            if  found_delimiter is False and find_listeners is False and c.lower() == ',' and transfer.strip() != '':
                speakers
                speakers.append(transfer.strip())
                transfer = ''

            # end of expression case
            if i == len(expression) - 1:
                if len(speakers) == 0:
                    speakers.append(transfer.strip())
                else:
                    listeners.append(expression[stop_index:].strip())
                stop_index = len(expression)

            # transfer regular characters
            if c.lower() != ',':
                transfer += c

            # eat and store stop words
            # TODO: user-defined predicate for delimiter
            found_delimiter = c.lower() == ' ' and expression[i - 3] == ' ' and expression[i - 2] == 't' and expression[i - 1] == 'o'

        return ((speakers, listeners), expression[stop_index:])

    def print(self):
        if self._next is not None:
            self._next.print()

        print(f'speakers: {self._speakers}\tlisteners: {self._listeners}')


def main():
    parser = argparse.ArgumentParser(description='testing for splitting character names from PFT scripts')
    parser.add_argument('character', type=str, nargs=1,
                        help='character string to split into characters')

    args = None
    try:
        args = parser.parse_args()
    except Exception as e:
        print(e)
        sys.exit(1)

    raw_str: str = args.character[0]
    if raw_str == '':
        print('please provide a valid character string')
        sys.exit(1)

    # determine how many speakers there are by counting 'speaker declarations'
    a = EntityNode(raw_str)
    a.print()


if __name__ == "__main__":
    main()
