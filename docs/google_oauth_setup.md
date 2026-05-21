# Google OAuth 配置说明

## 1. 创建 Google Cloud 项目

进入 Google Cloud Console，创建或选择一个项目。

## 2. 配置 OAuth consent screen

应用类型选择 External，测试阶段把自己的 Gmail 加入 Test users。

## 3. 启用 Gmail API

在 APIs & Services 中启用 Gmail API。

如果要使用第六阶段日程能力，还需要启用 Google Calendar API。

## 4. 创建 OAuth Client

类型选择 Web application，添加回调地址：

```text
http://localhost:8000/gmail/auth/callback
```

## 5. 放置 JSON 文件

下载 OAuth Client JSON 后重命名并放到：

```text
secrets/google_oauth_client.json
```

后端默认通过 `GOOGLE_OAUTH_CLIENT_FILE="../secrets/google_oauth_client.json"` 读取它。

当前 OAuth 回调地址通过 `GOOGLE_REDIRECT_URI` 指定：

```text
GOOGLE_REDIRECT_URI="http://localhost:8000/gmail/auth/callback"
```

## 6. 当前申请的 scope

```text
openid
https://www.googleapis.com/auth/userinfo.email
https://www.googleapis.com/auth/userinfo.profile
https://www.googleapis.com/auth/gmail.readonly
https://www.googleapis.com/auth/gmail.compose
https://www.googleapis.com/auth/gmail.send
https://www.googleapis.com/auth/gmail.modify
https://www.googleapis.com/auth/calendar.readonly
https://www.googleapis.com/auth/calendar.events
```

这些 scope 与新版开发路线保持一致：前八阶段已经使用 Gmail 读取、草稿创建、Calendar 读取和日程创建；第九、十阶段会继续使用 `gmail.modify` 和 `gmail.send` 实现标签修改、归档、发送等能力。即使具备发送或修改权限，系统仍通过 Pending Actions 做二次确认，不会自动发送或修改邮件。
