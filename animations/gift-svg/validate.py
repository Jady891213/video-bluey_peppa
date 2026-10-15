"""核验实际MP4完整解码、连续画面PTS及完整原WAV在正确时刻出现。"""
import array
import hashlib
import json
import math
from pathlib import Path
import subprocess
import wave

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'materials/final/gift/待确认成片/SVG_Remotion_佩奇画画_20261015'


def main():
    path = OUT / '制作配方.json'
    recipe = json.loads(path.read_text())
    video_path = OUT / '准备礼物_佩奇画画与乔治拿笔_SVG小样_10秒.mp4'
    subprocess.run(['ffmpeg', '-v', 'error', '-i', str(video_path), '-f', 'null', '-'],
                   check=True, timeout=30, capture_output=True)
    metadata = json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(video_path)]))
    video = next(s for s in metadata['streams'] if s['codec_type'] == 'video')
    audio = next(s for s in metadata['streams'] if s['codec_type'] == 'audio')
    assert (video['width'], video['height'], video['avg_frame_rate'], int(video['nb_frames'])) == (1280,720,'30/1',300)
    assert audio['sample_rate'] == '48000' and audio['channels'] == 2
    assert abs(float(metadata['format']['duration'])-10) < .05
    frames = json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_frames',
        '-show_entries', 'frame=best_effort_timestamp_time', '-of', 'json', str(video_path)]))['frames']
    times = [float(f['best_effort_timestamp_time']) for f in frames]
    assert len(times) == 300 and all(abs(b-a-1/30) < .0001 for a,b in zip(times,times[1:]))
    pcm = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(video_path), '-t', '10',
                                   '-vn', '-ar', '22050', '-ac', '1', '-f', 's16le', '-'])
    decoded = array.array('h', pcm)
    correlations = {}
    for line in recipe['lines']:
        source = ROOT / line['source']
        assert hashlib.sha256(source.read_bytes()).hexdigest() == line['source_sha256']
        with wave.open(str(source)) as wav:
            assert wav.getnchannels() == 1 and wav.getframerate() == 22050
            original = array.array('h', wav.readframes(wav.getnframes()))
        start = round(line['start_sec'] * 22050)
        actual = decoded[start:start+len(original)]
        assert len(actual) == len(original)
        correlation = sum(a*b for a,b in zip(original,actual)) / math.sqrt(
            sum(a*a for a in original) * sum(b*b for b in actual))
        assert correlation > .98, (line['line_id'],correlation)
        correlations[line['line_id']] = round(correlation,6)
    recipe['output'] = {
        'file': video_path.relative_to(ROOT).as_posix(),
        'sha256': hashlib.sha256(video_path.read_bytes()).hexdigest(),
        'bytes': video_path.stat().st_size, 'duration_sec':float(metadata['format']['duration']),
        'width':1280, 'height':720, 'fps':'30/1', 'video_frames':300,
        'codec':'h264', 'audio_codec':'aac', 'audio_hz':48000, 'audio_channels':2}
    recipe['validation'] = {
        'full_decode':'passed', 'continuous_frame_pts':'passed', 'original_voice_sha256':'passed',
        'complete_voice_waveform_correlation':correlations,
        'checked_keyframes':[0,45,90,150,177,206,255,285], 'listening_review':'待用户听审'}
    path.write_text(json.dumps(recipe,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'ok':True,'voice_correlations':correlations},ensure_ascii=False))


if __name__ == '__main__':
    main()
