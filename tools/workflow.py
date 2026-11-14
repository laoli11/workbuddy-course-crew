# -*- coding: utf-8 -*-
"""工作流状态与门禁（G0–G6）
新会话开工第一件事：python tools/workflow.py status --lesson 01

用法:
    python tools/workflow.py status [--lesson 01]
    python tools/workflow.py gate G3 --lesson 01
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = r"E:/WorkBuddy课程/01_基础课"
REG = os.path.join(REPO, "registry.json")
PY = sys.executable


def reg():
    return json.load(open(REG, encoding="utf-8"))


def lesson_dir(n):
    d = glob.glob(os.path.join(ROOT, f"第{n}课_*"))
    return d[0] if d else None


def sh(args, cwd=REPO):
    r = subprocess.run([PY] + args, capture_output=True, text=True, cwd=cwd)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def gate_g0(n, ld, meta):
    errs = []
    if not meta:
        return 1, ["registry 无本课条目"]
    if not meta.get("facts_confirmed"):
        errs.append("facts 未确认（讲师名/头衔/渠道需用户确认）")
    if not meta.get("authority_script") and not os.path.isfile(os.path.join(ld, "01_逐字稿与脚本", f"第{n}课_口播稿.md")):
        errs.append("无口播稿")
    return (0 if not errs else 1), errs or ["OK"]


def gate_g1(n, ld, meta):
    code, out = sh(["tools/validate_delivery.py"])
    errs = [] if code == 0 else [l for l in out.splitlines() if l.strip().startswith("-")][:5] or ["校验未通过"]
    return code, errs or ["机器闸全绿"]


def gate_g2(n, ld, meta):
    code, out = sh(["tools/storyboard.py", "--lesson", n])
    return code, [l.strip() for l in out.splitlines() if l.strip()][:6]


def gate_g3(n, ld, meta):
    errs = []
    tts = os.path.join(ld, "01_逐字稿与脚本", f"第{n}课_TTS朗读稿.txt")
    sb = os.path.join(ld, "01_逐字稿与脚本", f"第{n}课_分镜.json")
    vdir = os.path.join(ld, "02_配音")
    aj = os.path.join(ld, f"第{n}课_字幕_对齐.json")

    if not os.path.isfile(aj):
        errs.append("缺 VAD 对齐文件（第NN课_字幕_对齐.json）")
    # 配音段数 vs 分镜段数
    if os.path.isfile(tts) and os.path.isfile(sb):
        sys.path.insert(0, os.path.join(REPO, "tools"))
        from gen_tts import split_text
        nv = len(split_text(open(tts, encoding="utf-8").read().strip()))
        ns = len(json.load(open(sb, encoding="utf-8"))["segments"])
        if nv != ns:
            errs.append(f"配音段数 {nv} ≠ 分镜段数 {ns}")
        nf = len(glob.glob(os.path.join(vdir, f"第{n}课_段*.mp3")))
        if nf < nv:
            errs.append(f"配音文件 {nf} 个 < 段数 {nv}")
    # 字幕拆行：单条 ≤20 字
    srt = os.path.join(ld, f"第{n}课_字幕_对齐.srt")
    if os.path.isfile(srt):
        blocks = [b for b in open(srt, encoding="utf-8").read().strip().split("\n\n") if b.strip()]
        longn = 0
        for b in blocks:
            ls = b.split("\n")
            if len(ls) >= 3 and len("".join(ls[2:])) > 20:
                longn += 1
        if longn:
            errs.append(f"{longn}/{len(blocks)} 条字幕超 20 字（需拆行）")
    return (0 if not errs else 1), errs or ["配音段数一致、对齐文件齐全、字幕均 ≤20 字"]


def gate_g4(n, ld, meta):
    errs = []
    sb = os.path.join(ld, "01_逐字稿与脚本", f"第{n}课_分镜.json")
    if not os.path.isfile(sb):
        return 1, ["缺分镜 JSON"]
    d = json.load(open(sb, encoding="utf-8"))
    rec = [s["no"] for s in d["segments"] if s["mode"] == "recording"]
    if rec:
        hand = glob.glob(os.path.join(ld, "*待录屏*"))
        if not hand:
            errs.append(f"有 {len(rec)} 个录屏段但缺「待录屏清单」文件")
    return (0 if not errs else 1), errs or [f"分镜 {len(d['segments'])} 段合法"]


def gate_g5(n, ld, meta):
    errs = []
    spec = os.path.join(meta.get("_spec_dir", ""), "spec_storyboard.json")
    if not os.path.isfile(spec):
        cands = glob.glob(r"D:/workbudyy/spaces/2026_11_13_20-02-16/lesson01_final/spec_*.json")
        spec = cands[0] if cands else ""
    if not spec or not os.path.isfile(spec):
        return 1, ["未找到 spec（草稿未生成）"]
    d = json.load(open(spec, encoding="utf-8"))
    miss = [x["src"] for x in d.get("video", []) + d.get("audio", []) if not os.path.isfile(x["src"])]
    if miss:
        errs.append(f"{len(miss)} 个素材坏链")
    if not any(a.get("track") == "BGM" for a in d.get("audio", [])):
        errs.append("缺 BGM 音轨")
    tot = sum(float(v["dur"].rstrip("s")) for v in d.get("video", []))
    aud = max((float(a["dur"].rstrip("s")) for a in d.get("audio", [])), default=0)
    if abs(tot - aud) > 0.2:
        errs.append(f"视频轨 {tot:.1f}s 与音频 {aud:.1f}s 差 {abs(tot-aud):.1f}s (>0.2)")
    return (0 if not errs else 1), errs or [f"总长 {tot:.1f}s 对齐、素材齐全、双音轨"]


def gate_g6(n, ld, meta):
    spec = glob.glob(r"D:/workbudyy/spaces/2026_11_13_20-02-16/lesson01_final/spec_*.json")
    if not spec:
        return 1, ["未找到 spec"]
    code, out = sh(["tools/review_gate.py", "--lesson", n, "--spec", spec[0]])
    lines = [l.strip() for l in out.splitlines() if "🔴" in l][:6]
    return code, lines or ["审片全绿"]


GATES = {"G0": gate_g0, "G1": gate_g1, "G2": gate_g2, "G3": gate_g3,
         "G4": gate_g4, "G5": gate_g5, "G6": gate_g6}


def cmd_status(lesson):
    r = reg()
    print(f"工作流状态（registry 更新于 {r.get('updated')}）\n")
    for n, m in r["lessons"].items():
        if lesson and n != lesson:
            continue
        flag = "  " if n != lesson else "▶ "
        print(f"{flag}第{n}课 {m.get('title','')}  [{m.get('stage')}] {m.get('stage_name','')}")
        if m.get("blocking"):
            for b in m["blocking"]:
                print(f"      🔴 {b['gate']}: {b['issue']}")
        if m.get("pending_record"):
            print(f"      🎬 待录屏段：{m['pending_record']}")
    if lesson:
        stage = r["lessons"].get(lesson, {}).get("stage", "P1")
        g = stage.replace("P", "G", 1)   # P3 → G3（阶段与门禁同号）
        print(f"\n下一步：python tools/workflow.py gate {g} --lesson {lesson}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["status", "gate"])
    ap.add_argument("gate_name", nargs="?")
    ap.add_argument("--lesson", default="01")
    a = ap.parse_args()
    n = a.lesson
    if a.cmd == "status":
        cmd_status(n if n != "all" else None)
        return 0
    g = (a.gate_name or "").upper()
    if g not in GATES:
        print(f"未知门禁 {g}，可用：{list(GATES)}")
        return 2
    ld = lesson_dir(n)
    meta = reg()["lessons"].get(n)
    if not ld:
        print(f"找不到第{n}课目录"); return 2
    code, msgs = GATES[g](n, ld, meta)
    print(f"{'✅' if code == 0 else '❌'} {g} 第{n}课 " + ("PASS" if code == 0 else "FAIL"))
    for m in msgs:
        print("   " + m)
    return code


if __name__ == "__main__":
    sys.exit(main())