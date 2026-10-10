# 03：让字牌文字与玻璃共享排序 · 图2

对应[说明文档](../../docs/rendering-guide/03-sign-order.md)。箭头表示步骤或依赖，具体读法见正文。

```mermaid
flowchart TD
  Far["远处红玻璃"] --> Text["中间字牌文字"]
  Text --> Near["近处蓝玻璃"]
  Text --> Material["使用文字自身材质"]
  Text --> Ignore["文字不独立响应点选"]
  Ignore --> Block["选择实际方块表面"]
```
