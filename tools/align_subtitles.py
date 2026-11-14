# -*- coding: utf-8 -*-
"""字幕-动画对齐（VAD 实测版）
用音频能量检测真实语音段边界，替代"按字数估算"，输出逐句真实起止时间。
用法: python tools/align_subtitles.py --lesson 01 [--dry]
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_tts import FFMPEG, probe_seconds, split_text  # noqa

ROOT = r"E:/WorkBuddy课程/01_基础课"
SR = 16000
HOP = 0.010   # 10ms 帧
SIL_MIN = 0.12  # 最短静音 120ms 视为句界


def decode(path):
    """经 ffmpeg 转 16k 单声道 wav，用标准库 wave 读取（本机 ffmpeg 无 s16le 管道）。"""
    import tempfile, wave
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
    try:
        subprocess.run([FFMPEG, "-v", "error", "-y", "-i", path,
                        "-ar", str(SR), "-ac", "1", tmp],
                       capture_output=True, timeout=300)
        with wave.open(tmp, "rb") as w:
            raw = w.readframes(w.getnframes())
        return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def vad(audio, thresh_ratio=0.06, floor=0.004):
    """返回语音区间 [(start,end), ...]（秒）"""
    n = int(HOP * SR)
    nf = len(audio) // n
    if nf == 0:
        return []
    rms = np.array([np.sqrt(np.mean(audio[i * n:(i + 1) * n] ** 2)) for i in range(nf)])
    thr = max(np.percentile(rms, 20) * 1.8, rms.max() * thresh_ratio, floor)
    voiced = rms > thr
    # 平滑：去掉 <3 帧的孤立点
    for i in range(1, len(voiced) - 1):
        if voiced[i] and not voiced[i - 1] and not voiced[i + 1]:
            voiced[i] = False
        elif not voiced[i] and voiced[i - 1] and voiced[i + 1]:
            voiced[i] = True
    spans, start = [], None
    for i, v in enumerate(voiced):
        if v and start is None:
            start = i
        elif not v and start is not None:
            spans.append((start * HOP, i * HOP))
            start = None
    if start is not None:
        spans.append((start * HOP, len(voiced) * HOP))
    # 合并间隔 < SIL_MIN 的相邻段
    merged = []
    for s in spans:
        if merged and s[0] - merged[-1][1] < SIL_MIN:
            merged[-1] = (merged[-1][0], s[1])
        else:
            merged.append(list(s))
            merged[-1] = tuple(merged[-1])
    return [(round(a, 3), round(b, 3)) for a, b in merged if b - a > 0.08]


def align_sentences(sents, spans, total):
    """把句界映射到语音段：句数≤段数则合并过短段，句数>段数则按比例在段内切分。"""
    if not spans:
        # 无有效 VAD：退化为按字数比例
        tot = sum(len(s) for s in sents) or 1
        out, t = [], 0.0
        for s in sents:
            d = total * len(s) / tot
            out.append((round(t, 3), round(t + d, 3)))
            t += d
        return out
    # 句子数与语音段数不一致时，按累计比例映射
    sent_w = np.array([max(len(s), 1) for s in sents], dtype=float)
    sent_edges = np.concatenate([[0], np.cumsum(sent_w) / sent_w.sum()]) * total
    span_w = np.array([b - a for a, b in spans], dtype=float)
    span_edges = np.concatenate([[0], np.cumsum(span_w) / span_w.sum()]) * total

    def map_time(t):
        i = np.searchsorted(span_edges, t, side="right") - 1
        i = min(max(i, 0), len(spans) - 1)
        a, b = spans[i]
        e0, e1 = span_edges[i], span_edges[i + 1]
        if e1 <= e0:
            return a
        return a + (t - e0) / (e1 - e0) * (b - a)

    out = []
    for i in range(len(sents)):
        s = map_time(sent_edges[i])
        e = map_time(sent_edges[i + 1])
        if e <= s:
            e = min(total, s + 0.5)
        out.append((round(s, 3), round(e, 3)))
    return out


def build_srt(items, path):
    def fmt(x):
        ms = int(round(x * 1000)); h, ms = divmod(ms, 3600000)
        m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
    with open(path, "w", encoding="utf-8") as f:
        for i, (st, en, txt, _seg) in enumerate(items, 1):
            f.write(f"{i}\n{fmt(st)} --> {fmt(en)}\n{txt}\n\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lesson", default="01")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    n = a.lesson

    ds = glob.glob(os.path.join(ROOT, f"第{n}课_*", "01_逐字稿与脚本", f"第{n}课_TTS朗读稿.txt"))
    vd = glob.glob(os.path.join(ROOT, f"第{n}课_*", "02_配音"))
    outd = glob.glob(os.path.join(ROOT, f"第{n}课_*"))[0]
    assert ds and vd, "找不到 TTS 稿或配音目录"
    tts_path, vdir = ds[0], vd[0]

    chunks = split_text(open(tts_path, encoding="utf-8").read().strip())
    items, seg_meta, t0 = [], [], 0.0
    est_items = []   # 旧估算方法，用于量化偏差
    est_t = 0.0

    print(f"第{n}课：{len(chunks)} 个配音段")
    print(f"{'段':>3} {'配音段时长':>9} {'VAD语音段':>8} {'句子':>5} {'最大偏差':>9} {'平均偏差':>9}")
    for i, c in enumerate(chunks):
        mp3 = os.path.join(vdir, f"第{n}课_段{i+1:02d}.mp3")
        dur = probe_seconds(mp3)
        audio = decode(mp3)
        spans = vad(audio)
        sents = [s.strip() for s in re.split(r"(?<=[。！？])", c) if s.strip()]
        real = align_sentences(sents, spans, dur)
        # 旧方法（按字数比例，全句同起）
        tot = sum(len(s) for s in sents) or 1
        est, ct = [], 0.0
        for s in sents:
            d = dur * len(s) / tot
            est.append((ct, ct + d))
            ct += d
        diffs = [abs(r[0] - e[0]) for r, e in zip(real, est)]
        print(f"{i+1:>3} {dur:>8.1f}s {len(spans):>8} {len(sents):>5} {max(diffs):>8.2f}s {np.mean(diffs):>8.2f}s")

        for (s, e), txt in zip(real, sents):
            items.append((t0 + s, t0 + e, txt, i + 1))
        for (s, e), txt in zip(est, sents):
            est_items.append((est_t + s, est_t + e, txt, i + 1))
        seg_meta.append({"seg": i + 1, "dur": round(dur, 3), "vad_spans": len(spans),
                         "sentences": len(sents), "max_drift": round(max(diffs), 3),
                         "mean_drift": round(float(np.mean(diffs)), 3),
                         "first_voice": round(spans[0][0], 3) if spans else None})
        t0 += dur
        est_t += dur

    srt = os.path.join(outd, f"第{n}课_字幕_对齐.srt")
    if not a.dry:
        build_srt(items, srt)
    total = sum(m["dur"] for m in seg_meta)
    all_drift = [m["max_drift"] for m in seg_meta]
    print(f"\n总时长 {total:.1f}s / {len(items)} 条字幕")
    print(f"全局最大偏差 {max(all_drift):.2f}s / 平均 {np.mean([m['mean_drift'] for m in seg_meta]):.2f}s")
    print(f"字幕 → {srt}" + ("（试运行未写）" if a.dry else ""))

    meta = {"lesson": n, "total": round(total, 3), "segments": seg_meta,
            "sentences": [{"start": round(s, 3), "end": round(e, 3), "text": x, "seg": g}
                          for s, e, x, g in items]}
    mp = os.path.join(outd, f"第{n}课_字幕_对齐.json")
    if not a.dry:
        json.dump(meta, open(mp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"时间戳 → {mp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())