#!/usr/bin/env python3
"""按保存的配方逐镜生成、核验与组装《准备礼物》两段开场。

生成调用只使用官方 OiiOii CLI。submit 必须已通过 dry-run，存在任务ID则不重复提交。
临时输入、下载与转码放项目根 TMP to delete 目录；最终仅保存选定参考与两段结果。
"""
import argparse
import array
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import wave

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'materials/final/gift/准备礼物_完整开场两段_Wan3'
TMP = ROOT / 'TMP to delete - 准备礼物完整开场制作'
MANIFEST = OUT / '生成配方.json'
CLI = shutil.which('oiioii') or str(Path.home() / '.local/bin/oiioii')


def read():
    return json.loads(MANIFEST.read_text())


def save(m):
    MANIFEST.write_text(json.dumps(m, ensure_ascii=False, indent=2) + '\n')


def api(m, *args):
    r = subprocess.run([CLI, '--json', '--workspace', m['workspace_id'], *args],
                       text=True, capture_output=True)
    d = json.loads(r.stdout)
    if not d.get('ok'):
        raise RuntimeError(json.dumps(d.get('error', d), ensure_ascii=False))
    return d['data']


def audio(s):
    TMP.mkdir(exist_ok=True)
    fs = 22050
    samples = array.array('h', [0] * round(s['duration_sec'] * fs))
    for line in s['lines']:
        src = ROOT / line['source']
        source_hash = hashlib.sha256(src.read_bytes()).hexdigest()
        if line.get('source_sha256'):
            assert line['source_sha256'] == source_hash, 'Selected dialogue source changed'
        with wave.open(str(src)) as w:
            assert (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (fs, 1, 2)
            raw = array.array('h', w.readframes(w.getnframes()))
        rms = math.sqrt(sum(x*x for x in raw) / len(raw)) / 32768
        gain = min(10 ** (-23/20) / rms, .8 * 32768 / max(abs(x) for x in raw))
        start = round(line['offset_sec'] * fs)
        assert start + len(raw) <= len(samples), 'Do not cut spoken words'
        samples[start:start+len(raw)] = array.array('h', [round(x*gain) for x in raw])
        line['duration_sec'] = len(raw) / fs
        line['gain_db'] = round(20 * math.log10(gain), 3)
        line['source_sha256'] = source_hash
    file = TMP / (s['id'] + '-dialogue.wav')
    with wave.open(str(file), 'wb') as w:
        w.setparams((1, 2, fs, len(samples), 'NONE', 'not compressed'))
        w.writeframes(samples.tobytes())
    return file


def request(m, s, dry=False):
    args = ['video', 'generate', '--model-id', str(m['model_id']),
            '--duration', str(s.get('generation_duration_sec', s['duration_sec'])), '--resolution', m['resolution'],
            '--aspect-ratio', '16:9', '--mode', 'omni2Video' if s.get('audio_uri') else 'firstframe2Video',
            '--prompt', (OUT / s['prompt_file']).read_text(), '--image', s['image_uri']]
    if s.get('audio_uri'):
        args += ['--audio', s['audio_uri']]
    if dry:
        args += ['--dry-run']
    return api(m, *args)


def probe(p):
    return json.loads(subprocess.check_output(
        ['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(p)], text=True))


def export(m, s):
    src = TMP / (s['id'] + '-native.mp4')
    dst = TMP / (s['id'] + '-selected.mp4')
    d = probe(src)
    tags = d['format'].get('tags', {})
    filters = []
    if s.get('trim_start_sec'):
        filters += [f"trim=start={s['trim_start_sec']}", 'setpts=PTS-STARTPTS']
    if s.get('crop'):
        c = s['crop']
        assert c['width'] * 9 == c['height'] * 16, 'Keep the selected framing 16:9'
        filters.append(f"crop={c['width']}:{c['height']}:{c['x']}:{c['y']}")
    filters += ['scale=1280:720:force_original_aspect_ratio=decrease',
                'pad=1280:720:(ow-iw)/2:(oh-ih)/2', 'setsar=1', 'fps=30']
    vf = ','.join(filters)
    # 中间片只留画面，避免每镜AAC填充时长影响拼接；对白在完整时轴上只编码一次。
    cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(src),
           '-map', '0:v:0', '-an', '-vf', vf, '-c:v', 'libx264', '-crf', '18',
           '-preset', 'medium', '-pix_fmt', 'yuv420p', '-t', str(s['duration_sec']),
           '-map_metadata', '-1', '-movflags', '+faststart+use_metadata_tags',
           '-metadata', 'comment=AI生成画面：Wan3.0；现有AI对白；制作镜头']
    for k in ['AIGC', 'HOGI_GENERATION']:
        if k in tags:
            cmd += ['-metadata', k + '=' + tags[k]]
    cmd += [str(dst)]
    subprocess.run(cmd, check=True)
    s['selected_sha256'] = hashlib.sha256(dst.read_bytes()).hexdigest()
    return dst


def compose(m):
    voice_parts = array.array('h')
    lengths = {}
    for segment in m['segments']:
        samples = array.array('h')
        for s in m['shots']:
            if s['segment'] == segment['id']:
                with wave.open(str(audio(s))) as w:
                    samples.extend(array.array('h', w.readframes(w.getnframes())))
        stem = OUT / (segment['id'] + '-clean-dialogue.wav')
        with wave.open(str(stem), 'wb') as w:
            w.setparams((1, 2, 22050, len(samples), 'NONE', 'not compressed'))
            w.writeframes(samples.tobytes())
        voice_parts.extend(samples)
        lengths[segment['id']] = len(samples) / 22050
        segment['dialogue_stem'] = dict(file=stem.name, sha256=hashlib.sha256(stem.read_bytes()).hexdigest())
    voice = TMP / 'opening-full-dialogue.wav'
    with wave.open(str(voice), 'wb') as w:
        w.setparams((1, 2, 22050, len(voice_parts), 'NONE', 'not compressed'))
        w.writeframes(voice_parts.tobytes())
    full_duration = len(voice_parts) / 22050
    mix = voice
    if m.get('music'):
        music = ROOT / m['music']['file']
        with wave.open(str(music)) as w:
            raw = array.array('h', w.readframes(w.getnframes()))
        rms = math.sqrt(sum(x*x for x in raw) / len(raw)) / 32768
        gain = 10 ** (m['music']['target_rms_dbfs'] / 20) / rms
        mix = TMP / 'opening-full-mix.wav'
        filt = ('[1:a][2:a]acrossfade=d=1:c1=tri:c2=tri[m1];'
                '[m1][3:a]acrossfade=d=1:c1=tri:c2=tri[m2];'
                f'[m2]volume={gain},afade=t=in:d=0.5,'
                f'afade=t=out:st={full_duration-.6}:d=0.6[bg];'
                '[0:a]pan=stereo|c0=c0|c1=c0[v];'
                '[v][bg]amix=inputs=2:duration=first:normalize=0[a]')
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(voice),
                        '-i', str(music), '-i', str(music), '-i', str(music),
                        '-filter_complex', filt, '-map', '[a]', '-ar', '48000', '-ac', '2',
                        '-t', str(full_duration), '-c:a', 'pcm_s16le', str(mix)], check=True)
    offset = 0
    for segment in m['segments']:
        shots = [s for s in m['shots'] if s['segment'] == segment['id']]
        for s in shots:
            assert s.get('review', {}).get('accepted'), 'Review each shot before assembly'
            export(m, s)
        concat = TMP / (segment['id'] + '-concat.txt')
        concat.write_text(''.join("file '" + s['id'] + "-selected.mp4'\n" for s in shots))
        picture = TMP / (segment['id'] + '-picture.mp4')
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'concat',
                        '-safe', '0', '-i', str(concat), '-c', 'copy', '-map_metadata', '-1',
                        '-an', '-movflags', '+faststart', str(picture)], check=True)
        out = OUT / segment['file']
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(picture),
                        '-ss', str(offset), '-t', str(lengths[segment['id']]), '-i', str(mix),
                        '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy', '-c:a', 'aac',
                        '-b:a', '192k', '-ar', '48000', '-ac', '2', '-map_metadata', '-1',
                        '-movflags', '+faststart+use_metadata_tags', '-metadata',
                        'title=' + segment['title'], '-metadata',
                        'comment=AI生成动画：Wan3.0；沿用现有AI对白；未包含用户自备原版片头',
                        '-metadata', 'AI_GENERATED=1', str(out)], check=True)
        d = probe(out)
        v = next(x for x in d['streams'] if x['codec_type'] == 'video')
        segment['result'] = dict(sha256=hashlib.sha256(out.read_bytes()).hexdigest(),
                                 bytes=out.stat().st_size, duration_sec=float(d['format']['duration']),
                                 width=v['width'], height=v['height'], fps=v['r_frame_rate'])
        cursor = 0
        segment['timeline'] = []
        for s in shots:
            segment['timeline'].append(dict(id=s['id'], start_sec=cursor,
                                             end_sec=cursor+s['duration_sec'], lines=s['lines']))
            cursor += s['duration_sec']
        print(json.dumps({'segment': segment['id'], **segment['result']}, ensure_ascii=False), flush=True)
        offset += lengths[segment['id']]
        save(m)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('command', choices=['upload', 'validate', 'submit', 'status', 'download', 'compose'])
    p.add_argument('--shots', nargs='*')
    a = p.parse_args()
    m = read()
    shots = [s for s in m['shots'] if not a.shots or s['id'] in a.shots]
    if a.command == 'compose':
        compose(m)
        return
    for s in shots:
        if a.command == 'upload':
            ref = ROOT / s['reference']
            if not ref.exists():
                print(s['id'], 'reference pending', flush=True)
                continue
            if not s.get('image_uri'):
                d = api(m, 'upload', 'file', str(ref), '--name', '准备礼物完整开场-' + s['id'] + '-首帧')
                s['image_uri'] = d['uri']
                s['reference_sha256'] = hashlib.sha256(ref.read_bytes()).hexdigest()
                save(m)
            if s['lines'] and not s.get('audio_uri'):
                d = api(m, 'upload', 'file', str(audio(s)), '--name', '准备礼物完整开场-' + s['id'] + '-现有AI对白')
                s['audio_uri'] = d['uri']
        elif a.command == 'validate':
            d = request(m, s, True)
            assert d['valid']
            s['validation'] = dict(valid=True, points=d['estimate']['points'],
                                    method=d['resolved']['mcp_method_name'],
                                    mode=d['resolved']['arguments']['generateMode'], warnings=d['warnings'])
        elif a.command == 'submit':
            if s.get('task'):
                print(s['id'], 'task exists; skip resubmission', flush=True)
                continue
            assert s.get('validation', {}).get('valid')
            if s.get('submission_pending'):
                raise RuntimeError(s['id'] + ' 上次提交结果未知：请先查询官方任务记录，不能直接重复收费生成')
            s['submission_pending'] = True
            save(m)
            d = request(m, s)
            assert d.get('task_id'), 'Submission outcome unknown; inspect the original task before retry'
            s['task'] = {k:d.get(k) for k in ['task_id', 'local_task_id', 'status', 'model', 'generation_mode']}
            s.pop('submission_pending', None)
        elif a.command == 'status':
            if not s.get('task'):
                continue
            d = api(m, 'task', 'status', s['task']['task_id'])
            t = d.get('task', d)
            s['status'] = {k:t.get(k) for k in ['status', 'progress', 'backendAssetId', 'resourceUris', 'error'] if t.get(k) is not None}
            s['task']['status'] = t.get('status')
        elif a.command == 'download':
            if s.get('status', {}).get('status') != 'succeeded':
                continue
            TMP.mkdir(exist_ok=True)
            uri = s['status']['resourceUris'][0]
            target = TMP / (s['id'] + '-native.mp4')
            if not target.exists():
                pending = TMP / (s['id'] + '-download-TMP to delete.mp4')
                api(m, 'record', 'open', uri, '-o', str(pending), '--no-open')
                probe(pending)
                pending.replace(target)
            probe(target)
            d = api(m, 'points', 'cost', uri)
            s['charged_points'] = d['entries'][0].get('consumed_points')
        save(m)
        print(json.dumps({'shot': s['id'], 'validation': s.get('validation'),
                          'task': s.get('task'), 'status': s.get('status'),
                          'charged_points': s.get('charged_points')}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
