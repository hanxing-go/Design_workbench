# 赞助页维护

赞助页入口为 `/?view=sponsor`，首页导航与页脚提供入口。页面沿用 Minecraft 深色像素主题，说明项目维护方向、自愿赞助原则、非金钱支持方式和常见问题。

## 配置真实赞助渠道

编辑 `frontend/src/sponsor.config.ts` 的 `channels` 数组，只填写维护者提供的实际赞助渠道。未配置时，页面显示“赞助通道正在准备中”，并提供真实 GitHub 仓库入口。不会猜测赞助账号或生成收款码。

每个渠道包含以下字段：

| 字段 | 用途 |
| --- | --- |
| `id` | 唯一渠道名称，例如 `afdian`、`wechat` |
| `name` | 页面显示的渠道名称 |
| `description` | 渠道的简短介绍 |
| `icon` | `emerald`、`diamond`、`qr` 或 `github` |
| `url` | 维护者确认的 HTTPS 赞助页面；配置后打开该页面 |
| `qrImage` | 实际收款码图片的打包 URL；未配置链接时，按钮打开收款码弹窗 |
| `recipient` | 可选的收款方名称，显示在二维码下方 |

爱发电、GitHub Sponsors 等页面使用 `url`。微信或支付宝使用实际收款码：把图片保存在 `frontend/src/assets/sponsor/`，在配置文件中导入图片，将导入值赋给 `qrImage`。图片需由维护者提供，不使用示意二维码代替。

配置后执行 `npm.cmd run check --prefix frontend` 和 `npm.cmd run build --prefix frontend`，同步更新随包静态页面。此页面只展示赞助渠道，不创建支付订单、订阅或到账记录。
