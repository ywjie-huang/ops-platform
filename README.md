# my-project · 运维管理系统

基于 **Python + FastAPI** 构建的运维管理系统骨架。

## 模块

| 模块 | 路由前缀 | 说明 |
|------|----------|------|
| 资产管理 | `/api/v1/assets` | 服务器、容器、域名、证书 |
| 监控面板 | _(待扩展)_ | 主机状态、资源趋势 |
| 告警中心 | `/api/v1/alerts` | 告警聚合与分派 |
| 变更发布 | _(待扩展)_ | 发布计划与回滚 |
| 工单协作 | `/api/v1/tickets` | 工单创建与跟踪 |
| 审计日志 | `/api/v1/audit/logs` | 操作审计 |

## 快速启动

```bash
cd ~/.openclaw/my-project

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动开发服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

访问 API 文档：http://localhost:8000/docs

## 下一步

1. 配置 PostgreSQL，修改 `app/db/database.py` 中的 `DATABASE_URL`
2. 运行 `alembic init alembic` 初始化数据库迁移
3. 补全各模块的数据库 CRUD 操作
4. 接入登录鉴权（JWT）
