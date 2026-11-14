# 课程制片团（WorkBuddy Course Crew）

> 一个**多智能体协作的课程视频制作团队**：把口播稿、录音和素材交给它，逐句选画面、做动画、配音、配乐，最后合成可发布的成片。

这不是一个"做视频的软件"，而是一套**可复用的 skill 集合 + 智能体协作规范**——把录课这件事沉淀成「组件库 + 门禁 + 质量审计」三位一体的工作流，让 AI 每次做课都能做出稳定、有质感的效果，而不是靠运气。

## 为什么做这个

做课程视频最难的，不是"会不会用某个软件"，而是**有没有一套被严格执行的约束**：

- 同一个口播稿，为什么 Claude / Codex 做出来丝滑，手写代码做出来像 PPT？—— 差距不在工具，在约束。
- 做 26 节课，最大的成本不是每一节从头做，而是**每一节都从零重新发明轮子**。

这个仓库把「录课方法论」沉淀成三个 skill + 五个智能体，让流程可复用、效果可复现、经验可积累。

## 团队（5 个智能体）

| 智能体 | 名字 | 职责 |
|---|---|---|
| 制片总监 | 周全片 | 编排调度、TeamCreate 建团队、汇总交付 |
| 内容编导 | 文成稿 | 逐字稿 → 口播稿 → 分镜脚本 → 逐句动作表 |
| 语音配音 | 冯佳音 | 音色克隆、TTS 配音、配乐/音效选材、字幕 |
| 视频导演 | 影成帧 | 查组件库选型、概念动画、录屏指导、音画合成 |
| 审片导演 | 严把关 | 字幕/声音/画面/节奏质检、录屏必要性评估 |

## 六个 Skill（核心资产）

| Skill | 管什么 | 文件 |
|---|---|---|
| **production-spec** | 正确性：确定性渲染、字幕避让、音效音量、工程踩坑清单 | `skills/production-spec/SKILL.md` |
| **animation-spec** | 丝滑感：先方案后渲染、先样片后全片、光晕+胶片颗粒、配音驱动、字幕按字对齐 | `skills/animation-spec/SKILL.md` |
| **course-visual-library** | 画面从哪来：WorkBuddy 课程组件库 + 检索 + 门禁 + 成对样例 + 底层 kit | `skills/course-visual-library/` |
| **episode-assembly** | 整期编排：A/B 双轨画面结构、录屏包装（推近/跟口播）、段间交接表、机器闸阈值 | `skills/episode-assembly/SKILL.md` |
| **teaching-spec** | 教学法：SOP 四要素步骤链、术语即解释、每课一任务一条规则、开场钩子与耐心语气 | `skills/teaching-spec/SKILL.md` |
| **terminology-spec** | 术语唯一事实源：防中途换模型术语漂移，机器闸硬拦禁用写法与大小写错误 | `skills/terminology-spec/` |

### 课程视觉组件库（catalog.json）

把口播的表达意图映射到可复用画面组件，做动画前先检索、默认复用已认可组件，禁止脱离库原创。

当前 24 个组件，5 类：概念动画（进化蜕变/定位对比/生态连接/流程步骤/层级架构/记忆对比/文件夹归档/角色生长/跳焦/信息密度）、实操录屏包装（下载/安装避坑/登录/积分/配置）、文字强调（要点列表/关键词结论/数字滚动/终端命令/提示词输入/长回复拎要点）、数据图表（趋势折线/对比柱状）、章节转场。

## 目录结构

```
.
├── README.md                     # 本文档
├── plugin.json                   # 专家包元信息（Team 型）
├── settings.json                 # 团队入口
├── agents/                       # 5 个智能体定义
│   ├── course-crew-team-lead.md
│   ├── content-director.md
│   ├── voice-director.md
│   ├── video-director.md
│   └── reviewer.md
├── skills/                       # 6 个核心 skill
│   ├── production-spec/
│   ├── animation-spec/
│   ├── course-visual-library/
│   │   ├── SKILL.md
│   │   ├── catalog.json
│   │   └── references/paired-examples.md
│   ├── episode-assembly/
│   ├── teaching-spec/
│   └── terminology-spec/
│       ├── SKILL.md
│       └── terminology.json     # 术语唯一事实源（机器闸直接读取）
└── docs/
    ├── 剪辑专项规范.md            # 剪辑常见问题清单 + 音量参数
    ├── 基础课教学设计.md          # 7 门课学习目标 / SOP 步骤链 / 小任务
    └── 踩坑经验总结.md            # 25 条真实踩坑档案（现象/原因/解法/防范）+ 速查表
```

## 快速开始

在 WorkBuddy 里，把这个仓库作为「专家包」导入，或直接把 `skills/` 目录的内容交给任意编程 Agent 读取。

> 请读取 `skills/` 下的 SKILL.md。这是我的口播稿、录音和素材。请根据每段内容，从视觉组件库选择合适的组件，展示参考并说明理由，再生成关键帧供我确认，最后合成视频。

核心工作流：

```
逐字稿 → 口播稿 → 分镜脚本（内容编导）
                → 音色克隆 + 配音 + 配乐音效（语音配音）
                → 查组件库选型 + 动画 + 录屏（视频导演）
                → 音画合成成片（视频导演）
                → 审片质检（审片导演）
                → 剪映精修 + 归档
```

## 工具件（tools/）

流水线里的程序化闸门都是纯本地脚本，不依赖模型、不花 token，可以直接跑：

| 脚本 | 作用 |
|---|---|
| `tools/gen_broll.py` | 参数化生成 B roll SVG；自适应字号 + 文字边界校验，杜绝溢出和裁切 |
| `tools/apply_teaching_spec.py` | 按 teaching-spec 给口播稿补开场钩子 / 课后小任务 / 记住一句话，清禁用词，并从口播稿重建 TTS 朗读稿 |
| `tools/validate_delivery.py` | 交付机器闸：分镜 ↔ B roll 素材 ↔ 口播稿 ↔ TTS 稿 四方交叉校验 + 术语闸 |
| `tools/sync_catalog.py` | 组件库沉淀 + 专家包/仓库双份同步，顺带修复历史坏字符 |
| `tools/fix_terminology.py` | 术语批量修复：deepseek→DeepSeek 等大小写/错写一键修正（幂等） |
| `tools/gen_tts.py` | 批量配音：MiniMax speech-2.8-hd 克隆音色，≤400 字切段、并行合成、断点续跑、ffmpeg 拼接 |
| `tools/align_subtitles.py` | **字幕-动画实测对齐**：VAD 能量检测取真实句界（10ms 帧/120ms 静音判界），替代字数估算，输出逐句精确起止 |
| `tools/review_gate.py` | **审片闸门**：D2/D3/D4/D6/D8 自动检测，输出判定+测量值+阻断清单，退出码即结论 |
| `tools/push_github.py` | 走 Contents API 同步变更（绕开被墙的 git 协议），token 走环境变量 |

> **接手必读**：`docs/踩坑经验总结.md` —— 25 条真实踩坑档案，含现象/原因/解法/防范 + 症状速查表。做动画前额外读 `skills/animation-spec`（含 V2 固定色板），改文稿前读 `skills/terminology-spec`。

```bash
python tools/gen_broll.py
python tools/apply_teaching_spec.py --dry   # 先看报告，幂等可重复跑
python tools/apply_teaching_spec.py
python tools/validate_delivery.py           # 交付前必跑
python tools/sync_catalog.py
python tools/fix_terminology.py --dry
python tools/gen_tts.py --lesson 01         # 先配一课试听
```

> 设计原则：**技术缺陷交给脚本抓，审美问题留给人看图**。机器闸 PASS 不等于视觉通过，关键帧仍需人工过目。

## 自我进化路线

这套东西会持续迭代，越做越好：

```
做课（录 WorkBuddy 课）→ 沉淀（把表达方式/踩坑写进 skill + 组件库）→ 开源（本仓库）→ 反哺（复用 + 反馈让下一课更好）↺
```

每做一节课，就把这节课新出现的表达方式沉淀成新组件（写入 `catalog.json`），把踩过的坑写进 `production-spec` 的踩坑清单，把"做对 vs 做错"的对照写进 `paired-examples.md`。

## License

MIT License —— 允许商用、修改、再分发，保留版权与许可声明。第三方素材（字体/音效/图片）按各自原许可。
