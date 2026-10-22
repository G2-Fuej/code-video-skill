# Brief schema · 访谈结果的机器可读格式

`brief.json` 是访谈的唯一产物，也是整个渲染流程的唯一输入。`engine/brief.py::build_spec()` 把它展开成 `spec.json`（逐拍时间轴），`director.render()` 再把 spec 变成 mp4。

## 顶层字段

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `title` | str | `"UNTITLED"` | 项目名，出现在片尾卡与提示词标题 |
| `subtitle` | str | `""` | 完整主题陈述，会逐字进入 `prompt.md` 的「必须完整传达」段 |
| `duration` | float | `61.0` | 总片长（秒）。所有节拍 + 片尾卡之和 |
| `fps` | int | `60` | 帧率 |
| `width` / `height` | int | `1920` / `1080` | 分辨率。**必须与环境变量 `CODE_VIDEO_W/H` 一致** |
| `seed` | int | `7` | 所有随机布局的种子，同 seed 必然复现 |
| `grain` | float | `0.010` | 胶片颗粒强度 |
| `vignette` | float | `1.0` | 暗角强度 |
| `output` | str | `"code-video.mp4"` | 输出文件名 |
| `endcard_seconds` | float | `2.0` | 片尾卡时长 |
| `palette` | obj | 见下文 | 八色板 |
| `music` | obj | `{"enabled": true, "bpm": 96}` | 配乐开关与速度 |
| `data` | obj | `{}` | 真实统计，供 TERRAIN 等场景使用 |
| `beats` | list | 必填 | 叙事节拍，见下文 |
| `endcard_lines` | list | `[]` | 片尾卡逐行文案 `[文本, 字体角色, 字号]` |
| `endcard` | obj | `{}` | 结构化片尾信息（签名 / 项目 / 仓库 / 署名） |
| `credits` | obj | `{}` | 署名键值对，写进 README 的 Credits 段 |

## palette

```json
{
  "primary": "#2563EB",
  "accent":  "#14B8A6",
  "danger":  "#E11D48",
  "bg":      "#08090C",
  "ink":     "#E8EAF0",
  "sub":     "#8A93A6",
  "paper":   "#F2EFE6",
  "warm":    "#F5A524"
}
```

`paper` 只被浅底风格使用（editorial / plotter / destijl），其余为深底。

## beats[] · 叙事节拍

```json
{
  "role": "problem",
  "style": "flow",
  "weight": 1.0,
  "music": "hollow",
  "headline": "NO VANILLA DOWNLOAD",
  "tags": ["problem", "loss"],
  "caption": "可选：画面下方的小字"
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `role` | 是 | 语义角色，参与风格匹配 |
| `style` | 否 | 显式指定风格，优先级最高；同一风格不能重复使用 |
| `weight` | 否 | 时长权重，默认 1.0 |
| `music` | 否 | `drive` / `hollow` / `pad` / `climax` / `end` |
| `headline` | 通常 | 该幕主标题 |
| `tags` | 否 | 辅助匹配的标签数组 |
| `caption` | 否 | 副标题 / 小字 |

其余字段是**风格专属载荷**，只有被匹配到的那一种风格会读取：

- `terminal`（ascii）、`plates`（halftone）、`claims`（crt）
- `rows`（swiss / xy）、`modules` + `title` + `sheet`（blueprint）
- `body` + `quote` + `kicker` + `folio`（editorial）
- `payoff`（matrix）、`rose`（plotter）

完整对照见 `style-deck.md`。

## 最少可运行 brief

```json
{
  "title": "My Project",
  "duration": 20.0,
  "beats": [
    {"role": "title",   "headline": "MY PROJECT"},
    {"role": "problem", "headline": "IT WAS SLOW"},
    {"role": "repair",  "headline": "NOW IT IS FAST"},
    {"role": "payoff",  "headline": "SHIP IT", "payoff": "GO"}
  ],
  "endcard_lines": [["built in code", "display_b", 46]]
}
```

四个节拍会自动匹配到 `phyllotaxis` → `flow` → `voronoi` → `matrix`，加 2 秒片尾卡。

## 校验

```powershell
& $py scripts/render_pcl.py --check-only   # 只生成 spec 与 prompt，不渲染
```

检查项：

- `duration` 为正且 ≥ 6（片尾卡 2 秒 + 至少 4 幕）
- `beats` 非空；每个 beat 有 `role`
- 显式 `style` 在 `DECK_BY_STYLE` 中且不重复
- `palette` 的十六进制值合法
- `data.heights` 若存在，为数值数组