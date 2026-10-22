# Quick start · 从零跑通一次

适用场景：skill 已安装，想先跑一次 demo，确认这台机器能渲染。

## 0. 确认环境

```powershell
$py = "C:\Users\Administrator\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
& $py -c "import numpy, cv2, PIL, imageio_ffmpeg; print('deps ok')"
gh auth status
```

缺 `imageio-ffmpeg` 就装：

```powershell
& $py -m pip install imageio-ffmpeg
```

字体：`C:\Windows\Fonts\` 下需有 `msyh.ttc`（中文）、`consola.ttf`（等宽）、`georgia.ttf`（衬线）、`bahnschrift.ttf`（瑞士风）。系统自带，一般不需要额外操作。

## 1. 跑 4 秒烟测

```powershell
& $py <skill>\scripts\smoke.py
```

输出 `out\smoke.mp4`，约 33 秒。这是最快的验证：通了说明 core / typekit / stage / scenes / score / director 全链路没问题。

## 2. 跑 20 种风格联排

```powershell
& $py <skill>\scripts\check_styles.py
```

输出 `out\style-check.png`（1920×1350，2×10 联排）。看这一张图就能判断画面质量——任何一格出现空白、豆腐块、糊成一片，都在渲染正片前修掉。

## 3. 用 demo brief 渲染完整片

```powershell
& $py <skill>\scripts\render_pcl.py --check-only    # 先生成 spec/prompt，别渲染
```

这一步会：

- 校验 brief（片长、节拍、风格重复、配色）
- 打印 19 幕的时间轴
- 写出 `out\brief.json`、`out\spec.json`、`out\prompt.md`

确认时间轴就是你要的叙事顺序，再渲染：

```powershell
& $py <skill>\scripts\render_pcl.py
```

1920×1080@60fps，32 核约 16 分钟。**跑起来就别中断**——ffmpeg 的 raw 管道被中断会留下一个只有头部的坏文件。

## 4. 抽帧检查

```powershell
$ff = & $py -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())"
& $ff -y -i "<skill>\out\PCL-Workstation-Edition-61s.mp4" `
  -vf "select='eq(n\,60)+eq(n\,300)+eq(n\,480)+eq(n\,660)+eq(n\,830)+eq(n\,1030)+eq(n\,1230)+eq(n\,1440)+eq(n\,1650)+eq(n\,1900)+eq(n\,2100)+eq(n\,2300)+eq(n\,2500)+eq(n\,2700)+eq(n\,2900)+eq(n\,3080)+eq(n\,3250)+eq(n\,3450)',scale=480:-1,tile=3x6" `
  -frames:v 1 -update 1 "<skill>\out\final-sheet.png"
```

18 帧均匀取样，3×6 排布，一眼看完 61 秒。

## 5. 换成自己的项目

复制 `scripts\render_pcl.py` 里的 `BRIEF` 字典，替换成你的内容。最少只需要这些：

```python
BRIEF = {
    "title": "你的项目名",
    "duration": 61.0,
    "beats": [
        {"role": "title",   "headline": "主标题"},
        {"role": "problem", "headline": "问题"},
        {"role": "repair",  "headline": "解决"},
        {"role": "payoff",  "headline": "结论", "payoff": "GO"},
    ],
    "endcard_lines": [["built in code", "display_b", 46]],
}
```

`role` 和 `tags` 决定匹配哪种视觉风格，完整对照见 `style-deck.md`。

## 6. 发布到 GitHub

```powershell
& $py <skill>\scripts\publish.py `
  --brief  "<skill>\out\brief.json" `
  --spec   "<skill>\out\spec.json" `
  --video  "<skill>\out\PCL-Workstation-Edition-61s.mp4" `
  --repo   your-repo-name
```

脚本会新建 public 仓库（已存在则直接推送），生成 README，推送 brief / spec / prompt / engine / scripts / video。

## 常见卡点

| 现象 | 原因 | 处理 |
|------|------|------|
| `ValueError: spec asks for 1280x720@30 but this process renders 1920x1080@60` | `core` 在 import 时绑定分辨率 | 用 `--preview`（脚本自己 re-exec），不要手改 brief 里的 width/height |
| 视频只有几 KB | ffmpeg 管道被中断 | 重跑，别中断 |
| 中文显示方框 | 字体被回退到非 CJK 面孔 | 已由 `typekit.face_for` 自动处理；仍异常则检查 `msyh.ttc` |
| 渲染速度 < 2 fps | 其他进程占满 CPU | 关掉预览，`TERRAIN`/`GALAXY` 是最贵的两幕 |
| `gh: command not found` | 未装 GitHub CLI | 装 `gh` 并 `gh auth login` |