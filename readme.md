# MailFlow Agent

MailFlow Agent 是一个基于 FastAPI + LangGraph + Vue 的多 Agent 邮件与日程助理系统。

当前已完成开发文档中的：

- 第一阶段：FastAPI 后端、Vue 3 + TypeScript + Vite 前端、基础布局、路由、`/health`、Swagger 文档；
- 第二阶段：Google OAuth 登录回调、token 加密保存、Gmail 最近邮件读取、Settings 连接状态、Inbox 邮件列表。

## OAuth JSON 放在哪里

Google Cloud Console 下载的 OAuth Client JSON 请放在项目根目录：

```text
secrets/google_oauth_client.json
```

该目录已加入 `.gitignore`，不要提交到 Git。

Google Cloud Console 中的 Authorized redirect URI 配置为：

```text
http://localhost:8000/gmail/auth/callback
```

## 后端启动

当前项目已改为使用项目根目录下的 `.venv`，后续不要依赖 conda 的 `mailflow-agent` 环境。

```powershell
Copy-Item backend/.env.example backend/.env
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

打开：

```text
http://localhost:8000/docs
http://localhost:8000/health
```

## 前端启动

```powershell
cd frontend
npm install
npm run dev
```

打开：

```text
http://localhost:5173
```

## PostgreSQL / Redis

第一二阶段默认使用 SQLite，便于本地直接启动。若要按企业化环境切换 PostgreSQL / Redis：

```powershell
docker compose up -d
```

然后把 `backend/.env` 中的 `DATABASE_URL` 改为：

```text
postgresql+psycopg://mailflow:mailflow@localhost:5432/mailflow_agent
```

## 第二阶段使用流程

1. 启动后端和前端；
2. 将 OAuth JSON 放入 `secrets/google_oauth_client.json`；
3. 进入 `Settings`，点击“连接 Google 账号”；
4. 授权完成后回到前端；
5. 进入 `Inbox`，点击“同步邮件”查看 Gmail 最近邮件。
