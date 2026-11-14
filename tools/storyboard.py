# -*- coding: utf-8 -*-
"""分镜蓝图（storyboard）标准与校验
分镜是唯一蓝图：段号 / 配音区间 / 制作方式 / 素材引用，下游全部消费它。

分镜 JSON 结构（第NN课_分镜.json）：
{
  "lesson": "01",
  "title": "第01课《入门》",
  "total_hint": 572.2,
  "segments": [
    {
      "no": 1,
      "narration_range": [1, 1],        // 对应的配音段号区间（闭区间）
      "mode": "animation|recording|card",  // 制作方式（硬枚举）
      "content": "开场：自我介绍 + 课程范围",
      "a_roll": "opener 动画：标题扫光 + 讲师胶囊",
      "b_roll": "光粒子轨迹（氛围层）",
      "assets": ["opener/opener.mp4"],
      "hold_tail": "loop|still|none",   // 动画不足时长时如何延展
      "note": "可选说明"
    }
  ]
}

用法：
    python tools/storyboard.py --lesson 01 --check     # 校验现有分镜
    python tools/storyboard.py --lesson 01 --dump      # 打印分镜表
"""
import argparse
import glob
import json
import os
import sys

ROOT = r"E:/WorkBuddy课程/01_基础课"
MODES = {"animation", "recording", "card"}
HOLD = {"loop", "still", "none"}


def find(lesson):
    d = glob.glob(os.path.join(ROOT, f"第{lesson}课_*"))
    if not d:
        return None, None
    return d[0], os.path.join(d[0], "01_逐字稿与脚本", f"第{lesson}课_分镜.json")


def check(lesson, json_path):
    errs, warns = [], []
    if not os.path.isfile(json_path):
        return [f"分镜 JSON 不存在：{json_path}"], []
    try:
        d = json.load(open(json_path, encoding="utf-8"))
    except Exception as e:
        return [f"分镜 JSON 解析失败：{e}"], []

    segs = d.get("segments", [])
    if not segs:
        return ["segments 为空"], []

    # 配音段数（用于校验区间覆盖）
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from gen_tts import split_text
    tts = os.path.join(os.path.dirname(json_path), f"第{lesson}课_TTS朗读稿.txt")
    n_voice = len(split_text(open(tts, encoding="utf-8").read().strip())) if os.path.isfile(tts) else 0

    covered = []
    prev_end = 0
    for s in segs:
        no = s.get("no")
        if not isinstance(no, int):
            errs.append(f"段 {no}: no 必须是整数")
        rg = s.get("narration_range")
        if not (isinstance(rg, list) and len(rg) == 2 and all(isinstance(x, int) for x in rg)):
            errs.append(f"段 {no}: narration_range 必须是 [起,止] 两个整数")
            continue
        a, b = rg
        if a > b:
            errs.append(f"段 {no}: narration_range 起({a}) > 止({b})")
        if a != prev_end + 1:
            (errs if a > prev_end + 1 else warns).append(
                f"段 {no}: 配音段不连续（上一段止于 {prev_end}，本段从 {a} 开始）")
        covered.extend(range(a, b + 1))
        prev_end = b

        mode = s.get("mode")
        if mode not in MODES:
            errs.append(f"段 {no}: mode={mode!r} 不在 {sorted(MODES)} 内")
        hold = s.get("hold_tail", "loop")
        if hold not in HOLD:
            errs.append(f"段 {no}: hold_tail={hold!r} 不在 {sorted(HOLD)} 内")
        # 概念段（animation）不允许 still 占位
        if mode == "animation" and hold == "still":
            errs.append(f"段 {no}: 动画段禁止 hold_tail=still（会定格，违反 D4）")
        # 录屏段必须有指引
        if mode == "recording" and not s.get("a_roll"):
            warns.append(f"段 {no}: 录屏段缺 a_roll 录制指引")

    if n_voice:
        miss = [i for i in range(1, n_voice + 1) if i not in covered]
        dup = [i for i in set(covered) if covered.count(i) > 1]
        if miss:
            errs.append(f"配音段 {miss} 未被任何分镜段覆盖")
        if dup:
            errs.append(f"配音段 {sorted(set(dup))} 被多个分镜段重复覆盖")
    return errs, warns


def dump(json_path):
    d = json.load(open(json_path, encoding="utf-8"))
    print(f"# {d.get('title')}  总时长参考 {d.get('total_hint')}s\n")
    print(f"{'段':>3} {'配音区间':>10} {'制作方式':>10} {'延展':>6}  内容")
    for s in d["segments"]:
        rg = s.get("narration_range", [0, 0])
        print(f"{s['no']:>3} {str(rg[0])+'-'+str(rg[1]):>10} {s['mode']:>10} "
              f"{s.get('hold_tail','loop'):>6}  {s.get('content','')[:42]}")
    from collections import Counter
    c = Counter(s["mode"] for s in d["segments"])
    print(f"\n统计：animation {c['animation']} / recording {c['recording']} / card {c['card']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lesson", default="01")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--dump", action="store_true")
    a = ap.parse_args()
    dir_, jp = find(a.lesson)
    if not dir_:
        print("找不到课程目录"); return 2
    if a.dump and os.path.isfile(jp):
        dump(jp); return 0
    errs, warns = check(a.lesson, jp)
    if errs:
        print(f"❌ 分镜校验失败：{len(errs)} 项错误")
        for e in errs:
            print("  🔴", e)
    else:
        print("✅ 分镜校验通过")
    for w in warns:
        print("  🟡", w)
    return 0 if not errs else 1


if __name__ == "__main__":
    sys.exit(main())