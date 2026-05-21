# A股每日复盘看板

本目录是一个静态网站，用来展示每日 A 股涨停复盘报告。

## 文件结构

- `index.html`：看板页面
- `styles.css`：页面样式
- `app.js`：读取数据并渲染页面
- `data/reports.json`：日报数据源，最新报告排在数组第一项
- `reports/`：PDF 报告归档

## 每日更新方式

每天收盘后的自动化任务需要：

1. 抓取并核验当天涨停池日期。
2. 生成当天中文复盘报告。
3. 将结构化数据追加到 `data/reports.json` 的 `reports` 数组开头。
4. 若生成 PDF，则放入 `reports/YYYY-MM-DD.pdf`，并在报告对象的 `pdf` 字段引用它。
5. 更新 `updatedAt`。

本网站是纯静态页面，可用任意静态服务器打开，也可以部署到 GitHub Pages、Nginx 或对象存储静态站点。
