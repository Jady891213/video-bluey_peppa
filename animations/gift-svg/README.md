# 准备礼物 · SVG角色动画小样

10秒独立候选，固定1280×720/30fps镜位。背景、角色、纸上笔迹都是分层SVG；头部、眼睛、嘴、手臂和两支手持蜡笔由视频帧确定性驱动，没有整张插画的平移缩放。

## 运行

在本目录执行：

```sh
npm ci
node render.mjs --stills
node render.mjs
```

需要Node.js 20、Python 3、FFmpeg/ffprobe和Chrome。默认使用系统Google Chrome；其它兼容Chrome路径可通过 `REMOTION_BROWSER_EXECUTABLE` 指定。

正式输出位于仓库 `materials/final/gift/待确认成片/SVG_Remotion_佩奇画画_20261015`。渲染浏览器在finally关闭；正常导出后删除根目录 `TMP to delete - SVG小样`。质检模式保留标记临时帧用于查看，完成后手动清理。

## 源码

- `src/Scene.tsx`：矢量角色、固定厨房、道具和动作。`SceneArtwork`可直接输出SVG，`DrawingScene`接入Remotion帧。
- `src/speech.json`：从原配音生成的300帧短窗RMS门控，可由下列脚本重新生成。
- `prepare.py`：检查GIFT-L028/L029的SHA，计算增益、口型门控和完整音轨安排。
- `render.mjs`：Remotion离线渲染、原WAV配音合成、PNG与可编辑SVG导出。
- `validate.py`：核验实际MP4的完整解码、300帧连续时序，以及两句完整原WAV在指定时间的波形相关性。渲染后自动执行。

声音先在Python中合成为固定480000帧的48k双声道PCM，再使用Remotion自带FFmpeg编码和封装；不使用无限补静音滤镜。只在本次子进程中设置自带库路径，不修改系统FFmpeg或全局环境。

原WAV只引用、不复制。两句对白原速完整保留，画画与拿笔使用同一物件坐标；非说话角色保持微笑闭口。RMS门控用于基础口型开合，不等于逐音素对口型。

当前只是动作与造型候选。人物形状和动作自然程度仍待用户观看确认；现有网站、已采纳片段及原插图不受此项目影响。
