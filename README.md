# 君君动画故事

这是两个独立静态故事网站的迁移主库：

- `gift`：《准备礼物》，故事二。
- `football`：《君君的足球》，原故事。

## 目录

网站与素材分开存放，同级管理：

```text
websites/
  gift/dist/       # 故事二可直接部署的静态网站
  football/dist/   # 原故事可直接部署的静态网站
materials/
  original/gift/   # 选定的插图原文件与索引
  original/football/
  final/gift/      # 正式素材、已采纳、待确认与备用分开
  final/football/
tools/            # 无依赖预览与核验脚本
deployment-manifest.json
```

每个 `dist` 包含该故事实际播放所需的图片、音轨、字幕、页面和下载清单。迁移时将对应的 `dist` 内容发布到静态托管目录即可，两个故事分别部署。不要把 `materials`、模型或录屏一起打包进网站。

## 本地预览与核验

需要 Python 3，无需安装依赖。在仓库根目录执行：

```sh
python3 tools/serve.py gift
python3 tools/serve.py football
python3 tools/verify.py
python3 tools/verify.py --write
```

默认预览地址分别为 `http://127.0.0.1:8873`、`http://127.0.0.1:8874`；按 Ctrl+C 退出并释放端口。可用 `--port` 指定端口。预览仅监听本机。

核验检查部署清单的逐文件 SHA256、文件数量和总字节数，以及大文件、符号链接、私有路径和明显凭证文本。`--write` 另生成本地 `sha256-manifest.json`，覆盖源码、网站与素材文件；此清单自身及 Git 内部文件不参与计算，不修改部署元数据。

## 线上对应关系

GitHub 是可迁移源码与素材的主库。Sites 官方源码流程目前不支持将已有项目改绑到外部 GitHub，也不提供此仓库的自动部署。`deployment-manifest.json` 记录两个独立站点的 Site 项目、发布版本、源码提交和静态文件摘要。更新后需分别通过官方 Sites 保存与部署流程发布，再记录实际部署结果；GitHub 推送成功不等于 Sites 已上线。

## 素材范围

保留选定原始插图、完整配音、已采纳结果、明确备用片段和网站必需资源。原片录屏、角色声线、私人配音配置与独有母版已归并到相邻 `../本地私有素材`，不进入公共仓库；模型与环境仍留在原位置。该私有目录另保留两份旧站本地Git历史，没有重复网站工作树。一次性过程文件、重复素材和重复ZIP已清理。网站已有 AI 内容说明应保留；素材说明不构成原作授权证明。

《准备礼物》已完成可拼接的两段开场：第一段22.8秒（下车、关门、取箱与孩子对话），第二段18.6秒（抱箱进屋、拆箱和放料）。两段均为1280×720、16:9、30fps；[视频、干净对白与制作配方](materials/final/gift/已采纳成片/README.md)集中保存，[选定首帧清单](materials/original/gift/动画参考图/开场/reference-manifest.json)位于原始素材目录。原版正式片头由用户自行剪入。

上述两段已由用户采纳，集中存放在 `materials/final/gift/已采纳成片`，合计41.4秒。Wan 后续 C「礼物模特」16秒、D「打印与快递车」14.4秒经用户观看后反馈有问题，现放在[备用片段](materials/final/gift/备用片段/Wan_礼物模特与快递车/README.md)，不计入采纳。两条早期试片也归入备用目录；不会自动用于正式剪辑。

## MiniMax 第一幕待确认版

[104秒第一幕完整预览与四个分片](materials/final/gift/待确认成片/MiniMaxH3_第一幕与佩奇开场/README.md)已完成：保留A/B，在22.8秒插入现有4秒标题卡，再接选礼物、快递游戏、小蓝莓与下一份惊喜。新段分别15、15、15.4和13.2秒，各2–3镜，使用完整自有配音与低音量配乐；28句字幕和时轴随配方保存。

新H3结果全部放在“待确认成片”，不会自动改成已采纳。佩奇前10秒四次生成被平台审核阻断，未返回视频；输入与错误保留在同目录配方。本轮周额度97%→66%，并未切换按量Key。网站静态内容没有因动画制作而修改。

随后按用户要求再试佩奇15秒及4秒，两次仍为1027；第三幕开头15秒也被1026阻断，均无新增视频，周额度未观察到额外扣减。[本轮记录与第三幕100秒制作输入](materials/final/gift/待确认成片/MiniMaxH3_第二幕复试与第三幕/README.md)单独保存，包括官方独立部署路径；原第一幕候选继续保留。

## Updream 佩奇试片

2026年10月14日的[八条试片对比页](materials/final/gift/待确认成片/Updream_佩奇模型对比_20261014/准备礼物_Updream模型试片对比.html)可离线播放，另有[参数、结果与费用](materials/final/gift/待确认成片/Updream_佩奇模型对比_20261014/README.md)。Wan3.0、可灵3.0、HappyHorse1.1、Vidu Q4 Preview都返回佩奇视频；包含厨房画画、全家出门、佩奇与布鲁伊递礼物同框，以及布鲁伊下车迎接。8条合计55秒，实扣2550积分、余100；新结果全部待确认，未覆盖已采纳A/B、原配音或两个网站。

原生源片在 `materials/original/gift/动画源片/Updream_佩奇模型对比_20261014`，统一1280×720/30fps静音预览在上述待确认目录。抽帧检查记录了绿笔重复、侧脸转形及动作偏差，生成成功不能替代成片验收。

## 后续制作素材入口

[SVG＋Remotion 10秒动作小样](materials/final/gift/待确认成片/SVG_Remotion_佩奇画画_20261015/准备礼物_SVG动画小样_播放.html)演示佩奇画画、乔治拿起同一支绿笔、基础口型与眼神互动，使用现有两句完整原速对白。角色、场景及纸上笔迹均为矢量代码，[源码和重建说明](animations/gift-svg/README.md)独立保存；目前待确认，未加入正式剪辑。

先读 [动画素材清单](materials/final/gift/动画素材清单.json)，它分别列出已采纳、待确认、备用及当前剪辑源片的文件、SHA和时长。MiniMax 官方CLI已安装（mmx 1.0.28），认证、额度查询与H3实际生成均已验证；不能把 OiiOii 任务ID当作 MiniMax 任务。

```text
materials/original/gift/
  illustrations/              # 69幅当前正式PNG，映射见illustrations.json
  动画参考图/开场/             # 12张已采纳开场的选定参考
  动画参考图/后续/             # 10张后续原型，保留给MiniMax
  动画参考图/MiniMaxH3修正/    # 2张独立补镜参考
  动画源片/                   # 当前候选实际使用的6个H3源片
  music/                      # 已选配乐参考与说明
materials/final/gift/
  已采纳成片/                 # A、B两段MP4、干净对白与配方
  待确认成片/                 # 新H3完整第一幕、4分片、字幕与配方
  备用片段/                   # Wan C/D及早期试片，未正式采纳
  voices/                     # 108句完整原WAV
  story-plan.json             # 当前84页故事与台词
  voice-manifest.json         # 每句角色、文本、音频SHA
  动画素材清单.json           # 动画选用状态与后续输入索引
```

后续保持人物活泼、有真实动作，可自然切分镜；人物、打印机、画纸和模型的比例与位置须连续。对白使用自己的完整配音作为参考，未说话的角色不能跟着张嘴。最终剪辑统一1280×720、16:9、30fps；时长按故事和动作安排，不固定10秒。已采纳片段可作为风格参考，但不将所有中间参考图同时塞入生成任务。

仓库的 [Deployments](https://github.com/Jady891213/video-bluey_peppa/deployments) 已登记两套线上网站。环境名为 `Sites-gift` 与 `Sites-football`，点击环境地址可打开当前线上故事；这属于发布结果登记，后续改动仍需单独通过 Sites 官方流程发布。

登记使用 [GitHub Deployments](https://docs.github.com/en/rest/deployments/deployments) 与 [Deployment Statuses](https://docs.github.com/en/rest/deployments/statuses)；这些记录用于标记已经完成的发布，不执行上传素材或重新部署。
