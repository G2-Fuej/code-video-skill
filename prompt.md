做一个 61 秒、19 种风格、不调用任何视频模型的代码视频。
每一帧都是 Python 算出来的：numpy 数组 → ffmpeg。配乐也是程序化合成的，
没有一个采样素材。片长精确 61.000 秒，1920×1080，60fps，共 3660 帧。
代码是 AI 写的，画面不是 —— 没有任何扩散模型、视频大模型参与，
所有像素都是数学公式跑出来的。
一次跑完，就能得到 19 个完全不同的世界。

## 视频主题（必须完整传达）
基于开源版 Plain Craft Launcher (PCL) 2.14.0.0 源码制作的第三方界面二次修改版。上游取消了直装原版 MC 与整合包导入，本分支把它加了回来：一键下载原版 Minecraft 并自动装配 Forge / Fabric / NeoForge / OptiFine，也能搜索、下载并安装 CurseForge / Modrinth 整合包。无病毒、无广告、无埋点、完全开源。仓库：https://github.com/G2-Fuej/PCL-Workstation-Edition

## 时间轴
00:00 PHYLLOTAXIS      PCL WORKSTATION EDITION
00:02 TRUCHET          UPSTREAM CUT THE PIPELINE
00:05 FLOW FIELD       NO VANILLA DOWNLOAD  ·  NO MODPACK IMPORT
00:08 VORONOI          THIS FORK PUTS IT BACK
00:11 ASCII            RESTORED IN CODE
00:14 HALFTONE         原版游戏 · 整合包 · 加载器
00:17 SWISS GRID       INSTALL COMPONENTS
00:20 CRT / VHS        SOURCE AVAILABLE FOR AUDIT
00:23 KALEIDOSCOPE     CURSEFORGE / MODRINTH 整合包
00:26 OSCILLOSCOPE XY  VERSION → LOADER → DOWNLOAD
00:29 BLUEPRINT        ENGINEERING BLUEPRINT
00:33 TERRAIN          49938 LINES OF REAL SOURCE
00:36 EDITORIAL        第三方基于 PCL 独立进行二次创作
00:39 GALAXY           OPEN SOURCE LIGHTS IT UP
00:42 DE STIJL         重切布局 · 双栏工作台
00:45 PIXELSORT        DOWNLOAD 0% → 100%
00:48 PLOTTER          一键启动
00:51 METABALLS        原版 + 加载器 + API 融为一个实例
00:54 MATRIX           19 WORLDS · ONE RENDER
00:59 ENDCARD

## 技术栈
Python 3.11 · numpy · OpenCV · Pillow · ffmpeg
无网络请求，无外部素材，无视频生成模型

## 画面与配色规则
- primary: #2563EB
- accent: #14B8A6
- danger: #E11D48
- bg: #08090C
- ink: #E8EAF0
- sub: #8A93A6
- paper: #F2EFE6
- warm: #F5A524

## 片尾卡文案（必须逐字渲染）
written, rendered and scored in code
PCL Workstation Edition
github.com/G2-Fuej/PCL-Workstation-Edition
基于 Plain Craft Launcher 2.14.0.0 二次创作 · 原作者：龙腾猫跃（LTCat）