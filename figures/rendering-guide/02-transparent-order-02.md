# 02：让半透明表面按远近排队 · 图2

对应[说明文档](../../docs/rendering-guide/02-transparent-order.md)。箭头表示步骤或依赖，具体读法见正文。

```mermaid
flowchart TD
  Data["固定的两块玻璃顶点"] --> ViewA["从正面看"]
  Data --> ViewB["从背面看"]
  ViewA --> ListA["红远蓝近"]
  ViewB --> ListB["蓝远红近"]
  ListA --> DrawA["先红后蓝"]
  ListB --> DrawB["先蓝后红"]
  Offscreen["视野外的部件"] --> Skip["本次索引不绘制"]
```
