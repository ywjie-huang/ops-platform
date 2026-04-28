# my-project · 运维管理系统

这是一个已经能实际使用的 **Python + FastAPI 运维管理系统第一版**。

## 当前已经实现

- 登录页
- 基于 SQLite 的真实用户表
- 基于数据库校验的登录流程
- 后台首页仪表盘
- 资产管理页面
- 资产新增、编辑、删除
- 用户管理页面
- 用户新增、编辑、删除
- 自动初始化默认管理员和示例资产
- 使用更稳的 `pbkdf2_sha256` 密码哈希方案，避免部分 Windows/bcrypt 环境兼容问题

## 默认登录账号

- 账号：`admin`
- 密码：`admin123`

> 首次启动会自动创建 SQLite 数据库和默认管理员。

## 项目结构

- `app/static`：CSS、图片等静态资源
- `app/templates`：Jinja2 页面模板
- `app/db`：数据库连接与初始化
- `app/models`：SQLAlchemy 数据模型
- `app/routes_auth.py`：登录相关路由
- `app/routes_pages.py`：后台页面与资产 CRUD 页面

## 本地启动

```bash
cd ~/.openclaw/my-project

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Windows PowerShell 可用：

```powershell
cd D:\openclaw\config\my-project
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

打开：
- 登录页：`http://localhost:8000/login`
- 首页：`http://localhost:8000/`
- API 文档：`http://localhost:8000/docs`

## 数据文件

SQLite 数据库默认在：

- `data/ops.db`

## 下一步建议

1. 补权限控制和角色
2. 增加工单、告警、审计真实数据表
3. 接入 Alembic 做数据库迁移
4. 后续切 PostgreSQL
5. 增加分页、搜索、筛选
