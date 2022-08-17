import argparse
import json
import os
import subprocess as sp

TICK_RATE = 1000000

def hms_parts(hms):
    split_hms = hms.split(':')
    h = ''
    m = ''
    s = ''

    if len(split_hms[0]) < 2:
        h += '0' + split_hms[0]
    else:
        h += split_hms[0]
    if len(split_hms[1]) < 2:
        m += '0' + split_hms[1]
    else:
        m += split_hms[1]
    if len(split_hms[2]) < 2:
        s += '0' + split_hms[2]
    else:
        s += split_hms[2]

    return h, m, s

def ffprobe_dur_to_tc(path):
    # TODO: check if ffprobe is in user path
    abs_path = os.path.abspath(path)
    cmd_args = ['ffprobe',
                '-v',
                'quiet',
                '-select_streams',
                'v:0',
                '-show_entries',
                'stream=duration,r_frame_rate',
                '-sexagesimal',
                '-of',
                'json',
                '-i',
                abs_path]

    result = json.loads(sp.run(args=cmd_args, capture_output=True, text=True).stdout)

    raw_duration = result['streams'][0]['duration'].split('.')
    frame_rate = float(result['streams'][0]['r_frame_rate'].split('/')[0])
    h, m, s = hms_parts(raw_duration[0])
    dur_frames = int(round(float(raw_duration[1]) / TICK_RATE * frame_rate))

    tc = f'{h}:{m}:{s}:'
    if dur_frames < 10:
        tc += '0' + str(dur_frames)
    else:
        tc += str(dur_frames)

    return tc, frame_rate


def main():
    parser = argparse.ArgumentParser(description='Get run-times of video files in folder')
    parser.add_argument('path', nargs='?', type=str,
                        help='path to file or directory to search for files')
    parser.add_argument('--ext', nargs=1, type=str, default='',
                        help='extension of file to process')
    args = parser.parse_args()

    tc, fps = ffprobe_dur_to_tc(args.path)

    print(f'{args.path}: {tc}')


if __name__ == "__main__":
    main()
