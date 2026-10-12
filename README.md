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
  final/gift/      # 最终交付素材
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

仅保留选定原始插图、配音导出、最终素材与网站必需资源。原片录屏、声音参考、模型权重和推理环境仅存本地；中间试做与临时产物已清理，不进入公共仓库。网站已有 AI 内容说明应保留；角色、音乐和原作资料的权利仍属于各权利人，仓库记录与素材说明不构成授权证明。

《准备礼物》已完成可拼接的两段开场：第一段22.8秒（下车、关门、取箱与孩子对话），第二段18.6秒（抱箱进屋、拆箱和放料）。两段均为1280×720、16:9、30fps；[视频、干净对白与制作配方](materials/final/gift/准备礼物_完整开场两段_Wan3/README.md)集中保存，[选定首帧清单](materials/original/gift/完整开场参考帧/reference-manifest.json)位于原始素材目录。原版正式片头由用户自行剪入。

上述两段已由用户采纳。另已完成 Wan 后续 C「礼物模特」16秒、D「打印与快递车」14.4秒，沿用自己的完整配音，待用户观看确认；[后续成片、对白轨与配方](materials/final/gift/准备礼物_后续两段_Wan3/README.md)独立保存。四段合计71.8秒，其中已采纳41.4秒、待确认30.4秒。新片段未替换两个正式故事网站。

仓库的 [Deployments](https://github.com/Jady891213/video-bluey_peppa/deployments) 已登记两套线上网站。环境名为 `Sites-gift` 与 `Sites-football`，点击环境地址可打开当前线上故事；这属于发布结果登记，后续改动仍需单独通过 Sites 官方流程发布。

登记使用 [GitHub Deployments](https://docs.github.com/en/rest/deployments/deployments) 与 [Deployment Statuses](https://docs.github.com/en/rest/deployments/statuses)；这些记录用于标记已经完成的发布，不执行上传素材或重新部署。
