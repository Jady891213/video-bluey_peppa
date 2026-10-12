#!/usr/bin/env python3
"""核验独立静态站部署摘要、迁移文件体积与公开文本。"""

import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIMIT = 95 * 1024 * 1024
LOCAL_MANIFEST = ROOT / "sha256-manifest.json"
# 拆开字面量，避免检查器自己的规则成为私有路径或凭证样本。
PRIVATE_PATH = re.compile(r"/(?:Us" + r"ers|ho" + r"me)/[^\s/]+/|/var/fol" + r"ders/")
CREDENTIAL = re.compile(
    r"(?:s" + r"k-(?:proj-|svcacct-)?[A-Za-z0-9_-]{20,}"
    r"|gh" + r"[pousr]_[A-Za-z0-9]{30,}"
    r"|github_" + r"pat_[A-Za-z0-9_]{40,}"
    r"|AK" + r"IA[A-Z0-9]{16}"
    r"|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
    r"|[Bb]earer\s+[A-Za-z0-9._-]{30,})"
)


def sha256(path):
    with path.open("rb") as stream:
        digest = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
        return digest.hexdigest()


def inventory(directory, excluded=()):
    files = {}
    errors = []
    for path in sorted(directory.rglob("*")):
        relative = path.relative_to(directory)
        if ".git" in relative.parts or path in excluded:
            continue
        if any("TMP to delete" in part for part in relative.parts):
            errors.append(f"残留临时产物：{relative.as_posix()}")
            continue
        if path.is_symlink():
            errors.append(f"不接受符号链接：{relative.as_posix()}")
            continue
        if path.is_file():
            files[relative.as_posix()] = {
                "sha256": sha256(path), "bytes": path.stat().st_size
            }
    return files, errors


def declared_files(value):
    if isinstance(value, dict):
        return {
            name: item if isinstance(item, dict) else {"sha256": item}
            for name, item in value.items()
        }
    if isinstance(value, list):
        result = {item["path"]: item for item in value}
        if len(result) != len(value):
            raise ValueError("静态摘要含重复路径")
        return result
    raise ValueError("static_manifest.files 必须为路径字典或条目列表")


def check_sites(deployment):
    errors = []
    summaries = []
    data = json.loads(deployment.read_text(encoding="utf-8"))
    sites = data.get("sites")
    if not isinstance(sites, list) or not sites:
        raise ValueError("部署清单必须包含非空 sites 数组")
    for site in sites:
        manifest = site["static_manifest"]
        if not isinstance(manifest, dict):
            raise ValueError("static_manifest 必须为字典")
        root_name = manifest["root"]
        directory = (ROOT / root_name).resolve()
        if not directory.is_relative_to(ROOT) or not directory.is_dir():
            raise ValueError(f"静态目录不存在或越界：{root_name}")
        actual, file_errors = inventory(directory)
        errors.extend(f"{root_name}: {message}" for message in file_errors)
        expected = declared_files(manifest["files"])
        for name in sorted(expected.keys() - actual.keys()):
            errors.append(f"{root_name}: 缺少 {name}")
        for name in sorted(actual.keys() - expected.keys()):
            errors.append(f"{root_name}: 未登记 {name}")
        for name in sorted(expected.keys() & actual.keys()):
            item = expected[name]
            if item.get("sha256") != actual[name]["sha256"]:
                errors.append(f"{root_name}: SHA 不一致 {name}")
            if "bytes" in item and item["bytes"] != actual[name]["bytes"]:
                errors.append(f"{root_name}: 大小不一致 {name}")
        byte_count = sum(item["bytes"] for item in actual.values())
        if manifest["count"] != len(actual) or manifest["count"] != len(expected):
            errors.append(f"{root_name}: count 不一致")
        if manifest["bytes"] != byte_count:
            errors.append(f"{root_name}: bytes 不一致")
        summaries.append({"root": root_name, "count": len(actual), "bytes": byte_count})
    return summaries, errors


def check_animation_assets():
    """目录调整后，核对采用状态、清单媒体与原始输入引用。"""
    path = ROOT / 'materials/final/gift/动画素材清单.json'
    if not path.exists():
        return None, ['缺少动画素材清单']
    data = json.loads(path.read_text())
    errors = []
    accepted = data['accepted']
    if {x['id'] for x in accepted} != {'A', 'B'}:
        errors.append('已采纳动画必须仅为用户确认的A/B')
    actual_accepted = {
        p.relative_to(ROOT).as_posix()
        for p in (ROOT / 'materials/final/gift/已采纳成片').glob('*.mp4')
    }
    if actual_accepted != {x['file'] for x in accepted}:
        errors.append('已采纳目录与采用清单不一致')
    for item in accepted + data['backup']:
        p = ROOT / item['file']
        if not p.is_file() or sha256(p) != item['sha256']:
            errors.append(f'动画文件缺少或SHA不符：{item["file"]}')

    def walk(value, source):
        if isinstance(value, dict):
            for child in value.values():
                walk(child, source)
        elif isinstance(value, list):
            for child in value:
                walk(child, source)
        elif isinstance(value, str) and value.startswith('materials/'):
            p = (ROOT / value).resolve()
            if not p.is_relative_to(ROOT) or not p.exists():
                errors.append(f'{source}: 无效素材引用 {value}')

    for p in (ROOT / 'materials').rglob('*.json'):
        walk(json.loads(p.read_text()), p.relative_to(ROOT).as_posix())
    voices = json.loads((ROOT / 'materials/final/gift/voice-manifest.json').read_text())['lines']
    for line in voices:
        p = ROOT / line['wav_file']
        if not p.is_file() or sha256(p) != line['wav_sha256']:
            errors.append(f'原配音SHA不符：{line["line_id"]}')
    return {'accepted': len(accepted), 'backup': len(data['backup']),
            'full_voice_lines': len(voices)}, errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="另生成本地 sha256-manifest.json，不修改部署信息")
    args = parser.parse_args()
    files, errors = inventory(ROOT, excluded=(LOCAL_MANIFEST,))
    for name, item in files.items():
        if item["bytes"] > LIMIT:
            errors.append(f"文件超过 95 MiB：{name}")
        if item["bytes"] > 4 * 1024 * 1024:
            continue
        try:
            text = (ROOT / name).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if "\x00" in text:
            continue
        if PRIVATE_PATH.search(text):
            errors.append(f"文本含私有绝对路径：{name}")
        if CREDENTIAL.search(text):
            errors.append(f"文本疑似含凭证：{name}")
    summaries = []
    animation = None
    try:
        summaries, site_errors = check_sites(ROOT / "deployment-manifest.json")
        errors.extend(site_errors)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(f"部署清单无法核验：{exc}")
    try:
        animation, asset_errors = check_animation_assets()
        errors.extend(asset_errors)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(f'动画素材无法核验：{exc}')
    if args.write:
        LOCAL_MANIFEST.write_text(json.dumps({
            "algorithm": "sha256", "count": len(files),
            "bytes": sum(item["bytes"] for item in files.values()), "files": files,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": not errors, "files": len(files), "sites": summaries, "animation": animation,
                      "local_manifest_written": args.write, "errors": errors},
                     ensure_ascii=False, indent=2))
    raise SystemExit(1 if errors else 0)


if __name__ == "__main__":
    main()
