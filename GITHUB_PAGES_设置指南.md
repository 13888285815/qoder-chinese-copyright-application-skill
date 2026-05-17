# GitHub Pages 设置指南

## 目标
将项目部署到 GitHub Pages，实现远程共享演示访问。

## 当前状态
- ✅ 已创建 `gh-pages` 分支
- ✅ 已添加静态演示页面 `index.html`
- ✅ 已推送到 GitHub 远程仓库

## 需要在 GitHub 上完成的操作

### 方法一：通过 GitHub 网页设置（推荐）

1. **登录 GitHub**，访问项目仓库：
   https://github.com/13888285815/qoder-chinese-copyright-application-skill

2. **进入设置页面**：
   - 点击仓库顶部的 `Settings`（设置）选项卡

3. **启用 GitHub Pages**：
   - 在左侧菜单找到 `Pages`（页面）
   - 在 `Build and deployment`（构建和部署）部分：
     - `Source`（来源）：选择 `Deploy from a branch`（从分支部署）
     - `Branch`（分支）：选择 `gh-pages` 分支和 `/ (root)` 目录
     - 点击 `Save`（保存）

4. **等待部署完成**：
   - GitHub 会自动构建和部署
   - 通常在 1-2 分钟内完成
   - 部署完成后，会显示访问链接

5. **访问演示页面**：
   - 链接格式：`https://<用户名>.github.io/<仓库名>/`
   - 例如：`https://13888285815.github.io/qoder-chinese-copyright-application-skill/`

---

### 方法二：通过命令行创建（备用）

如果网页设置不可用，可以通过以下步骤：

```bash
# 确保在 gh-pages 分支
git checkout gh-pages

# 创建 .nojekyll 文件（避免 Jekyll 处理）
touch .nojekyll

# 提交并推送
git add .nojekyll
git commit -m "docs: 添加 .nojekyll 文件以禁用 Jekyll"
git push origin gh-pages
```

然后在 GitHub 设置中启用 Pages。

---

## 验证部署成功

1. 访问：`https://13888285815.github.io/qoder-chinese-copyright-application-skill/`
2. 应该看到静态演示页面
3. 页面包含：
   - 项目标题和简介
   - 功能列表
   - 使用说明
   - GitHub 仓库链接

---

## 注意事项

1. **这是静态演示页面**，不是完整的 Flask 应用
   - 静态页面仅用于展示项目功能
   - 完整功能需要本地部署 Flask 服务

2. **如果需要动态演示**，可以考虑：
   - 部署到 Vercel（支持 Python 应用）
   - 部署到 Heroku（需要信用卡验证）
   - 部署到 Railway（有免费额度）
   - 使用云服务（阿里云、腾讯云等）

3. **本地部署 fastest way**：
   ```bash
   git clone https://github.com/13888285815/qoder-chinese-copyright-application-skill.git
   cd qoder-chinese-copyright-application-skill/web
   pip install -r requirements.txt
   python3 app.py
   # 访问 <INTERNAL_URL_REDACTED>
   ```

---

## 下一步

1. ✅ **完成**：创建静态演示页面
2. ✅ **完成**：推送到 `gh-pages` 分支
3. ⚠️ **待完成**：在 GitHub 网页上启用 Pages 功能
4. ⚠️ **待验证**：访问演示页面确认部署成功

---

## 快速访问链接（部署成功后）

- **GitHub Pages 演示**：https://13888285815.github.io/qoder-chinese-copyright-application-skill/
- **GitHub 仓库**：https://github.com/13888285815/qoder-chinese-copyright-application-skill
- **本地演示**（需要启动服务）：<INTERNAL_URL_REDACTED>

---

## 常见问题

### Q1: 为什么不使用 `main` 分支？
A: `main` 分支包含完整的 Flask 应用代码，不适合直接作为 GitHub Pages 源。使用独立的 `gh-pages` 分支可以避免冲突。

### Q2: 能否直接部署 Flask 应用？
A: GitHub Pages 仅支持静态文件。要部署动态应用，请使用 Vercel、Heroku 等平台。

### Q3: 如何更新演示页面？
A: 在 `gh-pages` 分支修改 `index.html`，然后推送即可自动更新。

---

**最后更新**：2026-05-17
**作者**：云南意念科技有限公司
