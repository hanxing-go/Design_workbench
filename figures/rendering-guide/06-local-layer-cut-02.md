# 06：切层时只重建相关高度的分块 · 图2

对应[说明文档](../../docs/rendering-guide/06-local-layer-cut.md)。箭头表示步骤或依赖，具体读法见正文。

```mermaid
flowchart TD
  Cut["切层十六到十五"] --> Range["检查十五至十六"]
  Range --> Lower["下带零至十五"]
  Range --> Upper["上带十六至三十一"]
  Lower --> Reveal["补出十五层顶面"]
  Upper --> Hide["隐藏十六层及以上"]
  Unrelated["无关高度分块"] --> Keep["复用已有几何"]
```
