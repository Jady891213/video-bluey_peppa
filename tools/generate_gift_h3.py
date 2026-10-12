#!/usr/bin/env python3
"""MiniMax H3 参考生成：明确提交、恢复查询、完整原声拼接。密钥仅读本机CLI配置。"""

import argparse
import base64
import datetime
import hashlib
import json
import math
import mimetypes
import subprocess
import urllib.error
import urllib.request
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TMP = ROOT / "TMP to delete - H3制作"


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".writing")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    temp.replace(path)


def local(name):
    path = (ROOT / name).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError("素材路径越界")
    return path


def run(args):
    result = subprocess.run(args, capture_output=True)
    if result.returncode:
        raise RuntimeError(Path(args[0]).name + ": " + result.stderr.decode(errors="replace")[-2000:])
    return result


def quota():
    raw = json.loads(run(["mmx", "quota", "--output", "json"]).stdout)
    return {"checked_at": now(), "windows": [
        {k: row.get(k) for k in (
            "model_name", "current_interval_remaining_percent",
            "current_weekly_remaining_percent", "end_time", "weekly_end_time")}
        for row in raw.get("model_remains", [])
    ]}


def api(method, endpoint, payload=None):
    config = json.loads((Path.home() / ".mmx/config.json").read_text())
    key = config["api_key"]
    base = "https://api.minimaxi.com" if config.get("region") == "cn" else "https://api.minimax.io"
    body = json.dumps(payload, ensure_ascii=False).encode() if payload else None
    req = urllib.request.Request(base + endpoint, data=body, method=method, headers={
        "Authorization": "Bearer " + key, "Content-Type": "application/json"
    })
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            data = json.load(response)
    except urllib.error.HTTPError as error:
        try:
            detail = json.load(error).get("error", {})
        except (ValueError, AttributeError):
            detail = {}
        message = str(detail.get("message", "API请求失败")).replace(key, "[已隐藏]")
        raise RuntimeError(f"HTTP {error.code}: {message[:400]}") from None
    # 不保存请求头、Data URI或下载签名URL。
    return data


def probe(path):
    data = json.loads(run(["ffprobe", "-v", "error", "-show_streams", "-show_format",
                           "-of", "json", str(path)]).stdout)
    stream = next(s for s in data["streams"] if s["codec_type"] == "video")
    return {"sha256": digest(path), "bytes": path.stat().st_size,
            "duration_sec": float(data["format"]["duration"]),
            "width": stream["width"], "height": stream["height"],
            "fps": stream["r_frame_rate"], "frames": int(stream.get("nb_frames", 0))}


def dialogue(clip, length=None, final=False):
    """只叠完整原WAV，原生采样率不变；响度增益不改变说话速度。"""
    rate = 22050
    duration = length if length is not None else (clip["duration_sec"] if final else
                                                 clip.get("generation_duration_sec", clip["duration_sec"]))
    samples = [0] * round(duration * rate)
    import array
    for line in clip["lines"]:
        source = local(line["source"])
        with wave.open(str(source), "rb") as w:
            if (w.getframerate(), w.getnchannels(), w.getsampwidth()) != (rate, 1, 2):
                raise ValueError("原声格式变化，请显式处理")
            raw = array.array("h", w.readframes(w.getnframes()))
        start_sec = line.get("final_start_sec", line["start_sec"]) if final else line["start_sec"]
        start = round(start_sec * rate)
        if start + len(raw) > len(samples):
            raise ValueError(f"音轨不能容纳完整台词 {line['id']}")
        rms = math.sqrt(sum(v * v for v in raw) / len(raw)) / 32768
        peak = max(abs(v) for v in raw) / 32768
        factor = min(10 ** (-21 / 20) / max(rms, 1e-9), 0.91 / max(peak, 1e-9))
        line["source_sha256"] = digest(source)
        line["duration_sec"] = len(raw) / rate
        line["gain_db"] = round(20 * math.log10(factor), 3)
        for i, v in enumerate(raw):
            samples[start + i] += round(v * factor)
    if max(abs(v) for v in samples) > 32767:
        raise ValueError("对白叠加削波")
    kind = "final" if final else "reference"
    out = TMP / f"{clip['id']}-{kind}-dialogue.wav"
    out.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out), "wb") as w:
        w.setparams((1, 2, rate, 0, "NONE", "not compressed"))
        w.writeframes(array.array("h", samples).tobytes())
    return out


def payload_for(plan, clip):
    clip["prompt_sha256"] = digest(local(clip["prompt_file"]))
    clip["reference_image_sha256"] = {image: digest(local(image)) for image in clip["reference_images"]}
    content = [{"type": "text", "text": local(clip["prompt_file"]).read_text()}]
    first_frame = clip.get("input_mode") == "first_frame"
    if first_frame and (len(clip["reference_images"]) != 1 or clip.get("reference_video")):
        raise ValueError("首帧模式必须是单图，不能混参考音视频")
    for image in clip["reference_images"]:
        p = local(image)
        mime = mimetypes.guess_type(p.name)[0] or "image/png"
        content.append({"type": "image_url", "image_url": {"url":
            f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()},
            "role": "first_frame" if first_frame else "reference_image"})
    if first_frame:
        return {"model": plan["model"], "content": content,
                "duration": clip.get("generation_duration_sec", clip["duration_sec"]),
                "resolution": plan["resolution"], "ratio": plan["ratio"]}
    reference = clip.get("reference_video")
    if reference:
        out = TMP / f"{clip['id']}-motion-reference.mp4"
        run(["ffmpeg", "-v", "error", "-y", "-ss", str(reference["start_sec"]),
             "-i", str(local(reference["source"])), "-t", str(reference["duration_sec"]),
             "-an", "-vf", "scale=1280:720,fps=24", "-c:v", "libx264", "-crf", "20", str(out)])
        content.append({"type": "video_url", "video_url": {"url":
            "data:video/mp4;base64," + base64.b64encode(out.read_bytes()).decode()},
            "role": "reference_video"})
    groups = clip.get("audio_reference_groups")
    if groups:
        if len(groups) > 3:
            raise ValueError("H3最多3份声音参考")
        total = 0
        for i, group in enumerate(groups):
            entries = []
            length = 0
            for id in group["line_ids"]:
                line = dict(next(l for l in clip["lines"] if l["id"] == id))
                line["start_sec"] = length
                with wave.open(str(local(line["source"]))) as w:
                    length += w.getnframes() / w.getframerate()
                entries.append(line)
                length += group.get("gap_sec", 0.12)
            length -= group.get("gap_sec", 0.12)
            if not 2 <= length <= 15:
                raise ValueError("每份H3声音参考必须为2–15秒")
            total += length
            audio = dialogue({"id": f"{clip['id']}-voice{i+1}",
                              "duration_sec": length, "lines": entries})
            group["duration_sec"] = length
            group["sha256"] = digest(audio)
            group["source_entries"] = entries
            content.append({"type": "audio_url", "audio_url": {"url":
                "data:audio/wav;base64," + base64.b64encode(audio.read_bytes()).decode()},
                "role": "reference_audio"})
        if total > 15:
            raise ValueError("H3声音参考总时长不得超过15秒")
    else:
        audio = dialogue(clip)
        clip["reference_audio_sha256"] = digest(audio)
        content.append({"type": "audio_url", "audio_url": {"url":
            "data:audio/wav;base64," + base64.b64encode(audio.read_bytes()).decode()},
            "role": "reference_audio"})
    return {"model": plan["model"], "content": content,
            "duration": clip.get("generation_duration_sec", clip["duration_sec"]), "resolution": plan["resolution"],
            "ratio": plan["ratio"]}


def submit(plan, clip, path):
    if clip.get("task_id") or clip.get("submission", {}).get("state") in ("pending", "unknown"):
        raise ValueError("已有任务或未知提交结果；请先查询，不自动重复扣费")
    payload = payload_for(plan, clip)
    if len(json.dumps(payload).encode()) > 64 * 1024 * 1024:
        raise ValueError("请求体超过64MiB")
    clip["quota_before"] = quota()
    clip["submission"] = {"state": "pending", "started_at": now()}
    save(path, plan)
    try:
        response = api("POST", "/v2/video_generation", payload)
        task_id = response.get("task_id")
        if not task_id:
            raise RuntimeError("接口未返回task_id；先查历史再决定")
    except RuntimeError as error:
        unknown = str(error).startswith(("HTTP 5", "HTTP 408", "HTTP 409")) or "未返回task_id" in str(error)
        clip["submission"].update(state="unknown" if unknown else "rejected", error=str(error))
        save(path, plan)
        raise
    except Exception:
        clip["submission"]["state"] = "unknown"
        save(path, plan)
        raise RuntimeError("提交响应未知，不能直接重发；先查询任务列表") from None
    clip["task_id"] = str(task_id)
    clip["submission"].update(state="submitted", completed_at=now())
    save(path, plan)
    print(json.dumps({"clip": clip["id"], "task_id": clip["task_id"],
                      "duration": clip.get("generation_duration_sec", clip["duration_sec"]),
                      "resolution": plan["resolution"]}, ensure_ascii=False))


def status(plan, clip, path):
    data = api("GET", "/v2/query/video_generation/" + clip["task_id"])
    task = data.get("task", data)
    state = task.get("status")
    clip["backend_status"] = state
    clip["last_checked_at"] = now()
    if state in ("succeeded", "success", "completed"):
        target = local(clip["native_video"])
        if not target.exists():
            content = task.get("content", {})
            url = content.get("url") if isinstance(content, dict) else None
            if not url:
                raise RuntimeError("成功任务缺少下载URL")
            TMP.mkdir(exist_ok=True)
            downloading = TMP / f"{clip['id']}.download"
            with urllib.request.urlopen(url, timeout=90) as response, downloading.open("wb") as out:
                while block := response.read(1024 * 1024):
                    out.write(block)
            run(["ffmpeg", "-v", "error", "-i", str(downloading), "-f", "null", "-"])
            target.parent.mkdir(parents=True, exist_ok=True)
            downloading.replace(target)
        clip["native_result"] = probe(target)
        if "quota_after" not in clip:
            clip["quota_after"] = quota()
    elif state in ("failed", "cancelled", "expired"):
        error = task.get("error") or {}
        clip["failure"] = {"code": error.get("code"), "message": str(error.get("message", "generation_failed"))[:300]}
        if "quota_after" not in clip:
            clip["quota_after"] = quota()
    save(path, plan)
    print(json.dumps({"clip": clip["id"], "status": state,
                      "result": clip.get("native_result")}, ensure_ascii=False))


def render(plan, clip, path):
    source = local(clip["native_video"])
    native = probe(source)
    length = clip["duration_sec"]
    # 不加速人物动作；原生视频尾部可能有AAC填充，按约定时长规范化。
    frames = round(length * 30)
    audio = dialogue(clip, length, final=True)
    clip["rendered_dialogue_sha256"] = digest(audio)
    target = local(clip["final_video"])
    target.parent.mkdir(parents=True, exist_ok=True)
    music = plan.get("music", {}).get(clip["act"])
    args = ["ffmpeg", "-v", "error", "-y", "-i", str(source), "-i", str(audio)]
    if music:
        args += ["-stream_loop", "-1", "-i", str(local(music["source"]))]
        volume = music["linear_gain"]
        af = (f"[1:a]aresample=48000,pan=stereo|c0=c0|c1=c0[voice];"
              f"[2:a]aresample=48000,volume={volume},afade=t=in:d=0.5,"
              f"afade=t=out:st={length-.7}:d=0.7[bg];"
              "[voice][bg]amix=inputs=2:duration=first:normalize=0[a]")
    else:
        af = "[1:a]aresample=48000,pan=stereo|c0=c0|c1=c0[a]"
    suffix = clip.get("replacement_suffix")
    replacement = clip.get("replacement_prefix")
    fixed = clip.get("fixed_opening_crop")
    if suffix:
        index = 3 if music else 2
        args += ["-i", str(local(suffix["source"]))]
        start = suffix["start_frame"]
        remaining = round(length * suffix["source_fps"]) - start
        vf = (f"[0:v]trim=end_frame={start},scale=1280:720:force_original_aspect_ratio=increase,"
              f"crop=1280:720,setsar=1,setpts=PTS-STARTPTS[vfirst];"
              f"[{index}:v]trim=start_frame={suffix.get('source_start_frame', 0)},setpts=PTS-STARTPTS,"
              f"fps={suffix['source_fps']},tpad=stop_mode=clone:stop_duration=1,"
              f"trim=end_frame={remaining},scale=1280:720:force_original_aspect_ratio=increase,"
              f"crop=1280:720,setsar=1,setpts=PTS-STARTPTS[vrest];"
              f"[vfirst][vrest]concat=n=2:v=1:a=0[edited];[edited]")
    elif replacement:
        index = 3 if music else 2
        args += ["-i", str(local(replacement["source"]))]
        end = replacement["end_frame"]
        vf = (f"[{index}:v]trim=end_frame={end},scale=1280:720:force_original_aspect_ratio=increase,"
              f"crop=1280:720,setsar=1,setpts=PTS-STARTPTS[vfirst];"
              f"[0:v]trim=start_frame={end},scale=1280:720:force_original_aspect_ratio=increase,"
              f"crop=1280:720,setsar=1,setpts=PTS-STARTPTS[vrest];"
              f"[vfirst][vrest]concat=n=2:v=1:a=0[edited];[edited]")
    elif fixed:
        end = fixed["end_frame"]
        vf = (f"[0:v]split=2[first][rest];"
              f"[first]trim=end_frame={end},crop={fixed['width']}:{fixed['height']}:{fixed['x']}:{fixed['y']},"
              f"scale=1280:720,setsar=1,setpts=PTS-STARTPTS[vfirst];"
              f"[rest]trim=start_frame={end},scale=1280:720:force_original_aspect_ratio=increase,"
              f"crop=1280:720,setsar=1,setpts=PTS-STARTPTS[vrest];"
              f"[vfirst][vrest]concat=n=2:v=1:a=0[edited];[edited]")
    else:
        vf = "[0:v]"
    vf += (f"scale=1280:720:force_original_aspect_ratio=increase,"
          f"crop=1280:720,setsar=1,fps=30,"
          f"tpad=stop_mode=clone:stop_duration=1,trim=end_frame={frames},setpts=PTS-STARTPTS[v]")
    args += ["-filter_complex", vf + ";" + af, "-map", "[v]", "-map", "[a]",
             "-t", str(length), "-c:v", "libx264", "-preset", "medium", "-crf", "18",
             "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
             "-ac", "2", "-movflags", "+faststart", str(target)]
    run(args)
    run(["ffmpeg", "-v", "error", "-i", str(target), "-f", "null", "-"])
    clip["final_result"] = probe(target)
    clip["native_result"] = native
    save(path, plan)
    print(json.dumps({"clip": clip["id"], "result": clip["final_result"]}, ensure_ascii=False))


def write_subtitles(plan):
    """字幕使用成片时轴，保留说话人；已采纳片段的时轴读其原配方。"""
    assembly = plan["assembly"]
    accepted = json.loads(local(assembly["accepted_recipe"]).read_text())
    entries = []
    offset = 0
    for id in assembly["sequence"]:
        if id == "T":
            part = assembly["title_card"]
            lines = [dict(part["line"])]
            duration = part["duration_sec"]
        elif id in assembly["accepted_sources"]:
            part = next(s for s in accepted["segments"] if s["id"] == id)
            duration = assembly["accepted_sources"][id]["duration_sec"]
            lines = [dict(line, start_sec=shot["start_sec"] + line["offset_sec"])
                     for shot in part["timeline"] for line in shot["lines"]]
        else:
            part = next(c for c in plan["clips"] if c["id"] == id)
            lines = part["lines"]
            duration = part["duration_sec"]
        for line in lines:
            start = line.get("final_start_sec", line["start_sec"])
            end = start + line["duration_sec"]
            if start < 0 or end > duration:
                raise ValueError(f"字幕或完整台词越过片段边界：{line['id']}")
            entries.append({"id": line["id"], "speaker": line["speaker"],
                            "text": line["text"], "start_sec": round(offset + start, 6),
                            "end_sec": round(offset + end, 6)})
        offset += duration
    entries.sort(key=lambda e: e["start_sec"])
    if len({e["id"] for e in entries}) != len(entries):
        raise ValueError("合成时轴重复使用了台词")

    def timestamp(seconds):
        ms = round(seconds * 1000)
        return f"{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}"

    out = local(assembly["subtitles"])
    out.write_text("\n\n".join(
        f"{i}\n{timestamp(e['start_sec'])} --> {timestamp(e['end_sec'])}\n"
        f"{e['speaker']}：{e['text']}" for i, e in enumerate(entries, 1)
    ) + "\n", encoding="utf-8")
    assembly["subtitle_sha256"] = digest(out)
    assembly["dialogue_timeline"] = entries


def assemble(plan, path):
    assembly = plan["assembly"]
    title = assembly["title_card"]
    title_video = TMP / "episode-title.mp4"
    title_audio = dialogue({"id": "T", "duration_sec": title["duration_sec"],
                            "lines": [title["line"]]})
    run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", str(local(title["image"])),
         "-i", str(title_audio), "-vf", "scale=1280:720,setsar=1,fps=30", "-t", str(title["duration_sec"]),
         "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac",
         "-ar", "48000", "-ac", "2", "-b:a", "192k", str(title_video)])
    inputs = []
    for id in assembly["sequence"]:
        if id == "T":
            inputs.append((title_video, title["duration_sec"]))
        elif id in assembly["accepted_sources"]:
            item = assembly["accepted_sources"][id]
            file = local(item["file"])
            if digest(file) != item["sha256"]:
                raise ValueError("已采纳源片SHA变化，停止合成")
            inputs.append((file, item["duration_sec"]))
        else:
            clip = next(c for c in plan["clips"] if c["id"] == id)
            inputs.append((local(clip["final_video"]), clip["duration_sec"]))
    args = ["ffmpeg", "-v", "error", "-y"]
    for file, _ in inputs:
        args += ["-i", str(file)]
    filters = []
    for i, (_, duration) in enumerate(inputs):
        filters.append(f"[{i}:v]trim=duration={duration},setpts=PTS-STARTPTS[v{i}]")
        filters.append(f"[{i}:a]aresample=48000,atrim=duration={duration},asetpts=PTS-STARTPTS[a{i}]")
    filters.append("".join(f"[v{i}][a{i}]" for i in range(len(inputs))) +
                   f"concat=n={len(inputs)}:v=1:a=1[v][a]")
    out = local(assembly["file"])
    args += ["-filter_complex", ";".join(filters), "-map", "[v]", "-map", "[a]",
             "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
             "-movflags", "+faststart", str(out)]
    run(args)
    run(["ffmpeg", "-v", "error", "-i", str(out), "-f", "null", "-"])
    assembly["result"] = probe(out)
    assembly["expected_duration_sec"] = sum(d for _, d in inputs)
    assembly["title_card"]["line"] = title["line"]
    write_subtitles(plan)
    save(path, plan)
    print(json.dumps({"assembly": assembly["result"]}, ensure_ascii=False))


def execute(args):
    path = local(args.plan)
    plan = json.loads(path.read_text())
    if args.action == "assemble":
        assemble(plan, path)
        return
    clip = next(c for c in plan["clips"] if c["id"] == args.clip)
    if args.action == "prepare":
        audio = dialogue(clip)
        save(path, plan)
        print(json.dumps({"clip": clip["id"], "dialogue": audio.name,
                          "lines": len(clip["lines"])}, ensure_ascii=False))
    else:
        {"submit": submit, "status": status, "render": render}[args.action](plan, clip, path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--clip")
    parser.add_argument("--action", choices=("prepare", "submit", "status", "render", "assemble"), required=True)
    args = parser.parse_args()
    if args.action != "assemble" and not args.clip:
        parser.error("单段操作必须指定--clip")
    # 跨进程串行修改同一配方，避免并行下载/提交丢失 task_id。
    import fcntl
    TMP.mkdir(exist_ok=True)
    lock_name = hashlib.sha256(str(local(args.plan)).encode()).hexdigest()[:12] + ".lock"
    with (TMP / lock_name).open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        execute(args)


if __name__ == "__main__":
    main()
