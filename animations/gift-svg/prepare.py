"""从既有完整WAV生成30fps口型音量门控；不合成、不修改原配音。"""
from pathlib import Path
import array
import hashlib
import json
import math
import wave

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FPS = 30
OUT = ROOT / 'materials/final/gift/待确认成片/SVG_Remotion_佩奇画画_20261015'
LINES = [('GIFT-L028', 'peppa', 20), ('GIFT-L029', 'george', 135)]


def finite_mix(recipe):
    """先写有限长PCM，避免流式滤镜补静音造成编码时间戳异常。"""
    rate = 48000
    count = rate * 10
    left = array.array('d', [0.0]) * count
    right = array.array('d', [0.0]) * count
    for line in recipe['lines']:
        with wave.open(str(ROOT / line['source'])) as wav:
            source_rate, channels = wav.getframerate(), wav.getnchannels()
            assert wav.getsampwidth() == 2
            values = array.array('h', wav.readframes(wav.getnframes()))[::channels]
        start = line['start_frame'] * 1600
        gain = 10 ** (line['gain_db'] / 20) / 32768
        for i in range(round(len(values) * rate / source_rate)):
            if start + i >= count:
                raise ValueError('完整音轨超出视频')
            position = i * source_rate / rate
            j = int(position)
            u = position - j
            sample = (values[j] * (1-u) + values[min(j+1, len(values)-1)] * u) * gain
            left[start+i] += sample
            right[start+i] += sample
    with wave.open(str(ROOT / recipe['music']['source'])) as wav:
        assert wav.getsampwidth() == 2 and wav.getframerate() == rate
        channels = wav.getnchannels()
        music = array.array('h', wav.readframes(count))
    gain = 10 ** (recipe['music']['gain_db'] / 20) / 32768
    for i in range(min(count, len(music)//channels)):
        envelope = min(1, i/(rate*.5), (count-1-i)/(rate*.6))
        left[i] += music[i*channels] * gain * envelope
        right[i] += music[i*channels+min(1, channels-1)] * gain * envelope
    peak = max(max(abs(x) for x in left), max(abs(x) for x in right))
    if peak >= 1:
        raise ValueError('混音削波')
    pcm = array.array('h')
    for a,b in zip(left,right):
        pcm.extend([round(a*32767), round(b*32767)])
    tmp = ROOT / 'TMP to delete - SVG小样'
    tmp.mkdir(exist_ok=True)
    with wave.open(str(tmp/'dialogue-mix.wav'), 'wb') as wav:
        wav.setnchannels(2); wav.setsampwidth(2); wav.setframerate(rate)
        wav.writeframes(pcm.tobytes())
    return {'frames':count, 'sample_rate':rate, 'channels':2, 'peak_dbfs':round(20*math.log10(peak),3)}


def main():
    source = json.loads((ROOT / 'materials/final/gift/voice-manifest.json').read_text())
    by_id = {x['line_id']: x for x in source['lines']}
    envelopes = {'peppa': [0.0] * 300, 'george': [0.0] * 300}
    recipe = {'story': '准备礼物', 'technique': 'SVG + Remotion', 'fps': FPS,
              'width': 1280, 'height': 720, 'duration_sec': 10, 'frames': 300,
              'status': '待用户确认，独立动作试片，未加入已采纳或网站',
              'camera': '固定镜位，分层SVG，头/眼/口/手臂/蜡笔独立驱动',
              'source_directory': 'animations/gift-svg', 'lines': []}
    for line_id, role, start in LINES:
        line = by_id[line_id]
        path = ROOT / line['wav_file']
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        if sha != line['wav_sha256']:
            raise ValueError('原配音SHA不符：' + line_id)
        with wave.open(str(path)) as wav:
            rate = wav.getframerate()
            channels = wav.getnchannels()
            assert wav.getsampwidth() == 2
            samples = array.array('h', wav.readframes(wav.getnframes()))
        values = [x / 32768 for x in samples[::channels]]
        peak = max(abs(x) for x in values)
        rms = math.sqrt(sum(x*x for x in values) / len(values))
        gain_db = min(-20 - 20*math.log10(rms), -3 - 20*math.log10(peak))
        energies = []
        for f in range(math.ceil(len(values)/rate*FPS)):
            a = max(0, round((f/FPS-.012)*rate))
            b = min(len(values), round((f/FPS+.028)*rate))
            chunk = values[a:b]
            energies.append(math.sqrt(sum(x*x for x in chunk)/max(1, len(chunk))))
        reference = sorted(energies)[round(len(energies)*.9)]
        for f, energy in enumerate(energies):
            if f + start >= 300:
                raise ValueError('完整配音超出片长')
            normalized = max(0, min(1, (energy / reference - .09) / .9))
            envelopes[role][f+start] = round(normalized, 4)
        recipe['lines'].append({
            'line_id': line_id, 'speaker': line['speaker'], 'text': line['text'],
            'source': line['wav_file'], 'source_sha256': sha,
            'start_frame': start, 'start_sec': start/FPS,
            'source_duration_sec': line['duration_s'], 'gain_db': round(gain_db, 4),
            'playback_rate': 1, 'trimmed': False})
    music = 'materials/original/gift/music/peppa-lullaby-instrumental-selected.wav'
    recipe['music'] = {'source': music, 'gain_db': -30,
                       'source_sha256': hashlib.sha256((ROOT/music).read_bytes()).hexdigest(),
                       'fade_in_sec': .5, 'fade_out_sec': .6}
    recipe['mouth_method'] = '同角色完整音轨的短窗RMS控制开合；只在说话时段启用，不声称逐音素精确口型'
    recipe['actions'] = [
        {'time': [1.18, 4.55], 'action': '佩奇的蓝色蜡笔沿笔迹路径分段画画，换笔画时抬笔'},
        {'time': [4.7, 5.6], 'action': '乔治手掌伸向桌上的唯一绿色蜡笔'},
        {'time': [5.6, 6.45], 'action': '同一绿色蜡笔从桌面抬起并始终跟随手掌'},
        {'time': [8.2, 9.5], 'action': '佩奇补足球轮廓，乔治在纸右侧添绿色恐龙'},
        {'time': [9.5, 10], 'action': '抬笔、侧目与收尾微笑'}]
    recipe['mix'] = finite_mix(recipe)
    OUT.mkdir(parents=True, exist_ok=True)
    (HERE/'src/speech.json').write_text(json.dumps(envelopes, separators=(',', ':'))+'\n')
    (OUT/'制作配方.json').write_text(json.dumps(recipe, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'duration':10,'lines':recipe['lines']},ensure_ascii=False))


if __name__ == '__main__':
    main()
