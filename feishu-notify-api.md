# 飞书通知 API 文档

## 目录

- [接口总览](#接口总览)
- [认证说明](#认证说明)
- [发送卡片接口](#发送卡片接口)
- [更新卡片接口](#更新卡片接口)
- [通知记录管理接口](#通知记录管理接口)
- [API 调用示例](#api-调用示例)
- [数据库记录](#数据库记录)
- [相关文件](#相关文件)

## 接口总览

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 发送卡片 | `POST` | `/api/v1/feishu/notify` | 向个人或群聊发送飞书互动卡片 |
| 按消息ID更新卡片 | `PATCH` | `/api/v1/feishu/notify/{message_id}` | 通过飞书消息 ID 更新已发送的卡片内容 |
| 按自定义标识更新卡片 | `PATCH` | `/api/v1/feishu/notify-by-open-id/{open_message_id}` | 通过自定义消息标识更新已发送的卡片内容 |
| 查询通知记录列表 | `GET` | `/api/v1/notification-records` | 分页查询通知记录，支持筛选 |
| 查询通知记录详情 | `GET` | `/api/v1/notification-records/{id}` | 获取单条通知记录详情 |
| 删除通知记录 | `DELETE` | `/api/v1/notification-records/{id}` | 删除指定通知记录 |

**认证方式**：所有接口需要 Bearer Token 认证（`Authorization: Bearer <token>`）

**内容类型**：`application/json`

## 认证说明

本 API 使用 JWT Bearer Token 进行认证。

### 获取 Token

#### `POST /api/v1/auth/login`

用户登录获取访问令牌。

**请求体：**

```json
{
  "username": "string",
  "password": "string"
}
```

**成功响应 (200 OK)：**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400,
  "permissions": ["*"],
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@example.com",
    "full_name": "管理员",
    "is_active": true,
    "is_superuser": true,
    "last_login": "2024-01-01T00:00:00Z",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z",
    "permissions": ["*"],
    "roles": [{"id": 1, "name": "超级管理员"}]
  }
}
```

**登录失败响应 (401 Unauthorized)：**

```json
{
  "detail": "用户名或密码错误"
}
```

#### cURL 登录示例

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "your_password"
  }'
```

### 使用 Token

获取 Token 后，在请求头中添加 `Authorization: Bearer <your_token>`

```bash
curl -X POST "http://localhost:8000/api/v1/feishu/notify" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "card_content": {...},
    "user": "zhangsan"
  }'
```

### Token 刷新

#### `POST /api/v1/auth/refresh`

使用 Refresh Token 获取新的访问令牌。

**请求体：**

```
refresh_token: string
```

**成功响应 (200 OK)：**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

### 获取当前用户信息

#### `GET /api/v1/auth/me`

获取当前认证用户的信息。

**请求头：**

```
Authorization: Bearer <your_token>
```

**成功响应 (200 OK)：**

```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@example.com",
  "full_name": "管理员",
  "is_active": true,
  "is_superuser": true,
  "last_login": "2024-01-01T00:00:00Z",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z",
  "permissions": ["*"]
}
```

## 功能说明

向指定用户或群聊发送飞书互动卡片消息。

### 处理流程

**发送给个人（提供 `user`）：**
1. 根据 `user` 字段匹配 `user` 表的 `username` 或 `full_name`
2. 获取匹配用户的 `feishu_open_id`
3. 通过飞书 API 发送互动卡片（`receive_id_type="open_id"`）
4. 所有调用记录存储到 `notification_records` 表

**发送到群聊（提供 `chat_id`）：**
1. 直接使用 `chat_id` 作为接收者 ID
2. 通过飞书 API 发送互动卡片（`receive_id_type="chat_id"`）
3. 所有调用记录存储到 `notification_records` 表

> **注意**：`user` 和 `chat_id` 必须提供其中一个，且不能同时提供。

### 用户匹配逻辑

1. 优先按 `username` 精确匹配
2. 若未匹配到，则按 `full_name` 匹配（仅匹配 `feishu_open_id` 不为空的用户）

## 发送卡片接口

### `POST /api/v1/feishu/notify`

发送飞书互动卡片通知。

#### 请求参数

**请求体 (Request Body)：**

```json
{
  "card_content": { ... },
  "user": "string | null",
  "chat_id": "string | null",
  "callback_id": "string | null",
  "open_message_id": "string | null"
}
```

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `card_content` | `dict[str, Any]` | **是** | 飞书卡片 JSON 内容 |
| `user` | `string \| null` | 条件必填 | 要匹配的用户标识，可以是 `username` 或 `full_name`（与 `chat_id` 二选一） |
| `chat_id` | `string \| null` | 条件必填 | 飞书群聊 ID，如 `oc_cb42cb69eb9703e4cb284b516272c920`（与 `user` 二选一） |
| `callback_id` | `string \| null` | 否 | 业务回调标识，用于后续卡片更新时验证归属 |
| `open_message_id` | `string \| null` | 否 | 自定义消息标识，用于后续按此标识更新卡片（无需记住飞书返回的 `message_id`） |

> **关于 `open_message_id`**：发送卡片时飞书会返回一个 `message_id`（如 `om_xxxxx`），后续更新卡片需要使用该 ID。如果发送时指定了 `open_message_id`，则后续可以通过 `PATCH /notify-by-open-id/{open_message_id}` 更新卡片，无需记住飞书的 `message_id`。

#### card_content 格式示例

```python
card_content = {
    "schema": "2.0",
    "header": {
        "title": {"tag": "plain_text", "content": "告警通知"},
        "template": "red"
    },
    "body": {
        "elements": [
            {"tag": "markdown", "content": "**服务器 CPU 使用率过高**"},
            {"tag": "div", "text": {"tag": "lark_md", "content": "实例: `192.168.1.100`"}},
            {"tag": "div", "text": {"tag": "lark_md", "content": "告警级别: **严重**"}}
        ]
    }
}
```

更多卡片格式参考 [飞书卡片开发文档](https://open.feishu.cn/document/uAjLw4CM/ukzMukzMukzM/feishu-cards/card-components/interactive-components/button)

#### 成功响应 (200 OK)

```json
{
  "success": true,
  "message_id": "om_xxxxx",
  "matched_user": "zhangsan",
  "chat_id": null,
  "callback_id": "alert_123",
  "open_message_id": "my_custom_id",
  "error": null
}
```

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `success` | `boolean` | 发送是否成功 |
| `message_id` | `string \| null` | 飞书返回的消息 ID（用于按 message_id 更新卡片） |
| `matched_user` | `string \| null` | 匹配到的用户名（发送到群聊时为 null） |
| `chat_id` | `string \| null` | 群聊 ID（发送给个人时为 null） |
| `callback_id` | `string \| null` | 业务回调标识 |
| `open_message_id` | `string \| null` | 自定义消息标识（发送时传入的值） |
| `error` | `string \| null` | 错误信息（成功时为 null） |

#### 失败响应

| HTTP 状态码 | 说明 | 示例 |
|-------------|------|------|
| `400 Bad Request` | 参数校验失败（如 `user` 和 `chat_id` 均未提供或同时提供） | `{"detail": "user 和 chat_id 必须提供其中一个"}` |
| `400 Bad Request` | 用户无 `feishu_open_id` | `{"detail": "User zhangsan does not have a feishu_open_id"}` |
| `404 Not Found` | 未找到匹配的用户 | `{"detail": "User not found"}` |
| `401 Unauthorized` | 未认证 | - |
| `500 Internal Server Error` | 服务器内部错误 | - |

## 更新卡片接口

提供两种方式更新已发送的飞书卡片，底层均调用飞书 `im.v1.message.patch` API 实现原地更新（非发送新卡片）。

### 方式一：按飞书消息 ID 更新

#### `PATCH /api/v1/feishu/notify/{message_id}`

通过发送卡片时飞书返回的 `message_id` 更新卡片。

#### 请求参数

**路径参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `message_id` | `string` | 飞书消息 ID（从发送响应的 `message_id` 字段获取，如 `om_xxxxx`） |

**请求体 (Request Body)：**

```json
{
  "card_content": { ... },
  "callback_id": "string | null"
}
```

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `card_content` | `dict[str, Any]` | **是** | 更新后的飞书卡片 JSON 内容 |
| `callback_id` | `string \| null` | 否 | 业务回调标识，用于验证卡片归属（如提供，必须与发送时一致） |

#### 成功响应 (200 OK)

```json
{
  "success": true,
  "message_id": "om_xxxxx",
  "error": null
}
```

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `success` | `boolean` | 更新是否成功 |
| `message_id` | `string \| null` | 飞书消息 ID |
| `error` | `string \| null` | 错误信息（成功时为 null） |

#### 失败响应

| HTTP 状态码 | 说明 | 示例 |
|-------------|------|------|
| `403 Forbidden` | callback_id 不匹配 | `{"detail": "callback_id does not match"}` |
| `404 Not Found` | 未找到对应的通知记录 | `{"detail": "Notification record not found"}` |
| `401 Unauthorized` | 未认证 | - |
| `500 Internal Server Error` | 服务器内部错误 | - |

---

### 方式二：按自定义消息标识更新

#### `PATCH /api/v1/feishu/notify-by-open-id/{open_message_id}`

通过发送卡片时指定的 `open_message_id` 更新卡片。适用于不想维护飞书 `message_id` 的场景。

#### 请求参数

**路径参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `open_message_id` | `string` | 自定义消息标识（发送时通过 `open_message_id` 字段指定的值） |

**请求体 (Request Body)：**

```json
{
  "card_content": { ... },
  "callback_id": "string | null"
}
```

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `card_content` | `dict[str, Any]` | **是** | 更新后的飞书卡片 JSON 内容 |
| `callback_id` | `string \| null` | 否 | 业务回调标识，用于验证卡片归属（如提供，必须与发送时一致） |

#### 成功响应 (200 OK)

```json
{
  "success": true,
  "message_id": "om_xxxxx",
  "error": null
}
```

#### 失败响应

| HTTP 状态码 | 说明 | 示例 |
|-------------|------|------|
| `400 Bad Request` | 该记录无关联的飞书 message_id | `{"detail": "No Feishu message_id associated with this record"}` |
| `403 Forbidden` | callback_id 不匹配 | `{"detail": "callback_id does not match"}` |
| `404 Not Found` | 未找到对应的通知记录 | `{"detail": "Notification record not found by open_message_id"}` |
| `401 Unauthorized` | 未认证 | - |
| `500 Internal Server Error` | 服务器内部错误 | - |

---

### 更新卡片原理

更新卡片通过飞书 `im.v1.message.patch` API 实现，会**原地更新**已发送的卡片内容，而非发送新卡片。调用流程：

1. 根据路径参数查找 `notification_records` 表中的记录
2. 如提供 `callback_id`，验证与发送时记录的 `callback_id` 一致
3. 获取记录中存储的飞书 `message_id`
4. 调用飞书 `im.v1.message.patch` API 更新卡片内容
5. 更新数据库记录中的 `card_content`

> **注意**：只有 `msg_type="interactive"` 的卡片消息才支持更新，纯文本消息无法更新。

## 通知记录管理接口

### `GET /api/v1/notification-records`

分页查询通知记录列表，支持按用户和发送状态筛选。

#### 请求参数

**查询参数 (Query Parameters)：**

| 参数名 | 类型 | 必填 | 默认值 | 约束 | 说明 |
|--------|------|------|--------|------|------|
| `page` | `int` | 否 | `1` | `1 ~ 100` | 页码 |
| `page_size` | `int` | 否 | `10` | `10 ~ 100` | 每页条数 |
| `user` | `string` | 否 | - | - | 按用户名模糊筛选（ILIKE） |
| `success` | `boolean` | 否 | - | - | 按发送状态筛选（`true` 成功 / `false` 失败） |

#### 成功响应 (200 OK)

```json
{
  "total": 100,
  "items": [
    {
      "id": 1,
      "user": "张三",
      "matched_user": "zhangsan",
      "feishu_open_id": "ou_xxxxx",
      "chat_id": null,
      "receive_type": "open_id",
      "callback_id": "alert_123",
      "open_message_id": "my_custom_id",
      "card_content": { "schema": "2.0", ... },
      "message_id": "om_xxxxx",
      "success": true,
      "error": null,
      "created_at": "2026-05-11T10:00:00+08:00"
    }
  ]
}
```

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `total` | `int` | 符合筛选条件的总记录数 |
| `items` | `array` | 当前页的通知记录列表 |

**items 中每条记录的字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | `int` | 记录 ID |
| `user` | `string` | 请求传入的用户标识（群聊时为 `chat:<chat_id>`） |
| `matched_user` | `string \| null` | 实际匹配到的用户名 |
| `feishu_open_id` | `string \| null` | 飞书用户 Open ID |
| `chat_id` | `string \| null` | 飞书群聊 ID |
| `receive_type` | `string` | 接收类型：`open_id`（个人）或 `chat_id`（群聊） |
| `callback_id` | `string \| null` | 业务回调标识 |
| `open_message_id` | `string \| null` | 自定义消息标识 |
| `card_content` | `object \| null` | 卡片 JSON 内容 |
| `message_id` | `string \| null` | 飞书返回的消息 ID |
| `success` | `boolean` | 发送是否成功 |
| `error` | `string \| null` | 错误信息 |
| `created_at` | `datetime` | 创建时间 |

#### 请求示例

```bash
# 获取第一页（默认每页 10 条）
curl "http://localhost:8000/api/v1/notification-records" \
  -H "Authorization: Bearer <your_token>"

# 按用户模糊筛选
curl "http://localhost:8000/api/v1/notification-records?user=zhangsan" \
  -H "Authorization: Bearer <your_token>"

# 按发送状态筛选 + 自定义分页
curl "http://localhost:8000/api/v1/notification-records?success=true&page=2&page_size=20" \
  -H "Authorization: Bearer <your_token>"
```

---

### `GET /api/v1/notification-records/{id}`

获取单条通知记录详情。

#### 请求参数

**路径参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `id` | `int` | 通知记录 ID |

#### 成功响应 (200 OK)

```json
{
  "id": 1,
  "user": "张三",
  "matched_user": "zhangsan",
  "feishu_open_id": "ou_xxxxx",
  "chat_id": null,
  "receive_type": "open_id",
  "callback_id": "alert_123",
  "open_message_id": "my_custom_id",
  "card_content": { "schema": "2.0", ... },
  "message_id": "om_xxxxx",
  "success": true,
  "error": null,
  "created_at": "2026-05-11T10:00:00+08:00"
}
```

#### 失败响应

| HTTP 状态码 | 说明 | 示例 |
|-------------|------|------|
| `404 Not Found` | 记录不存在 | `{"detail": "Notification record not found"}` |

---

### `DELETE /api/v1/notification-records/{id}`

删除指定通知记录。

#### 请求参数

**路径参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `id` | `int` | 通知记录 ID |

#### 成功响应 (200 OK)

```json
{
  "message": "Notification record deleted successfully"
}
```

#### 失败响应

| HTTP 状态码 | 说明 | 示例 |
|-------------|------|------|
| `404 Not Found` | 记录不存在 | `{"detail": "Notification record not found"}` |

## API 调用示例

### 完整调用流程

#### 1. 登录获取 Token

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "your_password"
  }'
```

响应中的 `access_token` 即为认证 Token。

#### 2. 发送卡片给个人用户（带 callback_id 和 open_message_id）

```bash
curl -X POST "http://localhost:8000/api/v1/feishu/notify" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "card_content": {
      "schema": "2.0",
      "header": {
        "title": {"tag": "plain_text", "content": "告警通知"},
        "template": "red"
      },
      "body": {
        "elements": [
          {"tag": "markdown", "content": "**服务器 CPU 使用率过高**"},
          {"tag": "div", "text": {"tag": "lark_md", "content": "实例: `192.168.1.100`"}}
        ]
      }
    },
    "user": "zhangsan",
    "callback_id": "alert_123",
    "open_message_id": "alert_server_cpu"
  }'
```

#### 2b. 发送卡片到群聊

```bash
curl -X POST "http://localhost:8000/api/v1/feishu/notify" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "card_content": {
      "schema": "2.0",
      "header": {
        "title": {"tag": "plain_text", "content": "告警通知"},
        "template": "red"
      },
      "body": {
        "elements": [
          {"tag": "markdown", "content": "**服务器 CPU 使用率过高**"},
          {"tag": "div", "text": {"tag": "lark_md", "content": "实例: `192.168.1.100`"}}
        ]
      }
    },
    "chat_id": "oc_cb42cb69eb9703e4cb284b516272c920",
    "callback_id": "alert_456"
  }'
```

#### 3a. 按消息 ID 更新卡片

使用发送响应中返回的 `message_id`（如 `om_xxxxx`）更新卡片：

```bash
curl -X PATCH "http://localhost:8000/api/v1/feishu/notify/om_xxxxx" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "card_content": {
      "schema": "2.0",
      "header": {
        "title": {"tag": "plain_text", "content": "告警已解决"},
        "template": "green"
      },
      "body": {
        "elements": [
          {"tag": "markdown", "content": "**服务器 CPU 使用率已恢复正常**"}
        ]
      }
    },
    "callback_id": "alert_123"
  }'
```

#### 3b. 按自定义标识更新卡片

使用发送时指定的 `open_message_id`（如 `alert_server_cpu`）更新卡片，无需记住飞书返回的 `message_id`：

```bash
curl -X PATCH "http://localhost:8000/api/v1/feishu/notify-by-open-id/alert_server_cpu" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "card_content": {
      "schema": "2.0",
      "header": {
        "title": {"tag": "plain_text", "content": "告警已解决"},
        "template": "green"
      },
      "body": {
        "elements": [
          {"tag": "markdown", "content": "**服务器 CPU 使用率已恢复正常**"}
        ]
      }
    },
    "callback_id": "alert_123"
  }'
```

#### 4. 查询通知记录

```bash
# 查询所有记录
curl "http://localhost:8000/api/v1/notification-records" \
  -H "Authorization: Bearer <access_token>"

# 按用户筛选
curl "http://localhost:8000/api/v1/notification-records?user=zhangsan" \
  -H "Authorization: Bearer <access_token>"

# 按成功状态筛选
curl "http://localhost:8000/api/v1/notification-records?success=true" \
  -H "Authorization: Bearer <access_token>"
```

### Python 完整示例

```python
import requests

# 1. 登录获取 Token
login_url = "http://localhost:8000/api/v1/auth/login"
login_data = {
    "username": "admin",
    "password": "your_password"
}

login_response = requests.post(login_url, json=login_data)
token_data = login_response.json()
access_token = token_data["access_token"]

# 2. 发送飞书通知卡片（给个人用户，带 open_message_id）
notify_url = "http://localhost:8000/api/v1/feishu/notify"
headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}
payload = {
    "card_content": {
        "schema": "2.0",
        "header": {
            "title": {"tag": "plain_text", "content": "告警通知"},
            "template": "red"
        },
        "body": {
            "elements": [
                {"tag": "markdown", "content": "**服务器 CPU 使用率过高**"}
            ]
        }
    },
    "user": "zhangsan",
    "callback_id": "alert_123",
    "open_message_id": "alert_server_cpu"
}

response = requests.post(notify_url, json=payload, headers=headers)
result = response.json()
print("发送结果:", result)

# 2b. 发送飞书通知卡片（到群聊）
chat_payload = {
    "card_content": {
        "schema": "2.0",
        "header": {
            "title": {"tag": "plain_text", "content": "告警通知"},
            "template": "red"
        },
        "body": {
            "elements": [
                {"tag": "markdown", "content": "**服务器 CPU 使用率过高**"}
            ]
        }
    },
    "chat_id": "oc_cb42cb69eb9703e4cb284b516272c920",
    "callback_id": "alert_456"
}

chat_response = requests.post(notify_url, json=chat_payload, headers=headers)
print("群聊发送结果:", chat_response.json())

# 3a. 按消息 ID 更新卡片
if result.get("success") and result.get("message_id"):
    message_id = result["message_id"]
    update_url = f"http://localhost:8000/api/v1/feishu/notify/{message_id}"
    update_payload = {
        "card_content": {
            "schema": "2.0",
            "header": {
                "title": {"tag": "plain_text", "content": "告警已解决"},
                "template": "green"
            },
            "body": {
                "elements": [
                    {"tag": "markdown", "content": "**服务器 CPU 使用率已恢复正常**"}
                ]
            }
        },
        "callback_id": "alert_123"
    }
    update_response = requests.patch(update_url, json=update_payload, headers=headers)
    print("按消息ID更新结果:", update_response.json())

# 3b. 按自定义标识更新卡片
update_by_open_id_url = "http://localhost:8000/api/v1/feishu/notify-by-open-id/alert_server_cpu"
update_by_open_id_payload = {
    "card_content": {
        "schema": "2.0",
        "header": {
            "title": {"tag": "plain_text", "content": "告警已解决"},
            "template": "green"
        },
        "body": {
            "elements": [
                {"tag": "markdown", "content": "**服务器 CPU 使用率已恢复正常**"}
            ]
        }
    },
    "callback_id": "alert_123"
}
update_by_open_id_response = requests.patch(update_by_open_id_url, json=update_by_open_id_payload, headers=headers)
print("按自定义标识更新结果:", update_by_open_id_response.json())

# 4. 查询通知记录
records_url = "http://localhost:8000/api/v1/notification-records"
records_response = requests.get(
    records_url,
    params={"user": "zhangsan", "success": True, "page": 1, "page_size": 10},
    headers=headers,
)
print("通知记录:", records_response.json())
```

## 数据库记录

每次调用发送/更新接口都会在 `notification_records` 表创建或更新记录：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | `int` | 记录 ID |
| `user` | `string` | 请求传入的用户标识（群聊时为 `chat:<chat_id>`） |
| `matched_user` | `string \| null` | 实际匹配到的用户名 |
| `feishu_open_id` | `string \| null` | 飞书用户 Open ID |
| `chat_id` | `string \| null` | 飞书群聊 ID |
| `receive_type` | `string` | 接收类型：`open_id`（个人）或 `chat_id`（群聊） |
| `callback_id` | `string \| null` | 业务回调标识 |
| `open_message_id` | `string \| null` | 自定义消息标识 |
| `card_content` | `jsonb \| null` | 卡片 JSON 内容 |
| `message_id` | `string \| null` | 飞书返回的消息 ID |
| `success` | `boolean` | 发送是否成功 |
| `error` | `string \| null` | 错误信息 |
| `created_at` | `datetime` | 创建时间 |

## 相关文件

| 文件 | 说明 |
|------|------|
| `app/api/v1/auth.py` | 认证 API：login, logout, refresh, me |
| `app/api/v1/feishu_notifications.py` | 飞书通知 API：POST /notify, PATCH /notify/{message_id}, PATCH /notify-by-open-id/{open_message_id} |
| `app/api/v1/notification_records.py` | 通知记录管理 API：GET, DELETE |
| `app/integrations/feishu/service.py` | 飞书服务：`send_message_to_user`(支持 `receive_id_type`), `update_card_message`(调用 `im.v1.message.patch` 原地更新卡片) |
| `app/integrations/feishu/callback_handler.py` | 飞书回调处理：卡片按钮交互、消息接收 |
| `app/crud/crud_notification_record.py` | 通知记录 CRUD |
| `app/models/notification_record.py` | 通知记录数据模型（含 `chat_id`, `receive_type`, `open_message_id` 字段） |
| `app/schemas/notification_record.py` | 通知记录 Pydantic schemas |
| `frontend/src/pages/System/NotificationRecordList.tsx` | 前端通知记录页面 |
