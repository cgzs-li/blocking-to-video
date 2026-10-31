#!/usr/bin/env python3
"""Check declared video-plan structure; does not validate media or visual geometry."""
import argparse
import json
import math
import re
from pathlib import Path


def validate(plan, base=Path('.'), check_files=False):
    errors = []

    def require(condition, message):
        if not condition:
            errors.append(message)

    def number(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)

    def unique(items, label):
        ids = [item['id'] for item in items]
        require(all(isinstance(v, str) and v.strip() for v in ids), label + ': invalid id')
        require(len(ids) == len(set(ids)), label + ': duplicate id')
        return {item['id']: item for item in items}

    try:
        characters = set(plan['characters'])
        require(bool(characters), 'characters: empty')
        require(len(characters) == len(plan['characters']), 'characters: duplicate')
        assets = unique(plan['assets'], 'assets')
        identities = {}
        for character in characters:
            matches = [a['id'] for a in assets.values() if a['role'] == 'identity' and a.get('character') == character]
            require(len(matches) == 1, f'{character}: require exactly one identity asset')
            if matches:
                identities[character] = matches[0]
        shared = set()
        for role in ('scene', 'blocking', 'camera'):
            matches = [a['id'] for a in assets.values() if a['role'] == role]
            require(len(matches) == 1, f'{role}: require exactly one core asset')
            shared.update(matches)
        for asset in assets.values():
            require(isinstance(asset['file'], str) and bool(asset['file'].strip()), asset['id'] + ': missing file')
            if check_files:
                require((base / asset['file']).is_file(), asset['id'] + ': referenced file not found')
        cameras = set(plan['cameras'])
        require(bool(cameras), 'cameras: empty')
        lines = unique(plan['dialogue'], 'dialogue')
        for line in lines.values():
            require(line['speaker'] in characters, line['id'] + ': unknown speaker')
            require(isinstance(line['text'], str) and bool(line['text'].strip()), line['id'] + ': empty dialogue')
        pieces = {key: [] for key in lines}
        observed_order = []
        segments = unique(plan['segments'], 'segments')
        require(bool(segments), 'segments: empty')
        all_shot_ids = set()
        for seg in segments.values():
            sid = seg['id']
            active = set(seg['characters'])
            require(bool(active) and active <= characters, sid + ': unknown/empty characters')
            inputs = set(seg['input_assets'])
            require(inputs <= assets.keys(), sid + ': unknown asset input')
            needed = shared | {identities[c] for c in active if c in identities}
            require(needed <= inputs, sid + ': missing core inputs ' + ', '.join(sorted(needed - inputs)))
            require(number(seg['duration']) and seg['duration'] > 0, sid + ': invalid duration')
            for field in ('entry_state', 'exit_state'):
                require(isinstance(seg[field], str) and bool(seg[field].strip()), sid + ': missing ' + field)
            require(bool(seg['shots']), sid + ': empty shots')
            cursor = 0.0
            for shot in seg['shots']:
                shot_id = shot['id']
                require(shot_id not in all_shot_ids, shot_id + ': duplicate shot id')
                all_shot_ids.add(shot_id)
                start, end = shot['start'], shot['end']
                if not (number(start) and number(end) and end > start):
                    errors.append(shot_id + ': invalid times')
                    continue
                require(abs(start - cursor) < 1e-6, shot_id + ': gap or overlap')
                cursor = end
                require(shot['camera'] in cameras, shot_id + ': unknown camera')
                require(active <= shot['blocking'].keys(), shot_id + ': missing character blocking points')
                require(all(isinstance(v, str) and bool(v.strip()) for v in shot['blocking'].values()), shot_id + ': empty blocking point')
                speech_cursor = 0.0
                for speech in shot['speech']:
                    lid = speech['line_id']
                    require(lid in lines, shot_id + ': unknown dialogue id')
                    if lid not in lines:
                        continue
                    require(speech['speaker'] == lines[lid]['speaker'], shot_id + ': wrong speaker')
                    require(speech['speaker'] in active, shot_id + ': speaker missing from segment')
                    require(speech['mode'] in ('on', 'off'), shot_id + ': speech mode must be on/off')
                    a, b = speech['start'], speech['end']
                    require(number(a) and number(b) and 0 <= a < b <= end - start + 1e-6, shot_id + ': invalid speech window')
                    require(number(a) and a >= speech_cursor - 1e-6, shot_id + ': overlapping speech')
                    if number(b):
                        speech_cursor = b
                    pieces[lid].append(speech['text'])
                    if not observed_order or observed_order[-1] != lid:
                        observed_order.append(lid)
            require(number(seg['duration']) and abs(cursor - seg['duration']) < 1e-6, sid + ': duration does not match shots')
        require(observed_order == list(lines), 'dialogue: missing, repeated or reordered turns')
        normalize = lambda text: re.sub(r'\s+', '', text)
        for lid, line in lines.items():
            require(normalize(''.join(pieces[lid])) == normalize(line['text']), lid + ': dialogue changed or incomplete')
    except (KeyError, TypeError, ValueError, AttributeError) as error:
        errors.append('Invalid plan structure: ' + str(error))
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', type=Path)
    parser.add_argument('--check-files', action='store_true', help='Resolve asset files relative to plan JSON')
    args = parser.parse_args()
    try:
        plan = json.loads(args.plan.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError) as error:
        print('Cannot read plan: ' + str(error))
        return 2
    errors = validate(plan, args.plan.parent, args.check_files)
    for error in errors:
        print('ERROR: ' + error)
    if not errors:
        print('PASS: structural checks only; media and visual continuity remain unverified.')
    return int(bool(errors))


if __name__ == '__main__':
    raise SystemExit(main())
