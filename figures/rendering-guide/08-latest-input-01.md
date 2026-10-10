# 08：连续切层时使用最新目标 · 图1

对应[说明文档](../../docs/rendering-guide/08-latest-input.md)。箭头表示步骤或依赖，具体读法见正文。

```mermaid
flowchart LR
  OldInputs["原来：连续多个高度"] --> OldJobs["逐次执行旧目标"]
  OldJobs --> OldRepeat["重复构建过渡画面"]
  NewInputs["现在：连续多个高度"] --> Target["不断更新当前目标"]
  Target --> Set["分块编号合并去重"]
  Set --> Build["执行时读取最新高度"]
```
