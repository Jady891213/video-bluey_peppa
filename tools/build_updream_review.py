#!/usr/bin/env python3
"""整理已有 Updream 试片并生成离线对比页；不提交生成请求。"""

import hashlib
import html
import json
import subprocess
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'materials/final/gift/待确认成片/Updream_佩奇模型对比_20261014'
ORIGINAL = ROOT / 'materials/original/gift/动画源片/Updream_佩奇模型对比_20261014'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def media_info(path):
    subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-f', 'null', '-'],
                   check=True, capture_output=True)
    data = json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)
    ]))
    video = next(s for s in data['streams'] if s['codec_type'] == 'video')
    return {'sha256': digest(path), 'bytes': path.stat().st_size,
            'duration_sec': float(data['format']['duration']), 'width': video['width'],
            'height': video['height'], 'fps': video['r_frame_rate'],
            'audio_tracks': sum(s['codec_type'] == 'audio' for s in data['streams'])}


def main():
    manifest = OUT / '测试清单.json'
    data = json.loads(manifest.read_text())
    ORIGINAL.mkdir(parents=True, exist_ok=True)
    (OUT / 'thumbnails').mkdir(exist_ok=True)
    cards = []
    rows = []
    successes = []
    esc = html.escape
    for item in data['tests']:
        native = item.get('native_video')
        if native:
            source = ROOT / native
            if not source.is_file():
                recovered = ORIGINAL / source.name
                if not recovered.is_file():
                    raise FileNotFoundError(native)
                source = recovered
            destination = ORIGINAL / source.name
            if source.resolve() != destination.resolve():
                if destination.exists():
                    if digest(source) != digest(destination):
                        raise ValueError('同名源片不同，不能覆盖：' + destination.name)
                    source.unlink()
                else:
                    source.replace(destination)
            item['native_video'] = destination.relative_to(ROOT).as_posix()
            item['native_result'] = media_info(destination)
            manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
            preview = OUT / destination.name.replace('_原生.mp4', '.mp4')
            subprocess.run([
                'ffmpeg', '-v', 'error', '-y', '-i', str(destination), '-an',
                '-t', str(item['duration_sec']), '-vf',
                'scale=1280:720:force_original_aspect_ratio=decrease,'
                'pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30',
                '-c:v', 'libx264', '-crf', '18', '-preset', 'fast', '-movflags', '+faststart',
                str(preview)
            ], check=True, capture_output=True)
            item['preview_file'] = preview.relative_to(ROOT).as_posix()
            item['preview_result'] = media_info(preview)
            poster = OUT / 'thumbnails' / (item['id'] + '.png')
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', '0.2', '-i', str(preview),
                            '-frames:v', '1', '-vf', 'scale=640:360', str(poster)],
                           check=True, capture_output=True)
            source_image = ROOT / item.get('reference_image', data['reference_image'])
            item['reference_sha256'] = digest(source_image)
            title = item.get('scenario', '佩奇与乔治画礼物 · 同图对照')
            note = item.get('review_note', '试片已返回，等待观看确认。')
            cards.append(f'''<article class="card" data-model="{esc(item['model'])}">
<div class="cardhead"><span>{esc(item['id'])}</span><span>{esc(item['model'])}</span></div>
<video controls playsinline muted preload="none" poster="thumbnails/{item['id']}.png"
 src="{quote(preview.name)}"></video><div class="copy"><h2>{esc(title)}</h2>
<p class="meta">{item['duration_sec']} 秒 · {item.get('charged_credits', item['quoted_credits'])} 积分 · 静音对照</p>
<p>{esc(note)}</p><a download href="{quote(preview.name)}">下载这一条</a></div></article>''')
            successes.append(item)
            outcome = '已生成，待确认'
        else:
            outcome = item.get('result_message', item['status'])
        rows.append(f"<tr><td>{esc(item['id'])}</td><td>{esc(item['model'])}</td>"
                    f"<td>{item['duration_sec']} 秒</td><td>{esc(outcome)}</td>"
                    f"<td>{item.get('charged_credits', '未见计费记录')}</td></tr>")
    data['generated_count'] = len(successes)
    data['generated_duration_sec'] = sum(t['duration_sec'] for t in successes)
    manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    spent = data.get('final_consumed_credits', sum(t.get('charged_credits', 0) for t in data['tests']))
    remaining = data.get('final_remaining_credits', '等待核对')
    page = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>准备礼物 · Updream 模型试片对比</title><style>
*{box-sizing:border-box}body{margin:0;background:#f7f6ef;color:#20332d;font:16px/1.7 system-ui,sans-serif}
main{max-width:1240px;margin:auto;padding:32px 24px 64px}header{padding:24px 0 30px}
.eyebrow,.meta{color:#64756b;font-size:14px}h1{font-size:clamp(28px,5vw,44px);line-height:1.2;margin:12px 0}
h2{font-size:19px;margin:0 0 8px}.summary{padding:16px 20px;background:#e7efdf;border-radius:14px}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:22px;margin:24px 0}
.card{background:white;border:1px solid #dce3d8;border-radius:16px;overflow:hidden}
.cardhead{display:flex;justify-content:space-between;padding:12px 18px;background:#edf2e8;font-weight:650}
video{width:100%;aspect-ratio:16/9;background:#10241e;display:block}.copy{padding:18px 20px}
p{margin:8px 0 14px}a{color:#235f46;text-underline-offset:3px}.scroll{overflow:auto;background:white;border-radius:14px}
table{border-collapse:collapse;width:100%;font-size:14px}th,td{text-align:left;padding:12px 14px;border-bottom:1px solid #e7ece3}
th{background:#edf2e8;white-space:nowrap}td:first-child,td:nth-child(2),td:nth-child(3),td:last-child{white-space:nowrap}
footer{margin-top:24px;color:#64756b;font-size:14px}@media(max-width:680px){main{padding:20px 14px 40px}.grid{grid-template-columns:1fr}.copy{padding:15px}header{padding-top:10px}}
</style><main><header><div class="eyebrow">准备礼物 / 模型与动作测试 / 2026-10-14</div>
<h1>佩奇可以生成了，先看试片。</h1>
<p>同一张厨房参考图先做模型对照，再测试更长的动作、家庭出门和布鲁伊联动。</p>
<div class="summary">SUMMARY</div><p>这些是待确认试片。统一为 1280×720、30fps 静音预览，保留原生源片；正式配音后续使用项目既有角色音轨。</p>
<a href="PROJECT">打开 Updream 测试画布</a></header><section class="grid">CARDS</section>
<h2>所有提交结果与费用</h2><div class="scroll"><table><thead><tr><th>编号</th><th>模型</th><th>时长</th><th>结果</th><th>实扣积分</th></tr></thead><tbody>ROWS</tbody></table></div>
<footer>本轮结果只适用于已测试的素材和参数。生成成功后，人物形体、口型与道具连续性仍需逐镜确认。</footer></main>
<script>document.querySelectorAll('video').forEach(v=>v.addEventListener('play',()=>document.querySelectorAll('video').forEach(o=>{if(o!==v)o.pause()})));</script></html>'''
    page = page.replace('SUMMARY', f"已返回 {len(successes)} 条视频，共 {data['generated_duration_sec']} 秒。已消耗 {spent} 积分，余额 {remaining} 积分。")
    page = page.replace('PROJECT', esc(data['project_url'])).replace('CARDS', '\n'.join(cards)).replace('ROWS', '\n'.join(rows))
    (OUT / '准备礼物_Updream模型试片对比.html').write_text(page)
    print(json.dumps({'generated': len(successes), 'duration': data['generated_duration_sec'],
                      'review': str((OUT / '准备礼物_Updream模型试片对比.html').relative_to(ROOT))}, ensure_ascii=False))


if __name__ == '__main__':
    main()
