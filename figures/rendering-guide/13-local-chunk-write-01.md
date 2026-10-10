# 13 · 保存局部修改时，直接寻找附近坐标 · 图1

对应[说明文档](../../docs/rendering-guide/13-local-chunk-write.md)。箭头表示步骤或依赖，具体读法见正文。

```mermaid
flowchart LR
    oldEdit["以前<br/>修改少量分块"] --> oldScan["遍历全建筑<br/>筛出目标块的方块"]
    oldScan --> oldEncode["编码目标分块"]
    oldEncode --> oldWrite["写入目标分块"]
    newEdit["现在<br/>修改少量分块"] --> newLookup["遍历目标块坐标<br/>直接查询方块"]
    newLookup --> newEncode["编码目标分块"]
    newEncode --> newWrite["写入目标分块"]
```
