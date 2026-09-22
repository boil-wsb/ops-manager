# 外部鉴权服务对接文档（工号登录 · 角色校验 · 首次强制改密）

> ops-manager 作为同网段服务间的 auth 服务，提供：
>
> 1. **工号登录**：外部服务用工号+密码登录并获取 JWT token；
> 2. **角色校验**：通过工号获知用户是否属于**行政 / 采购 / 营销**角色及具体角色标识；
> 3. **首次登录强制改密**：初始密码首次登录后必须修改密码，否则业务接口被拦截。

***

## 1. 快速接入

| 项目      | 内容                                                                                     |
| ------- | -------------------------------------------------------------------------------------- |
| 接口地址    | `POST http://<ops-manager-host>:8000/api/v1/auth/...` / `.../auth-service/verify-role` |
| 请求/响应格式 | `application/json; charset=utf-8`                                                      |
| 认证方式    | 角色校验免 JWT（仅信任网段）；登录/改密接口为公开前缀（见各小节）                                                    |
| 限流      | 登录 60 次/分钟/IP；角色校验 60 次/分钟/IP                                                          |

> 信任网段：`127.0.0.1/32`、`192.168.0.0/16`、`10.0.0.0/8`。角色校验接口非信任网段调用将返回 `401 Not authenticated`（全局 JWT 拦截）。

***

## 2. 接口一览

| 方法   | 路径                                 | 说明                                               |
| ---- | ---------------------------------- | ------------------------------------------------ |
| POST | `/api/v1/auth/external/login`      | 工号登录，签发 token；首次登录返回 `must_change_password=true` |
| POST | `/api/v1/auth/change-password`     | 修改密码（带 token）；改密成功清除待改密标记并重签 token               |
| POST | `/api/v1/auth/refresh`             | 刷新 token（沿用待改密状态，未改密不绕过）                         |
| GET  | `/api/v1/auth/me`                  | 当前用户信息（待改密状态下仍可访问）                               |
| POST | `/api/v1/auth-service/verify-role` | 工号角色校验                                           |

***

## 3. 工号登录

### POST /api/v1/auth/external/login

### 3.1 请求体

```json
{
  "employee_id": "JR2023008",
  "password": "初始密码"
}
```

### 3.2 成功响应 — HTTP 200

```json
{
  "access_token": "eyJhbGciOi...",
  "refresh_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "expires_in": 28800,
  "permissions": [],
  "permission_version": null,
  "must_change_password": true,
  "user": {
    "id": 95,
    "username": "sushanshan",
    "full_name": "苏珊珊",
    "employee_id": "JR2023008",
    "is_active": true,
    "is_superuser": false,
    "permissions": [],
    "roles": []
  }
}
```

| 字段                     | 类型      | 说明                                          |
| ---------------------- | ------- | ------------------------------------------- |
| access\_token          | string  | 访问令牌，`Authorization: Bearer <access_token>` |
| refresh\_token         | string  | 刷新令牌                                        |
| must\_change\_password | boolean | **true = 首次登录，必须先改密**；false = 正常            |

### 3.3 错误响应

| HTTP 状态码 | detail  | 场景                   |
| -------- | ------- | -------------------- |
| 401      | 工号或密码错误 | 工号不存在或密码错误（统一文案，防枚举） |
| 403      | 用户已被禁用  | 账号被停用                |

***

## 4. 首次登录强制改密

### 4.1 流程

```text
外部服务 ──工号+初始密码──> POST /auth/external/login
        <── must_change_password=true + token(带待改密标记)
        ──token──> 业务接口（如 /roles /assets ...）  → 403 请先修改初始密码
        ──token + 旧密码/新密码──> POST /auth/change-password
        <── 200 + 新 token(无标记，可直接使用)
        ──新 token──> 业务接口  → 正常访问
```

> 被拦截的接口：**除** **`/api/v1/auth/*`** **外的一切业务接口**均返回 `HTTP 403 {"detail":"请先修改初始密码"}`。
> 改密/登出/个人信息/刷新（`/auth/*` 前缀）不受影响。

### 4.2 修改密码 — POST /api/v1/auth/change-password

请求头：`Authorization: Bearer <token>`

请求体：

```json
{
  "old_password": "初始密码",
  "new_password": "新密码(8-100位)"
}
```

成功响应 — HTTP 200（同时返回可直接使用的无标记新 token）：

```json
{
  "message": "密码修改成功",
  "access_token": "eyJhbGciOi...(新)",
  "refresh_token": "eyJhbGciOi...(新)",
  "token_type": "bearer",
  "expires_in": 28800,
  "must_change_password": false
}
```

错误：旧密码错误 → `400 当前密码错误`。

### 4.3 注意事项

1. **必须用返回的新 token 替换旧 token**，旧 token 即使未过期也持续被拦截；
2. 未改密前调用 `/auth/refresh` 获得的 token **仍带待改密标记**，业务接口同样被拦截（不可绕过）；
3. 新同步/新建用户默认 `must_change_password=true`；存量用户默认关闭，由管理员按需开启。

***

## 5. 工号角色校验

### POST /api/v1/auth-service/verify-role

根据工号验证用户角色并返回命中的业务角色（行政/采购/营销）。

### 5.1 请求体

```json
{
  "employee_id": "JR2023008"
}
```

| 字段           | 类型     | 必填 | 说明                                         |
| ------------ | ------ | -- | ------------------------------------------ |
| employee\_id | string | 是  | 员工工号，与用户表中的 `employee_id`（工号）精确匹配，最大 64 字符 |

### 5.2 响应

#### 成功（命中角色）— HTTP 200

```json
{
  "employee_id": "JR2023008",
  "authorized": true,
  "role": "采购",
  "code": "procurement",
  "full_name": "张三",
  "matched_roles": [
    { "name": "采购", "code": "procurement" }
  ]
}
```

#### 成功（用户存在但未命中角色）— HTTP 200

```json
{
  "employee_id": "JR2023008",
  "authorized": false,
  "role": null,
  "code": null,
  "full_name": "张三",
  "matched_roles": []
}
```

| 字段             | 类型             | 说明                                       |
| -------------- | -------------- | ---------------------------------------- |
| employee\_id   | string         | 回显请求工号                                   |
| authorized     | boolean        | 是否命中行政/采购/营销任一角色                         |
| role           | string \| null | 命中的第一个角色中文名，未命中为 `null`                  |
| code           | string \| null | 命中的第一个角色 ASCII 标识，未命中为 `null`            |
| full\_name     | string \| null | 用户姓名                                     |
| matched\_roles | array          | 命中的所有角色 `[{name, code}]`（用户可能同时拥有多个目标角色） |

### 5.3 业务角色对照

外部服务请以 `code` 为唯一稳定标识进行匹配（中文名 `name` 可能被管理员调整，`code` 保持不变）：

| 角色名（name） | code（稳定标识，推荐用于匹配） |
| --------- | ----------------- |
| 行政        | `admin_dept`      |
| 采购        | `procurement`     |
| 营销        | `marketing`       |

### 5.4 错误响应

| HTTP 状态码 | detail                     | 场景              |
| -------- | -------------------------- | --------------- |
| 400      | 请求体 JSON 解析失败（422 为字段校验失败） | 参数非法            |
| 401      | Not authenticated          | 非信任网段调用，被全局鉴权拦截 |
| 403      | 用户已停用                      | 工号存在但对应用户已被禁用   |
| 404      | 工号不存在                      | 用户表中无此工号        |
| 429      | 限流                         | 超过 60 次/分钟/IP   |

***

## 6. 调用示例

### 6.1 完整流程：登录 → 改密 → 鉴权调用（Python）

```python
import requests

BASE = "http://<ops-manager-host>:8000"

# 1. 工号登录（初始密码）
login = requests.post(
    f"{BASE}/api/v1/auth/external/login",
    json={"employee_id": "JR2023008", "password": "初始密码"},
    timeout=10,
).json()

token = login["access_token"]
if login["must_change_password"]:
    # 2. 首次登录：先修改初始密码
    changed = requests.post(
        f"{BASE}/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"old_password": "初始密码", "new_password": "新密码"},
        timeout=10,
    ).json()
    token = changed["access_token"]   # 用改密返回的新 token 替换

# 3. 携带 token 调用业务接口
headers = {"Authorization": f"Bearer {token}"}
resp = requests.get(f"{BASE}/api/v1/roles", headers=headers, timeout=10)

# 4. 角色校验（无需 token，信任网段内即可）
verify = requests.post(
    f"{BASE}/api/v1/auth-service/verify-role",
    json={"employee_id": "JR2023008"},
    timeout=10,
).json()
```

### 6.2 curl

```bash
curl -X POST 'http://192.168.23.36:8000/api/v1/auth/external/login' \
  -H 'Content-Type: application/json' \
  -d '{"employee_id":"JR2023008","password":"初始密码"}'

curl -X POST 'http://192.168.23.36:8000/api/v1/auth/change-password' \
  -H 'Authorization: Bearer <登录返回的token>' \
  -H 'Content-Type: application/json' \
  -d '{"old_password":"初始密码","new_password":"新密码"}'

curl -X POST 'http://192.168.23.36:8000/api/v1/auth-service/verify-role' \
  -H 'Content-Type: application/json' \
  -d '{"employee_id":"JR2023008"}'
```

### 6.3 角色校验示例：Python（requests）

```python
import requests

resp = requests.post(
    "http://<ops-manager-host>:8000/api/v1/auth-service/verify-role",
    json={"employee_id": "JR2023008"},
    timeout=10,
)
data = resp.json()

if resp.status_code == 200 and data["authorized"]:
    # 命中三角色之一，按 code 处理具体角色
    role_code = data["code"]           # 例如 "procurement"
    role_name = data["role"]           # 例如 "采购"
else:
    # 404 工号不存在 / 403 用户停用 / authorized=false 无权限
    print(resp.status_code, data)
```

### 6.4 角色校验示例：Java（OkHttp）

```java
OkHttpClient client = new OkHttpClient();
String json = "{\"employee_id\":\"JR2023008\"}";
Request request = new Request.Builder()
        .url("http://<ops-manager-host>:8000/api/v1/auth-service/verify-role")
        .post(RequestBody.create(json, MediaType.parse("application/json")))
        .build();
try (Response response = client.newCall(request).execute()) {
    System.out.println(response.code());
    System.out.println(response.body().string());
}
```

***

## 7. 对接建议

1. **成功判定**：以 `HTTP 200 + authorized == true` 为准，`code` 用于区分具体角色；
2. **初始密码**：新同步用户初始密码为统一默认密码（`mh123456`），首次登录必须修改；改密后再无初始密码概念；
3. **token 生命周期**：登录/改密/刷新返回的 token 均需替换本地缓存；改密前旧 token 会被业务接口持续拦截；
4. **分布式部署**：在负载均衡/反代层将该接口加入白名单（透传即可），无需特殊处理；
5. **工号来源**：工号与飞书通讯录同步，录入后生效；如提示"工号不存在"，请先确认该员工的飞书信息已同步；
6. **安全说明**：角色校验接口仅信任网段内可用，且带限流保护；如需进一步收紧（如按调用方 IP 白名单或 API Key），请联系平台管理员调整 `AUTH_TRUSTED_NETWORKS` / `AUTH_EXCLUDED_PATHS` 配置。

***

## 8. 变更记录

| 日期         | 说明                                  |
| ---------- | ----------------------------------- |
| 2026-09-03 | 新建：三角色（行政/采购/营销）+ 工号角色校验接口 v1       |
| 2026-09-03 | 新增：工号登录（external/login）+ 首次登录强制改密流程 |

