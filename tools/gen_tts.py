# -*- coding: utf-8 -*-
"""
课程制片团 · 批量配音（MiniMax speech-2.8-hd，克隆音色）

读 7 门课的 TTS 朗读稿，按 ≤400 字/句界切段，并行合成 mp3：
  - 每课输出目录  02_配音/
  - 分段文件      第NN课_段XX.mp3（保留分段，方便剪映按段对轨）
  - 完整拼接      第NN课_完整配音.mp3（ffmpeg concat）

参数沿用第一课已验证配置：voice-ca8478b9d5fd / speed 1.15 / vol 4.0 / pitch 0
失败段自动重试 1 次；全部失败则退出码 1。

用法：
    python tools/gen_tts.py --lesson 01          # 只配第01课
    python tools/gen_tts.py                      # 全部 7 课
    python tools/gen_tts.py --dry                # 只报告分段数
"""
import glob
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

ROOT = r"E:/WorkBuddy课程/01_基础课"
ENDPOINT = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
MODEL = "MiniMax/speech-2.8-hd"
VOICE_ID = "voice-ca8478b9d5fd"
SPEED, VOL, PITCH = 1.15, 4.0, 0
FFMPEG = ("D:/workbudyy/spaces/2026_11_13_20-02-16/remotion/node_modules/"
          "@remotion/compositor-win32-x64-msvc/ffmpeg.exe")

with open(os.path.expanduser("~/.bailian/config.json"), encoding="utf-8") as f:
    API_KEY = json.load(f)["api_key"]


def split_text(text, max_chars=400):
    """按句界切分，每段 ≤ max_chars，段落收口。"""
    chunks, cur = [], ""
    for para in [p.strip() for p in text.split("\n\n") if p.strip()]:
        for s in re.split(r"(?<=[。！？!?])", para):
            s = s.strip()
            if not s:
                continue
            if len(cur) + len(s) <= max_chars:
                cur += s
            else:
                if cur:
                    chunks.append(cur)
                cur = s
    if cur:
        chunks.append(cur)
    return chunks


def synthesize(text):
    payload = {
        "model": MODEL,
        "input": {
            "text": text,
            "voice_setting": {"voice_id": VOICE_ID, "speed": SPEED,
                              "vol": VOL, "pitch": PITCH},
            "audio_setting": {"sample_rate": 32000, "format": "mp3", "channel": 1},
        },
    }
    headers = {"Authorization": "Bearer " + API_KEY, "Content-Type": "application/json"}
    r = requests.post(ENDPOINT, headers=headers, json=payload, timeout=180)
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
    data = r.json()
    base = data.get("output", {}).get("base_resp", {})
    if base.get("status_code") != 0:
        raise RuntimeError(f"合成失败: {base.get('status_msg', base)}")
    audio_hex = data.get("output", {}).get("data", {}).get("audio")
    if not audio_hex:
        raise RuntimeError("接口未返回音频")
    return bytes.fromhex(audio_hex)


def probe_seconds(path):
    if not os.path.exists(FFMPEG):
        return None
    try:
        out = subprocess.run(
            [FFMPEG, "-i", path], capture_output=True, text=True,
            timeout=30).stderr
        m = re.search(r"Duration: (\d+):(\d+):(\d+)\.(\d+)", out)
        if m:
            h, mi, s, cs = map(int, m.groups())
            return h * 3600 + mi * 60 + s + cs / 100
    except Exception:
        pass
    return None


def do_lesson(n, dry=False, workers=3):
    ds = glob.glob(os.path.join(ROOT, f"第{n}课_*", "01_逐字稿与脚本", f"第{n}课_TTS朗读稿.txt"))
    if not ds:
        print(f"[跳过] 第{n}课 TTS 稿不存在")
        return 0
    text = open(ds[0], encoding="utf-8").read().strip()
    chunks = split_text(text)
    outdir = os.path.join(os.path.dirname(os.path.dirname(ds[0])), "02_配音")
    print(f"第{n}课：{len(chunks)} 段（约 {sum(len(c) for c in chunks)} 字）→ {outdir}")
    if dry:
        return len(chunks)
    os.makedirs(outdir, exist_ok=True)

    segs = [None] * len(chunks)
    pending = []          # 只合成缺失段（幂等）
    for i in range(len(chunks)):
        p = os.path.join(outdir, f"第{n}课_段{i+1:02d}.mp3")
        if os.path.exists(p) and os.path.getsize(p) > 0:
            segs[i] = p
        else:
            pending.append(i)
    if pending:
        print(f"  已存在 {len(chunks)-len(pending)} 段，待合成 {len(pending)} 段")
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(synthesize, chunks[i]): i for i in pending}
        for fut in as_completed(futs):
            i = futs[fut]
            try:
                audio = fut.result()
            except Exception as e:
                time.sleep(5 if "429" in str(e) else 3)   # 限流退避后重试 1 次
                try:
                    audio = synthesize(chunks[i])
                except Exception as e2:
                    print(f"  [段 {i+1}] 失败: {e2}")
                    continue
            p = os.path.join(outdir, f"第{n}课_段{i+1:02d}.mp3")
            with open(p, "wb") as f:
                f.write(audio)
            segs[i] = p

    ok = [p for p in segs if p]
    print(f"  完成 {len(ok)}/{len(chunks)} 段")
    if not ok:
        print(f"[失败] 第{n}课全部失败")
        return 0

    lst = os.path.join(outdir, "_concat.txt")
    with open(lst, "w", encoding="utf-8") as f:
        for p in ok:
            f.write("file '{}'\n".format(os.path.abspath(p).replace("\\", "/")))
    full = os.path.join(outdir, f"第{n}课_完整配音.mp3")
    if os.path.exists(FFMPEG):
        subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0",
                        "-i", lst, "-c", "copy", full], check=True)
    else:
        with open(full, "wb") as f:
            for p in ok:
                f.write(open(p, "rb").read())
    os.remove(lst)
    dur = probe_seconds(full)
    print(f"  拼接完成 → {full}" + (f"（{dur/60:.1f} 分钟）" if dur else ""))
    return len(ok)


def main():
    args = sys.argv[1:]
    dry = "--dry" in args
    workers = 3
    only = None
    i = 0
    while i < len(args):
        a = args[i]
        if a.startswith("--workers="):
            workers = int(a.split("=")[1])
        elif a == "--workers" and i + 1 < len(args):
            workers = int(args[i + 1]); i += 1
        elif a.startswith("--lesson="):
            only = a.split("=")[1]
        elif a == "--lesson" and i + 1 < len(args):
            only = args[i + 1]; i += 1
        i += 1
    lessons = [only] if only else ["01", "02", "03", "04", "05", "06", "07"]
    done = 0
    for n in lessons:
        done += do_lesson(n, dry=dry, workers=workers) or 0
    print(f"\n合计 {done} 段" + ("（试运行）" if dry else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
