# my-project · 运维管理系统

这是一个已经开始成型的 **Python + FastAPI 运维管理系统**。

## 现在已经有的能力

- 登录页
- 简单的 Cookie 登录流程
- 后台首页仪表盘
- 资产管理、告警中心、工单系统、审计建议区块
- 基础 API 骨架

## 演示账号

- 账号：`admin`
- 密码：`admin123`

## 本地启动

```bash
cd ~/.openclaw/my-project

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

打开：
- 登录页: http://localhost:8000/login
- 系统首页: http://localhost:8000/
- API 文档: http://localhost:8000/docs

## 当前阶段说明

这是一版可继续演进的第一阶段系统：
- 页面已经有了
- 登录流程已经有了
- 业务数据目前还是演示数据
- 还没有接数据库和真实用户体系

## 我建议的下一步

1. 把登录改成数据库用户表
2. 先接 SQLite，后面再切 PostgreSQL
3. 先完成资产管理 CRUD 页面
4. 再补菜单详情页、权限、审计日志

## 建议开发顺序

- 第一步：用户登录 + 首页
- 第二步：资产管理
- 第三步：工单系统
- 第四步：告警中心
- 第五步：权限和审计
