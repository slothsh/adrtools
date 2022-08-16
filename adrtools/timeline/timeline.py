#!/usr/bin/env python3

from timecode import Timecode

FPS_DEFAULT = 25.0
TCIN_DEFAULT = '00:00:00:00'
TCOUT_DEFAULT = '00:00:00:01'


def __event_default_read__(data):
    return ''


class TimelineEvent:
    def __init__(self,
                 data,
                 fps=FPS_DEFAULT,
                 read=__event_default_read__,
                 tcin=Timecode(FPS_DEFAULT, TCIN_DEFAULT),
                 tcout=Timecode(FPS_DEFAULT, TCOUT_DEFAULT)):

        self._fps = fps
        self._tcin = tcin
        self._tcout = tcout
        self._data = data
        self._read = read

    def duration(self):
        lo = min(self._tcin, self._tcout)
        hi = max(self._tcin, self._tcout)
        return hi - lo

    def __repr__(self):
        return str(self)

    def __str__(self):
        return f'{self._tcin}\t{self._tcout}\t{self.duration()}\t{self._read(self._data)}'

    def __eq__(self, rhs):
        return self.duration() == rhs.duration()

    def __ne__(self, rhs):
        return not self == rhs

    _fps = FPS_DEFAULT
    _tcin = Timecode(FPS_DEFAULT, TCIN_DEFAULT)
    _tcout = Timecode(FPS_DEFAULT, TCOUT_DEFAULT)
    _data = {}
    _read = __event_default_read__


class Timeline:
    def __init__(self, fps=FPS_DEFAULT, events=[]):
        self._fps = fps
        self._entities = events

    _fps = FPS_DEFAULT
    _events = []
