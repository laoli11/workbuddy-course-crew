# -*- coding: utf-8 -*-
"""
课程制片团 · B roll 素材生成器

用代码批量生成透明底 SVG 图卡/示意/角标，风格与第02课手工 broll 一致：
深色科技风、发光描边、渐变箭头、粒子点缀。

设计硬约束（针对「文字溢出/排版水平低」的历史问题）：
1. 所有文字按中英混排估算实际宽度，自动降字号直到装进容器；
2. 生成后跑 validate()，用 XML 解析逐条检查文字边界不越出 720x300 画布；
3. 关键内容主体最高点 y<=244，底部提示 y=278，给字幕条留出安全区；
4. 不使用 emoji / 特殊符号字体，纯几何图形 + 文本，避免方框字。

用法：
    python tools/gen_broll.py            # 生成全部
    python tools/gen_broll.py --check   # 只校验已有 SVG
"""
import math
import os
import re
import sys
import glob
import xml.etree.ElementTree as ET

W, H = 720, 300
OUT_ROOT = r"E:/WorkBuddy课程/01_基础课"

COLORS = {
    "blue":   "#60a5fa",
    "cyan":   "#22d3ee",
    "purple": "#a78bfa",
    "green":  "#4ade80",
    "red":    "#f87171",
    "amber":  "#fbbf24",
    "slate":  "#94a3b8",
}
LIGHT = "#e2e8f0"
DIM = "#8ea3bf"
FONT = "Microsoft YaHei, PingFang SC, sans-serif"


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def char_w(ch, fs):
    o = ord(ch)
    if o > 0x2E80:            # CJK / 全角
        return fs * 1.0
    if ch in " .,:;'|":
        return fs * 0.30
    if ch in "ilI1":
        return fs * 0.32
    return fs * 0.58


def text_w(s, fs):
    return sum(char_w(c, fs) for c in str(s))


def fit_font(s, maxw, base=28, minfs=13):
    fs = base
    while fs > minfs and text_w(s, fs) > maxw:
        fs -= 1
    return fs


class Canvas:
    def __init__(self, title, note, accent, header=None):
        self.title = title
        self.note = note
        self.header = header
        self.accent = COLORS.get(accent, COLORS["blue"])
        self.parts = []
        self.texts = []   # (x, y, s, fs, anchor, maxw) 供自检

    def text(self, x, y, s, maxw, base=26, color=None, anchor="middle",
             weight="normal", minfs=13):
        s = str(s)
        fs = fit_font(s, maxw, base, minfs)
        col = color or LIGHT
        self.parts.append(
            f'<text x="{x:.1f}" y="{y:.1f}" font-size="{fs}" fill="{col}" '
            f'text-anchor="{anchor}" font-family="{FONT}" font-weight="{weight}">{esc(s)}</text>')
        self.texts.append((x, y, s, fs, anchor, maxw))
        return fs

    def rect(self, x, y, w, h, rx=18, stroke=None, fill="#0b1220",
             opacity=0.62, sw=2, glow=False, dash=None):
        st = stroke or self.accent
        d = f' stroke-dasharray="{dash}"' if dash else ""
        g = ' filter="url(#glow)"' if glow else ""
        self.parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'rx="{rx}" fill="{fill}" fill-opacity="{opacity}" stroke="{st}" '
            f'stroke-opacity="0.62" stroke-width="{sw}"{d}{g}/>')

    def circle(self, cx, cy, r, color, opacity=0.9, glow=False):
        g = ' filter="url(#glow)"' if glow else ""
        self.parts.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{color}" '
            f'fill-opacity="{opacity}"{g}/>')

    def arrow(self, x1, x2, y, color=None, sw=6):
        c = color or self.accent
        self.parts.append(
            f'<path d="M {x1:.1f} {y:.1f} L {x2-14:.1f} {y:.1f}" stroke="{c}" '
            f'stroke-width="{sw}" stroke-linecap="round" fill="none" '
            f'stroke-opacity="0.85" filter="url(#glow)"/>')
        self.parts.append(
            f'<polygon points="{x2:.1f},{y:.1f} {x2-16:.1f},{y-10:.1f} '
            f'{x2-16:.1f},{y+10:.1f}" fill="{c}"/>')
        for k in (0.32, 0.58, 0.82):
            self.circle(x1 + (x2 - x1) * k, y, 3.2, COLORS["amber"], 0.9, glow=True)

    def render(self):
        a = self.accent
        head = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">',
            '<defs>',
            '<linearGradient id="topline" x1="0" y1="0" x2="1" y2="0">',
            f'<stop offset="0" stop-color="{a}" stop-opacity="0"/>',
            f'<stop offset="0.5" stop-color="{a}" stop-opacity="0.9"/>',
            f'<stop offset="1" stop-color="{a}" stop-opacity="0"/>',
            '</linearGradient>',
            '<filter id="glow" x="-60%" y="-60%" width="220%" height="220%">',
            '<feGaussianBlur stdDeviation="5" result="b"/>',
            '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>',
            '</filter>',
            '</defs>',
            f'<path d="M 90 52 L 630 52" stroke="url(#topline)" stroke-width="2" fill="none"/>',
            f'<circle cx="40" cy="52" r="3" fill="{a}" fill-opacity="0.7"/>',
            f'<circle cx="680" cy="52" r="3" fill="{a}" fill-opacity="0.7"/>',
        ]
        # 标题（warning 版式用小灰标签，把视觉重心让给框内警示大字）
        if self.header:
            self.text(W / 2, 36, self.header, 620, base=18, color=DIM)
        else:
            self.text(W / 2, 36, self.title, 620, base=25, color=a, weight="bold")
        # 底部提示
        self.text(W / 2, 278, self.note, 640, base=19, color=DIM, minfs=13)
        tail = ['</svg>']
        return "\n".join(head + self.parts + tail) + "\n"


def split_item(item):
    """'主文字|副文字|副文字2' -> list"""
    return [p.strip() for p in str(item).split("|") if p.strip()]


def build(spec):
    name, kind, title, items, note, accent = spec
    c = Canvas(title, note, accent,
               header="避坑 · 这里慢一点看" if kind == "warning" else None)
    n = len(items)

    if kind == "cards":
        gap = 18
        cw = (640 - gap * (n - 1)) / n
        y, ch = 82, 146
        for i, item in enumerate(items):
            p = split_item(item)
            x = 40 + i * (cw + gap)
            c.rect(x, y, cw, ch, stroke=c.accent)
            c.circle(x + cw / 2, y + 30, 17, c.accent, 0.22, glow=True)
            c.text(x + cw / 2, y + 36, str(i + 1), 30, base=18, color=c.accent, weight="bold")
            main_y = y + 86 if len(p) > 1 else y + 96
            c.text(x + cw / 2, main_y, p[0], cw - 22, base=28, weight="bold")
            if len(p) > 1:
                c.text(x + cw / 2, y + 120, p[1], cw - 22, base=17, color=DIM)
            if len(p) > 2:
                c.text(x + cw / 2, y + 138, p[2], cw - 22, base=15, color=DIM, minfs=12)

    elif kind == "flow":
        gap = 42
        nw = (640 - gap * (n - 1)) / n
        y, nh = 100, 112
        for i, item in enumerate(items):
            p = split_item(item)
            x = 40 + i * (nw + gap)
            c.rect(x, y, nw, nh, stroke=c.accent)
            c.text(x + nw / 2, y + 50, p[0], nw - 18, base=25, weight="bold")
            if len(p) > 1:
                c.text(x + nw / 2, y + 82, p[1], nw - 18, base=17, color=DIM)
            if i < n - 1:
                c.arrow(x + nw + 5, x + nw + gap - 4, y + nh / 2)

    elif kind == "compare":
        lw, lx, rx, rw = 272, 40, 408, 272
        y, ch = 76, 164
        c.rect(lx, y, lw, ch, stroke=COLORS["red"], fill="#1a0f14")
        c.rect(rx, y, rw, ch, stroke=COLORS["green"], fill="#0d1a14")
        c.circle(W / 2, y + ch / 2, 26, c.accent, 0.16, glow=True)
        c.text(W / 2, y + ch / 2 + 8, "VS", 44, base=24, color=c.accent, weight="bold")
        for x, w, item, col in ((lx, lw, items[0], COLORS["red"]),
                                (rx, rw, items[1], COLORS["green"])):
            p = split_item(item)
            c.text(x + w / 2, y + 52, p[0], w - 28, base=28, color=col, weight="bold")
            if len(p) > 1:
                c.text(x + w / 2, y + 96, p[1], w - 28, base=19, color=LIGHT)
            if len(p) > 2:
                c.text(x + w / 2, y + 132, p[2], w - 28, base=17, color=DIM)

    elif kind == "stack":
        step = min(34, 168 / max(n, 1))
        h = min(30, step - 3)
        for i, item in enumerate(items):
            p = split_item(item)
            x = 110 + i * 22
            y = 76 + i * step
            w = 460 - i * 18
            c.rect(x, y, w, h, rx=10, stroke=c.accent, opacity=0.5 + i * 0.06)
            c.rect(x - 10, y + 5, 4, h - 10, rx=2, stroke=c.accent, sw=1, glow=True)
            c.text(x + 16, y + h * 0.70, p[0], w - 32,
                   base=21, color=LIGHT, anchor="start", weight="bold")
            if len(p) > 1:
                c.text(x + w - 16, y + h * 0.70, p[1], w * 0.42,
                       base=16, color=DIM, anchor="end", minfs=12)

    elif kind == "badge":
        p = split_item(items[0])
        c.rect(180, 88, 360, 124, rx=28, stroke=c.accent, opacity=0.55, glow=True)
        c.text(W / 2, 164, p[0], 320, base=44, color=c.accent, weight="bold")
        if len(p) > 1:
            c.text(W / 2, 194, p[1], 320, base=19, color=DIM)
        side = items[1:5]
        pos = [(20, 100), (560, 100), (20, 190), (560, 190)]
        for (x, y), item in zip(pos, side):
            q = split_item(item)
            c.rect(x, y, 140, 52, rx=14, stroke=c.accent, opacity=0.45)
            c.text(x + 70, y + 33, q[0], 124, base=18, color=LIGHT)

    elif kind == "grid":
        cols = min(4, n)
        rows = math.ceil(n / cols)
        cw, gapx, ch, gapy = 148, 16, 62, 12
        y0 = 80
        for r in range(rows):
            row = items[r * cols:(r + 1) * cols]
            total = len(row) * cw + (len(row) - 1) * gapx
            x0 = (W - total) / 2
            for j, item in enumerate(row):
                p = split_item(item)
                x = x0 + j * (cw + gapx)
                y = y0 + r * (ch + gapy)
                c.rect(x, y, cw, ch, rx=14, stroke=c.accent, opacity=0.5)
                c.text(x + cw / 2, y + 39, p[0], cw - 18, base=22, weight="bold")
                if len(p) > 1:
                    c.text(x + cw / 2, y + 56, p[1], cw - 18, base=14, color=DIM, minfs=12)

    elif kind == "warning":
        # 信息层级：框内大字 = 警示本身（title），框内小字 = 怎么做 / 为什么（items）
        c.rect(60, 84, 600, 144, rx=20, stroke=COLORS["red"],
               fill="#2a0f14", opacity=0.55, sw=3, glow=True)
        # 几何警示三角，不用 emoji
        c.parts.append(
            f'<polygon points="100,112 82,146 118,146" fill="none" '
            f'stroke="{COLORS["red"]}" stroke-width="3" stroke-linejoin="round"/>')
        c.text(100, 140, "!", 20, base=20, color=COLORS["red"], weight="bold")
        c.text(W / 2 + 18, 152, title, 500, base=34,
               color="#fca5a5", weight="bold")
        lines = []
        for item in items:
            lines.extend(split_item(item))
        if lines:
            c.text(W / 2 + 18, 190, lines[0], 520, base=19, color=COLORS["red"])
        if len(lines) > 1:
            c.text(W / 2 + 18, 214, lines[1], 520, base=17, color=DIM)

    else:
        raise ValueError("unknown kind: " + kind)

    return c


# (文件名, kind, 标题, 条目, 底部提示, 主色)
SPECS = {
    "01": [
        ("broll_大模型问答框", "cards", "AI 大模型 = 会聊天",
         ["豆包|文字问答", "DeepSeek|文字问答", "问答框|一问一答"],
         "能回答问题，但不会替你动手干活", "slate"),
        ("broll_三板块", "cards", "WorkBuddy = 会干活",
         ["办公|写文档做表格", "开发|写代码建应用", "设计|做图做页面"],
         "三个板块，都对着实际工作", "blue"),
        ("broll_工作流融合", "flow", "扣子：不再用搭工作流",
         ["工作流节点链|原来的重心", "插件 + 大模型|现在", "开箱即用|不用自己搭"],
         "节点收拢、融合成新形态，一个连续动作完成", "purple"),
        ("broll_国内生态", "cards", "国内生态，下载即用",
         ["飞书|办公协同", "邮件|收发处理", "Excel|表格数据", "企微|企业信息"],
         "连接器图标沿弧线依次接入中心", "cyan"),
        ("broll_拼写buddy", "badge", "拼写：buddy 是「伙伴」",
         ["w-o-r-k-b-u-d-d-y|别打成 body", "b-u-d-d-y", "官网保底", "workbuddy.cn", "英文点"],
         "记不住拼写，就直接敲 workbuddy.cn", "amber"),
        ("broll_多端支持", "cards", "自动识别你的系统",
         ["Windows|10 以上", "Mac|苹果电脑", "鸿蒙|华为", "Linux|及移动端"],
         "下载页会自动推荐对应版本", "green"),
    ],
    "03": [
        ("broll_三种模式", "cards", "新建任务：三种模式",
         ["办公|默认，最常用", "开发|写代码建应用", "设计|做图做页面"],
         "新手默认选「办公」就对了", "blue"),
        ("broll_积分倍率", "flow", "右边的数字 = 积分倍率",
         ["快速|1× 省积分", "均衡|2×", "极致|3× 消耗快"],
         "数字越大，积分花得越快", "amber"),
        ("broll_夜间免费", "badge", "夜间免费时段",
         ["23:00 – 08:00|腾讯混元 HY3 / HY4", "夜间", "免费", "HY3", "HY4"],
         "晚上干活优先用免费额度", "green"),
        ("broll_零积分", "badge", "数字为 0",
         ["0 积分|不消耗额度", "优先用", "免费标签", "省着花", "看数字"],
         "看到 0，就是这一档不花钱", "green"),
        ("broll_多模态输入", "cards", "多模态 = 不只看文字",
         ["文字|纯语言也行", "图片|能看懂", "视频|能看懂", "音频|能听懂"],
         "四条输入沿弧线汇入同一个模型", "cyan"),
        ("broll_模型价格", "cards", "编码模型：价格差很多",
         ["混元|常用", "Space Bunning|编码", "DeepSeek|编码", "Kimi 3|1.62 最贵"],
         "新手不用纠结，只选快速/均衡/极致", "amber"),
        ("broll_五张图", "grid", "桌面上 5 张图片",
         ["IMG_01", "IMG_02", "IMG_03", "IMG_04", "IMG_05"],
         "AI 用命令行读取，不是看图猜", "blue"),
        ("broll_先备份", "warning", "先备份，再重命名",
         ["这一步别跳|做错了还能退回来"],
         "先备份是安全操作的习惯", "green"),
        ("broll_权限风险", "warning", "「允许完全访问」有风险",
         ["电脑里没有贵重资料再勾|平时用默认安全沙箱"],
         "默认权限会追着你确认，是保护你", "red"),
        ("broll_散乱vs归档", "compare", "任务 vs 空间",
         ["任务：散乱存|文件到处都是|找不到", "空间：归档存|指定文件夹|好管理不丢"],
         "左边乱飞，右边被文件夹吸进去", "blue"),
        ("broll_工作空间树", "stack", "空间 = 一个真实文件夹",
         ["D:\\", "WorkBuddy课程|工作空间", "01_基础课|项目目录", "03_素材|文件都在这"],
         "所有产物落在同一个文件夹里", "cyan"),
        ("broll_优化前后", "compare", "自动优化提示词",
         ["优化前|一句话|信息不全", "优化后|补全要求|更适合新手"],
         "写不好提示词，点一下让 AI 帮你补", "purple"),
    ],
    "04": [
        ("broll_三入口", "cards", "左上角，三个入口",
         ["专家|更接近本人", "技能|别人的经验", "连接器|接外部能力"],
         "三个词先认个脸，后面用装修比喻讲透", "blue"),
        ("broll_水电走线", "flow", "装修第一步：通水通电",
         ["房子|线框落位", "水管电路|沿墙走线", "连接器|前提条件"],
         "管线一点点长出来，不是整张图直接出现", "cyan"),
        ("broll_三种工种", "cards", "技能 = 有手艺的工人",
         ["电工|依赖电路", "水暖工|依赖水路", "瓷砖工|不依赖水电"],
         "瓷砖工脚下不连水电，这个差异要讲清", "purple"),
        ("broll_装修队长", "badge", "专家 = 装修队长",
         ["协调指挥|不自己干活", "指挥工人", "调度水电", "对用户负责", "越靠左越近"],
         "三条指挥弧线连到工人和水电", "amber"),
        ("broll_层级轴", "flow", "越靠左，离用户越近",
         ["连接器|前提条件", "技能|手艺经验", "专家|协调指挥"],
         "一条轴线一次画出，别分三页", "blue"),
        ("broll_三栏对照", "cards", "回到 WorkBuddy",
         ["连接器|接外部能力", "技能|封装的经验", "专家|更接近本人"],
         "装修元素原地变形回真实界面", "cyan"),
        ("broll_飞书周报封装", "flow", "技能里可以包含连接器",
         ["飞书连接器|外部能力", "写周报经验|方法", "飞书周报技能|装在一起"],
         "点开技能说明，能看到它需要哪些连接器", "green"),
        ("broll_专家封装", "flow", "专家 = 封装多个技能",
         ["写周报|技能 A", "记账打卡|技能 B C", "个人工作台|专家"],
         "同一张封装图放大一层，形成递进", "purple"),
        ("broll_斜杠搜索", "badge", "斜杠搜索最常用",
         ["/ 去AI味|输入斜杠直接搜", "去试试", "加号选", "斜杠搜", "三种方式"],
         "三种使用方式都录一遍，斜杠多停留", "blue"),
        ("broll_定时指令", "badge", "每天定时领积分",
         ["09:00|自动执行", "每天", "重复", "推送", "有效期"],
         "设定时用技能，比自己从零写省事", "green"),
        ("broll_原生复杂", "warning", "不用技能，自己设定时很难",
         ["要写一堆代码|新手别从这儿入手"],
         "这就是为什么推荐先用现成技能", "red"),
        ("broll_代码别动", "warning", "上面的代码，看不懂就别动",
         ["只改下面的重复/时间/有效期/推送|改错了整个任务会失效"],
         "红色警示贴边，不挡住设置项文字", "red"),
    ],
    "05": [
        ("broll_文档交给AI", "flow", "把资料交给 AI",
         ["Word 文档|你的资料", "知识库|存进去", "按资料回答|能查细节"],
         "三种方式，适用范围一层比一层大", "blue"),
        ("broll_工作空间圈", "badge", "方式一：工作空间",
         ["单任务 · 单项目|只在这个任务里有效", "第 1 圈", "范围最小", "当前任务", "跳出不用"],
         "同心圆第 1 圈，后面会一圈圈放大", "cyan"),
        ("broll_存储提示词", "badge", "关键词：存储",
         ["把这个文档作为你的知识库，存储|一句话固化", "要写存储", "会建索引", "能长期用", "别只说回答"],
         "只说「结合文档回答」不算真的存进去", "green"),
        ("broll_错误对照", "warning", "只说「结合文档回答」不够",
         ["没有「存储」两个字|下次开新对话就忘了"],
         "错误说法做灰化划掉对照", "red"),
        ("broll_目录逐层", "stack", "存进去之后，长什么样",
         [".workbuddy|软件自动建", "memory|记忆目录", "知识库|资料在这", "Markdown|转成纯文本"],
         "一镜向下钻取，不做成 PPT 分页", "purple"),
        ("broll_Word转MD", "flow", "为什么转成 Markdown",
         ["Word|格式复杂", "Markdown|纯文本", "AI 更好读|检索快"],
         "格式变形用 morph，不要硬切", "blue"),
        ("broll_index全文", "compare", "为什么要存两份",
         ["index 总索引|答概念|快速定位", "全文|答细节|逐条查证"],
         "一份管方向，一份管细节", "cyan"),
        ("broll_E16", "badge", "实测：E16 是什么",
         ["E16|扫地机 App 报错", "基站问题", "不用寄修", "看文档", "验证成功"],
         "用真实问题验证知识库有没有生效", "amber"),
        ("broll_多任务汇聚", "grid", "多任务之间共享",
         ["任务 A", "任务 B", "任务 C", "任务 D"],
         "四个任务指向同一个共享资料库", "blue"),
        ("broll_多用户共享", "grid", "团队多人共享",
         ["成员 1", "成员 2", "成员 3", "成员 4"],
         "资料库比工作空间多了一层「共享」", "purple"),
        ("broll_入库三入口", "cards", "资料库怎么加文档",
         ["新建|直接写", "上传|本地文件", "导入|腾讯文档"],
         "也可以直接说「把这个存入资料库里」", "cyan"),
        ("broll_跨任务调用", "flow", "全新对话也能用",
         ["新对话|不建工作空间", "引用资料库|一句话", "答出 E16|验证通过"],
         "证明它跳出了单个任务", "green"),
        ("broll_ima授权", "flow", "方式三：ima 知识库",
         ["更多 → ima|入口", "微信扫码|授权", "知识库面板|打开"],
         "同心圆第 3 圈继续外扩", "blue"),
        ("broll_20G", "badge", "免费 20G 空间",
         ["20G|个人够用", "免费", "容量大", "多格式", "可商用"],
         "数字从 0 滚动到 20G", "green"),
        ("broll_格式图标组", "grid", "支持格式多",
         ["文件", "文件夹", "网页链接", "笔记", "腾讯文档", "录音纪要"],
         "支持格式多，是 ima 的第二个好处", "purple"),
        ("broll_四文档", "grid", "上传后多出 4 个文档",
         ["文档 1", "文档 2", "文档 3", "文档 4"],
         "切回 WorkBuddy，能看到文档已同步", "cyan"),
        ("broll_三圈对比", "stack", "三种方式，怎么选",
         ["工作空间|单任务单项目", "资料库|多任务多用户共享", "ima|企业级商用大库"],
         "范围越大，共享越多", "amber"),
    ],
    "06": [
        ("broll_手机连电脑", "flow", "人在外面，也能指挥电脑",
         ["手机|发指令", "云端|中转", "电脑 WorkBuddy|执行"],
         "一条连接线 0.5 秒画出", "blue"),
        ("broll_两个开关", "cards", "两个开关都要勾",
         ["允许移动端连接此设备|不勾连不上", "保持唤醒状态|不勾会卡死"],
         "红色标签贴边，不挡开关文字", "red"),
        ("broll_锁屏卡死", "warning", "两个开关不勾会卡死",
         ["电脑一锁屏，远程任务就断|这里慢一点看"],
         "第一种方式最常见的坑", "red"),
        ("broll_云端切设备", "flow", "云端切换设备",
         ["手机端|扫码登录", "设备列表|两台都在", "电脑端|选中它"],
         "两台设备同帧出现，方便对照", "cyan"),
        ("broll_双端同步", "compare", "手机说，电脑动",
         ["手机投屏|语音提问", "电脑端|同步响应"],
         "两端变化间隔不超过 0.3 秒", "blue"),
        ("broll_六入口", "grid", "助理设置页：六个平台",
         ["微信", "企业微信", "飞书", "钉钉", "QQ", "企微 Bot"],
         "六个入口扇形错峰展开", "purple"),
        ("broll_上下文增长", "flow", "聊天记录越长，越费积分",
         ["记录叠加|越来越长", "积分消耗|同步上升", "6 小时|默认截断"],
         "三者同帧联动，不轮流播卡片", "amber"),
        ("broll_六小时截断", "badge", "默认 6 小时截断",
         ["06:00|上下文时间窗", "可调整", "省积分", "别怕长", "会自动截"],
         "截断线落定时给一个轻提示音", "amber"),
        ("broll_微信联系人", "badge", "微信 Cloud Bot",
         ["红色联系人|就在微信里", "不用开小程序", "像聊天一样", "发任务", "收文件"],
         "连小程序都不用打开", "green"),
        ("broll_自动挑模型", "cards", "不用手动选多模态模型",
         ["快速模式|前三个自动挑", "图片|能识别", "语音|能听懂"],
         "打消新手「要不要先换模型」的顾虑", "green"),
        ("broll_压缩包回传", "flow", "要文件，直接让它发",
         ["手机发消息|提要求", "电脑打包|压缩", "手机收到|5 张图"],
         "任何文件、文档、压缩包都能要", "cyan"),
        ("broll_删除重连", "flow", "连接失败怎么办",
         ["创建失败|重复创建", "删除机器人|清干净", "重新连接|成功"],
         "三步完整走一遍，别只讲结论", "red"),
        ("broll_二维码别关", "warning", "二维码页面别关",
         ["关掉就得重新走一遍授权|右上角小窗全程保留"],
         "本节课最大的避坑点", "red"),
        ("broll_群内艾特", "grid", "企业微信可以拉群",
         ["群聊", "智能机器人", "艾特它", "全员可用"],
         "这是企微和微信最大的区别", "purple"),
        ("broll_两条连接", "compare", "两种连接方式",
         ["微信助理|个人聊天|一对一", "企业微信|可拉群|全员共用"],
         "连线分叉成两条，收尾呼应开头", "blue"),
    ],
    "07": [
        ("broll_prompt输入框", "badge", "提示词 = prompt",
         ["你写给 AI 的那句话|最基础，也最重要", "开头呼应", "结尾呼应", "别跳步", "耐心听"],
         "首尾复用同一张输入框，形成呼应", "blue"),
        ("broll_三能力", "cards", "写好提示词的三种能力",
         ["词汇量|说得准", "审美|知道什么叫好", "抽象|能提炼结构"],
         "三张卡自左向右错峰浮起", "purple"),
        ("broll_文学对比", "compare", "谁写得最好",
         ["文学方向|词汇+审美+抽象|往往最强", "程序员|结构熟|但结构本身不复杂"],
         "纠正「程序员天然更懂」的误区", "purple"),
        ("broll_行业关键词", "cards", "行业经验决定上限",
         ["小程序|懂行才写得出", "网页|懂术语", "App|懂场景"],
         "关键词胶囊沿一条线依次点亮", "cyan"),
        ("broll_三角色", "cards", "提示词的三种角色",
         ["user|你说的话", "assistant|AI 的回复", "system|官方预置"],
         "三张卡同尺寸、顶对齐、等间距", "blue"),
        ("broll_system贯穿", "stack", "system 优先级最高",
         ["system|置顶", "贯穿所有对话|向下约束", "user / assistant|都受影响"],
         "顶部贯穿条一次画出", "amber"),
        ("broll_无状态大脑", "badge", "AI 是无状态的",
         ["每次对话都从零开始|靠聊天记录记住前面", "无状态", "短期记忆", "上下文", "会遗忘"],
         "这是理解上下文上限的前提", "slate"),
        ("broll_上下文条截断", "flow", "上下文会装满",
         ["聊天记录|打包送来", "短期记忆|越积越长", "上限截断|右端被切"],
         "进度条填充 + 截断是一个连续动作", "amber"),
        ("broll_三条出路", "cards", "装不下时的三种做法",
         ["忽略|早期内容丢掉", "压缩总结|压成摘要", "长期记忆|12 点刷新"],
         "三条出路从截断点分叉", "cyan"),
        ("broll_黑盒子", "badge", "黑盒子比喻",
         ["AI 不是不聪明|是你给的信息太少", "补一条", "亮一档", "再补", "答案更准"],
         "盒内粒子密度与质量条同帧联动", "slate"),
        ("broll_蛋糕两问", "compare", "同一件事，两种问法",
         ["规矩小助手|请写蛋糕介绍|语气平", "捣蛋家伙|用调皮口气写|语气活"],
         "扮演角色：套语气，也调记忆", "purple"),
        ("broll_必须", "flow", "少说「也许」，多用「必须」",
         ["也许…|模糊，AI 会自由发挥", "必须…|边界清楚，结果稳"],
         "划掉 → 落定，一个动作做完", "green"),
        ("broll_Markdown对照", "compare", "分隔符 + Markdown",
         ["# 标题|井号开头|结构清楚", "* 加粗斜体|星号包住|重点突出"],
         "左输入右渲染，同屏对照", "blue"),
        ("broll_分步相乘", "flow", "分步执行：12345 × 12345",
         ["拆位|按位拆开", "逐位相乘|一步一步", "合并结果|得出答案"],
         "每一步只亮当前位，其余压暗", "amber"),
        ("broll_注意力光点", "grid", "复杂任务要拆开",
         ["标书 1", "标书 2", "标书 3", "标书 4"],
         "注意力光点一块一块跳焦", "cyan"),
        ("broll_审核流水线", "flow", "检查者角色：合同审核",
         ["初审|通读", "精细化|逐条改", "检查者|挑错", "律师|定稿"],
         "四节点从左到右一次串成", "green"),
        ("broll_检查者拦截", "warning", "检查者把错误拦下",
         ["红圈标出 → 回退一格重改|比一次写完更靠谱"],
         "流水线要能看到「回退」这个动作", "red"),
        ("broll_五段框架", "stack", "最常用：五段结构",
         ["角色|你是谁", "技能|你会什么", "要求|工作流程", "示例|给个样子", "限制|不能做什么"],
         "先叠成一摞，再展开成阶梯", "purple"),
        ("broll_代码化提示词", "badge", "提示词 + 代码",
         ["既非纯给人看|也非纯给机器看", "新结构", "更可控", "可复用", "进阶用"],
         "只作展示，新手先掌握五段框架", "slate"),
        ("broll_模型推荐", "cards", "按用途挑模型",
         ["Claude|编程 / 中文写作", "DeepSeek|推理", "豆包|日常"],
         "推荐只是参考，先把手里的用熟", "blue"),
    ],
}


def validate(path):
    """解析 SVG，估算每个 text 的边界，检查不越界、字号不过小。"""
    errors = []
    try:
        root = ET.parse(path).getroot()
    except Exception as e:
        return [f"XML 解析失败: {e}"]
    ns = "{http://www.w3.org/2000/svg}"
    for t in root.iter(ns + "text"):
        s = "".join(t.itertext())
        if not s.strip():
            continue
        try:
            x = float(t.get("x", 0))
            y = float(t.get("y", 0))
            fs = float(t.get("font-size", 26))
        except ValueError:
            errors.append("属性值非法: " + s[:20])
            continue
        anchor = t.get("text-anchor", "middle")
        w = text_w(s, fs)
        left = x if anchor == "start" else (x - w if anchor == "end" else x - w / 2)
        right = left + w
        if left < -1 or right > W + 1:
            errors.append(f"横向越界 [{left:.0f},{right:.0f}]: {s[:24]}")
        if y < 0 or y > H:
            errors.append(f"纵向越界 y={y}: {s[:24]}")
        if fs < 12:
            errors.append(f"字号过小 {fs}: {s[:24]}")
    return errors


def main():
    check_only = "--check" in sys.argv
    total, failed = 0, 0
    for lesson, specs in SPECS.items():
        lesson_dirs = glob.glob(os.path.join(OUT_ROOT, f"第{lesson}课_*"))
        if not lesson_dirs:
            print(f"  [SKIP] 找不到第{lesson}课目录")
            continue
        outdir = os.path.join(lesson_dirs[0], "03_素材", "broll")
        os.makedirs(outdir, exist_ok=True)
        for spec in specs:
            name = spec[0] if spec[0].endswith(".svg") else spec[0] + ".svg"
            path = os.path.join(outdir, name)
            if not check_only:
                c = build(spec)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(c.render())
            total += 1
            if os.path.exists(path):
                errs = validate(path)
                if errs:
                    failed += 1
                    print(f"  [FAIL] 第{lesson}课 {name}: " + "; ".join(errs[:2]))
            else:
                failed += 1
                print(f"  [MISS] 第{lesson}课 {name}")
    print(f"\nB roll 校验：共 {total} 个，失败 {failed} 个")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
