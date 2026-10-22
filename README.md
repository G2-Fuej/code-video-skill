# PCL Workstation Edition

基于开源版 Plain Craft Launcher (PCL) 2.14.0.0 源码制作的第三方界面二次修改版。上游取消了直装原版 MC 与整合包导入，本分支把它加了回来：一键下载原版 Minecraft 并自动装配 Forge / Fabric / NeoForge / OptiFine，也能搜索、下载并安装 CurseForge / Modrinth 整合包。无病毒、无广告、无埋点、完全开源。仓库：https://github.com/G2-Fuej/PCL-Workstation-Edition

A 61-second promo reel where **every pixel is computed**. No diffusion model,
no video-generation model, no sampled footage or music: frames are numpy arrays
written to ffmpeg, and the score is built from oscillators and envelopes.

## Video

https://github.com/G2-Fuej/code-video-skill/blob/main/PCL-Workstation-Edition-61s.mp4

## Reproduce

```powershell
python engine/director.py spec.json -o out.mp4 --probe
```

The whole timeline lives in `spec.json`, generated from `brief.json` by
`engine/brief.py`. Nothing in the render path touches the network.

## Structure

```text
brief.json      # interview answers: the only human input
spec.json       # resolved timeline (act -> style -> payload)
prompt.md       # human-readable version of the same timeline
engine/         # render pipeline (core, typekit, scenes, score, director)
scripts/        # smoke test, style check, publish
```

## Credits

- **Original author**: 龙腾猫跃 (LTCat) — https://meloong.com/pcl
- **Upstream source**: https://github.com/Meloong-Git/PCL
- **This fork**: https://github.com/G2-Fuej/PCL-Workstation-Edition

Generated with the `code-video` skill.
