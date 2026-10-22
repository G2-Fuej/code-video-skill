# Style deck · 19 种风格的语义分工

`brief.py::STYLE_DECK` 是唯一的风格注册表。每个叙事节拍通过 `role` 或 `tags` 匹配到一种风格；一种风格在一个视频里只用一次，保证 19 个世界互不重复。

| # | style | 标签语义 | 需要的载荷 | 适合承载 |
|---|-------|----------|-----------|----------|
| 01 | `phyllotaxis` | title / brand / hero | `headline`, `kicker` | 开场、项目名 |
| 02 | `truchet` | mechanics / system / pipeline / background | `caption` | 项目背景、机制说明 |
| 03 | `flow` | problem / obstacle / loss / conflict | `caption` | 痛点、被砍掉的能力 |
| 04 | `voronoi` | repair / restore / fix / rebuild | `caption` | 修复、恢复、重组 |
| 05 | `ascii` | code / terminal / claim / audit | `terminal`, `headline` | 命令行、清单、自证 |
| 06 | `halftone` | feature / features / capability | `plates`: [3 项] | 功能三栏、三色套印 |
| 07 | `swiss` | component / variant / stack / options | `rows`: [...], `kicker` | 组件列表、逐拍改写 |
| 08 | `crt` | trust / safety / security / clean | `claims`: [3 项] | 安全声明、信号干净 |
| 09 | `kaleidoscope` | ecosystem / library / catalog | `caption` | 生态、资源库 |
| 10 | `xy` | flow / steps / sequence / signal-path | `rows`: [3 项] | 流程步骤、闭环 |
| 11 | `blueprint` | architecture / structure / modules | `title`, `sheet`, `modules`: [{name, sub}] | 工程结构、架构图 |
| 12 | `terrain` | scale / size / volume / codebase | `caption` + `data.heights` | 规模、数据量 |
| 13 | `editorial` | legal / license / colophon / credit | `body`, `quote`, `kicker`, `folio` | 许可、署名、引述 |
| 14 | `galaxy` | community / stars / open-source | `caption` | 社区、开源 |
| 15 | `destijl` | recompose / layout / redesign | `caption` | 版式重切、几何重构 |
| 16 | `pixelsort` | progress / speed / throughput | `caption` | 进度、性能、下载 |
| 17 | `plotter` | action / one-click / launch / result | `caption`, `rose {n,d}` | 一键操作、收束 |
| 18 | `metaballs` | fusion / combine / integrate / whole | `caption` | 融合、集成 |
| 19 | `matrix` | payoff / final / url / call-to-action | `payoff`（短词）, `caption` | 收尾、仓库地址 |

## 载荷格式

- `caption` / `headline` / `kicker`：单行字符串。过长会被 `fit_mask` 自动缩小。
- `plates`：字符串数组，取前 3 个，对应三种油墨。
- `claims`：字符串数组，逐条打字出现，建议 3 条。
- `rows`：字符串数组，SWISS 逐拍切换，XY 用作左侧步骤标签。
- `modules`：对象数组 `{name, sub}`，最多 4 个，对应蓝图的四个方框。
- `body`：多行字符串（`\n` 分隔），EDITORIAL 左页正文，首字做首字下沉。
- `terminal`：多行字符串，ASCII 幕逐行显示。
- `payoff`：短词，MATRIX 代码雨最终汇聚成它（建议 ≤4 字符）。
- `rose`：`{"n": 6, "d": 5}`，PLOTTER 的玫瑰线参数。

## 时长分配

`brief.beats[].weight` 控制占比，默认 1.0。片尾卡单独占 `endcard_seconds`（默认 2.0）。总时长由 `duration` 决定，各拍按权重瓜分剩余时间。

## 音乐映射

每个节拍可指定 `music`：

- `drive`：脉冲低音琶音，适合推进、功能展示
- `hollow`：单次低频撞击 + 静默，适合"东西被砍掉了"
- `pad`：温暖合成弦，适合恢复、说明、情感段
- `climax`：声部汇聚，适合收尾前的爬升
- `end`：低频长音收束，片尾卡专用
