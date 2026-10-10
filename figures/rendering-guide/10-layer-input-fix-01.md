# 10：先保存输入值，再同步控件 · 图1

对应[说明文档](../../docs/rendering-guide/10-layer-input-fix.md)。箭头表示步骤或依赖，具体读法见正文。

```mermaid
flowchart LR
  OldInput["原来：用户输入二十"] --> OldStop["先停止并同步"]
  OldStop --> OldRead["读到旧值三十九"]
  OldRead --> Noop["目标未变不切层"]
  NewInput["现在：用户输入二十"] --> Save["先保存二十"]
  Save --> NewStop["再停止并同步"]
  NewStop --> Seek["用保存值切到二十"]
```
