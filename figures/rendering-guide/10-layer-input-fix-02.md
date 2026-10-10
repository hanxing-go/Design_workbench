# 10：先保存输入值，再同步控件 · 图2

对应[说明文档](../../docs/rendering-guide/10-layer-input-fix.md)。箭头表示步骤或依赖，具体读法见正文。

```mermaid
flowchart TD
  Input["最低高度负四<br/>输入第三层"] --> Capture["先保存数字三"]
  Capture --> Stop["停止播放并同步显示"]
  Stop --> Valid["检查保存值有效"]
  Valid --> Convert["换算世界高度负二"]
  Convert --> Clamp["限制到建筑高度范围"]
  Clamp --> Layer["设置实际目标层"]
  Layer --> Sync["显示与新目标一致"]
```
