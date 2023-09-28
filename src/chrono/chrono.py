import re

TICKS_RESOLUTION = 1000
TICKS_MAX_GAP = TICKS_RESOLUTION * 5
FPS_DEFAULT = 25.0
IDEAL_SECONDS = 5
MAX_SECONDS = 8
TICKS_IDEAL_LENGTH = IDEAL_SECONDS * TICKS_RESOLUTION
TICKS_MAX_LENGTH = MAX_SECONDS * TICKS_RESOLUTION

# def get_character_casting(character):
#     matched_casting = [(x['gender'], x['age_lo'], x['age_hi']) for x in CASTING_TABLE if x['character'] == character.upper()]
#
#     if len(matched_casting) > 0:
#         casting = matched_casting[0]
#         return f"{casting[0]}{casting[1]}-{casting[2]}"
#
#     return "CAST ME"


def normalise_entries(entries):
    regular_entries = [x for x in entries if re.search("^.+/.+$", x.split('\t')[4].strip()) is None]
    globbed_entries = [x for x in entries if re.search("^.+/.+$", x.split('\t')[4].strip()) is not None]

    normalised_entries = []
    for e in globbed_entries:
        parts = e.split("\t")
        characters = parts[4].split("/")
        for c in characters:
            normalised_entries.append(f"{parts[0].strip()}\t{parts[1].strip()}\t{parts[2].strip()}\t{parts[3].strip()}\t{c.strip()}\t{parts[5]}\t{parts[6].strip()}")

    return [*regular_entries, *normalised_entries]


def ticks_to_timecode(ticks, fps=FPS_DEFAULT):
    h = m = s = f = 0.0
    fps_delimiter = ":"

    h = int(ticks / (3600 * fps * TICKS_RESOLUTION))
    ticks %= 3600 * fps * TICKS_RESOLUTION
    m = int(ticks / (60 * fps * TICKS_RESOLUTION))
    ticks %= 60 * fps * TICKS_RESOLUTION
    s = int(ticks / (fps * TICKS_RESOLUTION))
    ticks %= fps * TICKS_RESOLUTION
    f = int(ticks / TICKS_RESOLUTION)

    h_str = str(h).rjust(2, "0")
    m_str = str(m).rjust(2, "0")
    s_str = str(s).rjust(2, "0")
    f_str = str(f).rjust(2, "0")

    return f"{h_str}:{m_str}:{s_str}{fps_delimiter}{f_str}"


def timecode_to_ticks(timecode, fps=FPS_DEFAULT):
    tc_parts = [float(x) * fps * TICKS_RESOLUTION for x in timecode.split(":")]
    return (tc_parts[0] * 3600) + (tc_parts[1] * 60) + (tc_parts[2]) + (tc_parts[3] / fps)


def timecode_to_frames(timecode, fps=FPS_DEFAULT):
    tc_parts = [int(x) * fps for x in timecode.split(":")]
    return (tc_parts[0] * 3600) + (tc_parts[1] * 60) + (tc_parts[2]) + (tc_parts[3] // fps)


def timeregion_merge_sequence(sequence):
    # TODO: assert sequence is, in fact, in sequential order
    start = sequence[0]._start
    end = sequence[-1]._end
    fps = start._fps
    return TimeRegion(start, end, fps)


def timeregion_make_subsequences(sequence, ignore=[], ideal_duration=IDEAL_SECONDS, max_duration=MAX_SECONDS):
    sub_sequence = []
    merged_sequences = []

    ideal_duration_ticks = ideal_duration * TICKS_RESOLUTION
    max_duration_ticks = max_duration * TICKS_RESOLUTION

    acc = 0.0
    current_start = 0.0
    merged_english = ""
    actor = ""
    character = ""
    total_entries = len(sequence)

    for i, seq in enumerate(sequence):
        region = seq["region"]

        if len(sub_sequence) == 0:
            current_start = region._start

        acc += (region._end - current_start)._ticks
        sub_sequence.append(region)
        merged_english += seq["line"] + " "
        actor = seq["age"]
        character = seq["character"]

        if character in ignore:
            continue

        merge_early = False
        shared_boundary = False
        gt_max_length = False
        if i + 1 < total_entries:
            next_region = sequence[i + 1]['region']
            next_duration = (next_region._end - current_start)._ticks

            if next_duration >= ideal_duration_ticks * region._fps:
                merge_early = True

            if (next_region._start - region._end)._ticks <= TICKS_MAX_GAP:
                shared_boundary = True

            if next_duration >= max_duration_ticks * region._fps:
                gt_max_length = True

        if (acc >= (ideal_duration_ticks * region._fps) and not shared_boundary) or (merge_early and not shared_boundary) or (gt_max_length) or i + 1 == total_entries:
            merged_region = timeregion_merge_sequence(sub_sequence)
            merged_sequences.append({
                                        "age": actor,
                                        "line": merged_english.strip(),
                                        "character": character,
                                        "region": merged_region,
                                    })
            sub_sequence.clear()
            acc = 0.0
            current_start = 0.0
            merged_english = ""
            actor = ""
            character = ""

    return merged_sequences


class Timecode:
    _ticks = 0.0
    _fps = FPS_DEFAULT

    def __init__(self, ticks, fps=FPS_DEFAULT):
        self._ticks = ticks
        self._fps = fps

    def __str__(self):
        return ticks_to_timecode(self._ticks, self._fps)

    def __repr__(self):
        return ticks_to_timecode(self._ticks, self._fps)

    def __eq__(self, rhs):
        return self._ticks == rhs._ticks

    def __ne__(self, rhs):
        return self._ticks != rhs._ticks

    def __gt__(self, rhs):
        return self._ticks > rhs._ticks

    def __lt__(self, rhs):
        return self._ticks < rhs._ticks

    def __add__(self, rhs):
        return Timecode(self._ticks + rhs._ticks)

    def __sub__(self, rhs):
        return Timecode(self._ticks - rhs._ticks)


class TimeRegion:
    _start = 0.0
    _end = 0.0
    _fps = FPS_DEFAULT

    def __init__(self, tcin, tcout, fps=FPS_DEFAULT):
        # TODO: handle fps mismatch between tcin & tcout
        self._start = tcin
        self._end = tcout
        self._fps = fps

    @classmethod
    def from_timecodes(cls, tcin, tcout, fps=FPS_DEFAULT):
        return TimeRegion(tcin, tcout, fps)

    @classmethod
    def from_timecode_strings(cls, tcin, tcout, fps=FPS_DEFAULT):
        return TimeRegion(Timecode(timecode_to_ticks(tcin, fps)), Timecode(timecode_to_ticks(tcout, fps), fps))

    @classmethod
    def from_ticks(cls, ticks_in, ticks_out, fps=FPS_DEFAULT):
        return TimeRegion(Timecode(ticks_in, fps), Timecode(ticks_out, fps), fps)

    def duration_ticks(self):
        return (self._end - self._start)._ticks

    def duration(self):
        return self._end - self._start

    def __str__(self):
        return f"{self._start} --> {self._end}"

    def __repr__(self):
        return f"{self._start} --> {self._end}"
