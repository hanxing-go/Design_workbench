# 07：把几何重建分散到多帧 · 图1

对应[说明文档](../../docs/rendering-guide/07-frame-budget.md)。箭头表示步骤或依赖，具体读法见正文。

```mermaid
flowchart LR
  OldQueue["原来：大量待建分块"] --> OldWork["连续重建到结束"]
  OldWork --> OldUI["页面长时间等待"]
  NewQueue["现在：大量待建分块"] --> Budget["按预算处理一批"]
  Budget --> Frame["交回浏览器并请求绘制"]
  Frame --> Remaining["下一轮处理剩余分块"]
  Remaining --> Budget
```
