# 星轨科技门户迁移至SSG+对象存储需求 (v3.0)
## 1. 架构变更
- 前端迁移至静态站点生成器(SSG)，部署至OSS存储桶 `starorbit-portal-prod`。
- 启用CDN，边缘节点缓存策略：HTML文件 `max-age=0, must-revalidate`，静态资源(js/css/images) `max-age=31536000, immutable`。
- WAF需拦截User-Agent包含 `BadBot` 或 `Scraper` 的请求，返回403。

## 2. 数据与路径映射
- 旧版 `/uploads/` 目录需全量同步至OSS `/assets/uploads/`。
- 旧版 `/docs/secure/` 目录下的文件不迁移，保留在旧系统MySQL中，通过旧系统API动态获取。
- 数据库仅保留用户表和文章表，迁移至新MySQL集群。

## 3. 验收标准
- 验证CDN缓存头是否正确。
- 验证WAF拦截是否生效。
- 验证OSS路径映射是否正确，特别是 `/assets/uploads/` 的访问。