# 00：屏幕里的建筑是怎样画出来的 · 图3

对应[说明文档](../../docs/rendering-guide/00-start-here.md)。箭头表示步骤或依赖，具体读法见正文。

```mermaid
flowchart TD
    largeScene["十万方块场景"] --> commands["问题一<br/>每帧提交大量<br/>小绘制命令"]
    largeScene --> rebuild["问题二<br/>一次连续做完<br/>大量网格重建"]
    largeScene --> repeatedRead["问题三<br/>数据没变仍重复<br/>读取与计算"]
    commands --> batching["对应办法<br/>合批、透明索引排序"]
    rebuild --> scheduling["对应办法<br/>分帧、合并输入<br/>复用网格"]
    repeatedRead --> cache["对应办法<br/>缓存、增量解码<br/>缩小比较范围"]
```
