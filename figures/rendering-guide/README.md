# 渲染优化图示源文件

每张图保留 Mermaid 源码（`.mmd`）、预览包装（`.md`）和已经导出的图片（`.png`）。正文位于 [图解目录](../../docs/rendering-guide/README.md)，无需安装工具即可阅读图片。

修改图示时请同步源码和包装文件，并使用 Mermaid CLI 渲染与检查。例如：

```powershell
npx.cmd -y @mermaid-js/mermaid-cli@11.12.0 -i figures/rendering-guide/01-opaque-batching-01.mmd -o figures/rendering-guide/01-opaque-batching-01.png -b white
```

`manifest.json` 保存文档、图号和源码哈希。图示是流程示意，不是按比例绘制的游戏画面或性能曲线。
