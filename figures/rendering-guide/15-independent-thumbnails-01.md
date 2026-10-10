# 15｜独立缩略图：小照片有自己的摄影棚 · 图1

对应[说明文档](../../docs/rendering-guide/15-independent-thumbnails.md)。箭头表示步骤或依赖，具体读法见正文。

```mermaid
flowchart LR
    oldTask["以前：拍小图"] --> oldResize["缩小主画布"]
    oldResize --> oldPhoto["绘制并取图片"]
    oldPhoto --> oldRestore["恢复主画布<br/>重画建筑"]
    newTask["现在：拍小图"] --> newLookup{"已有图片？"}
    newLookup -->|"有"| newReuse["直接使用图片"]
    newLookup -->|"无"| newPhoto["专用小画布<br/>绘制并缓存"]
```
