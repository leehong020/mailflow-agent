# Google OAuth 配置说明

## 1. 创建 Google Cloud 项目

进入 Google Cloud Console，创建或选择一个项目。

## 2. 配置 OAuth consent screen

应用类型选择 External，测试阶段把自己的 Gmail 加入 Test users。

## 3. 启用 Gmail API

在 APIs & Services 中启用 Gmail API。

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
```

当前阶段只读取 Gmail，不申请发送、删除、修改邮件权限。
