# 06：切层时只重建相关高度的分块 · 图1

对应[说明文档](../../docs/rendering-guide/06-local-layer-cut.md)。箭头表示步骤或依赖，具体读法见正文。

```mermaid
flowchart LR
  OldInput["原来：改变切层"] --> OldAll["广泛重建场景"]
  OldAll --> OldResult["等待全部工作"]
  NewInput["现在：改变切层"] --> Range["计算旧新高度范围"]
  Range --> Select["只安排相交分块"]
  Select --> Reuse["其余几何继续复用"]
```
