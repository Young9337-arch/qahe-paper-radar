# QAHE Paper Radar

零成本、每日更新的量子反常霍尔效应论文聚合与材料体系分类网站。数据来自 arXiv 和 Crossref，前端是 Next.js 14 静态导出。

## 本地运行

```bash
python -m pip install -r requirements.txt
python scripts/update_papers.py
npm install
npm run dev
```

抓取脚本遇到单个来源或图片提取失败时会降级继续。设置 `CONTACT_EMAIL` 环境变量可让 Crossref 正确识别 API 客户端。

## 部署

1. 推送至 GitHub 仓库的 `main` 分支。
2. 在仓库 Settings → Pages 中将 Source 设为 **GitHub Actions**。
3. 可在 Settings → Secrets and variables → Actions → Variables 添加 `CONTACT_EMAIL`。

工作流每天北京时间 09:17 抓取、提交 JSON、构建并部署。也可在 Actions 页面手动运行。Vercel 导入仓库后同样可直接构建；若只用 Vercel，可保留定时数据更新并移除 Pages 部署步骤。

## 数据说明

Crossref 查询最近 7 天，arXiv 查询最近 30 天，结果会与历史数据按 arXiv ID / DOI 合并。自动分类按 `scripts/update_papers.py` 中的 taxonomy 顺序匹配，未命中项进入 `Other_New_Materials`。
