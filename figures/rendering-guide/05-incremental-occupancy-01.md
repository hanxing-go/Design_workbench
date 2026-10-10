# 05：只更新发生变化的位置索引 · 图1

对应[说明文档](../../docs/rendering-guide/05-incremental-occupancy.md)。箭头表示步骤或依赖，具体读法见正文。

```mermaid
flowchart LR
  OldEdit["原来：局部变化"] --> OldScan["扫描全部方块"]
  OldScan --> OldMap["重新建立位置表"]
  NewEdit["现在：局部变化"] --> Remove["删除变化分块旧记录"]
  Remove --> Insert["写入该分块新记录"]
  Insert --> Reuse["继续复用完整位置表"]
```
