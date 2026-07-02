# 内网 sh 脚本通过 ops-manager 接口发送飞书卡片方案

## 适用场景

内网 sh 脚本需要组装飞书卡片信息并发送到指定群组 `oc_a78f223fb1c88d81241f174f680f83f9`，通过项目已有的 `POST /api/v1/feishu/notify` 接口实现。

## 核心结论

- **接口路径**：`POST /api/v1/feishu/notify`
- **免认证**：该接口已在 [auth_middleware.py](backend/app/core/auth_middleware.py) 的 `EXCLUDE_PATHS` 白名单中（第 80 行），内网任意主机直连 8000 端口即可调用，无需登录、无需 token
- **关键实现文件**：[feishu_notifications.py](backend/app/api/v1/feishu_notifications.py) 第 35-218 行
- **发送到群聊**：请求体传 `chat_id` + `card_content` 即可

## 请求字段说明

| 字段 | 必填 | 说明 |
|------|------|------|
| `card_content` | 是 | 飞书卡片 JSON（schema 2.0） |
| `chat_id` | 是（与 user 二选一） | 群聊 ID，填 `oc_a78f223fb1c88d81241f174f680f83f9` |
| `callback_id` | 否 | 业务标识，用于后续更新卡片时校验归属 |
| `open_message_id` | 否 | 自定义标识，便于后续按标识更新卡片 |
| `callback_url` | 否 | 卡片按钮回调转发地址（需同时提供 open_message_id） |

## 基础 sh 脚本示例

```bash
#!/bin/bash
# send_feishu_card.sh - 通过 ops-manager 接口向指定群组发送飞书卡片
# 用法: ./send_feishu_card.sh "标题" "内容(markdown)" [severity]

set -euo pipefail

# ===== 配置区 =====
API_BASE="http://127.0.0.1:8000"
CHAT_ID="oc_a78f223fb1c88d81241f174f680f83f9"

# 业务参数（可由命令行传入）
TITLE="${1:-脚本通知}"
CONTENT="${2:-**来自内网脚本的卡片消息**}"
SEVERITY="${3:-info}"   # info / warning / critical，控制 header 颜色

# 颜色映射
case "$SEVERITY" in
  critical) TEMPLATE="red"    ;;
  warning)  TEMPLATE="orange" ;;
  *)        TEMPLATE="blue"    ;;
esac

# 自定义标识（可选，便于后续按标识更新卡片）
OPEN_MESSAGE_ID="script_$(date +%Y%m%d_%H%M%S)_$$"

# ===== 组装 card_content =====
# 使用 jq 构造 JSON，避免转义地狱；若无 jq 可改用 python3 -c
CARD_JSON=$(jq -n \
  --arg title "$TITLE" \
  --arg content "$CONTENT" \
  --arg template "$TEMPLATE" \
  '{
    schema: "2.0",
    header: {
      title: { tag: "plain_text", content: $title },
      template: $template
    },
    body: {
      elements: [
        { tag: "markdown", content: $content },
        { tag: "hr" },
        { tag: "note", elements: [
          { tag: "plain_text", content: "由内网脚本通过 ops-manager 发送" }
        ]}
      ]
    }
  }')

# ===== 发送请求 =====
RESPONSE=$(curl -sS -X POST "${API_BASE}/api/v1/feishu/notify" \
  -H "Content-Type: application/json" \
  -d "$(jq -n \
        --arg chat_id "$CHAT_ID" \
        --arg open_message_id "$OPEN_MESSAGE_ID" \
        --argjson card "$CARD_JSON" \
        '{chat_id: $chat_id, open_message_id: $open_message_id, card_content: $card}')")

# ===== 结果解析 =====
SUCCESS=$(echo "$RESPONSE" | jq -r '.success')
MESSAGE_ID=$(echo "$RESPONSE" | jq -r '.message_id // "null"')
ERROR=$(echo "$RESPONSE" | jq -r '.error // "null"')

if [ "$SUCCESS" = "true" ]; then
  echo "[OK] 卡片发送成功 message_id=${MESSAGE_ID} open_message_id=${OPEN_MESSAGE_ID}"
  # 后续如需更新该卡片，把 OPEN_MESSAGE_ID 记录到文件
  echo "$OPEN_MESSAGE_ID" >> /tmp/feishu_card_ids.log
else
  echo "[FAIL] 卡片发送失败 error=${ERROR}" >&2
  echo "完整响应: $RESPONSE" >&2
  exit 1
fi
```

## 进阶：组装复杂业务卡片

针对不同业务场景（部署、巡检、告警等），建议在 sh 中用函数封装卡片构造逻辑：

```bash
build_deploy_card() {
  local app="$1" env="$2" status="$3" operator="$4"
  local template; [ "$status" = "success" ] && template="green" || template="red"
  jq -n --arg app "$app" --arg env "$env" --arg status "$status" \
        --arg operator "$operator" --arg template "$template" \
  '{
    schema: "2.0",
    header: { title: {tag:"plain_text", content:"部署通知"}, template: $template },
    body: { elements: [
      {tag:"div", fields:[
        {is_short:true, text:{tag:"lark_md", content:"**应用**\n"+$app}},
        {is_short:true, text:{tag:"lark_md", content:"**环境**\n"+$env}},
        {is_short:true, text:{tag:"lark_md", content:"**状态**\n"+$status}},
        {is_short:true, text:{tag:"lark_md", content:"**操作人**\n"+$operator}}
      ]}
    ]}
  }'
}

# 调用示例
CARD_JSON=$(build_deploy_card "user-service" "prod" "success" "$(whoami)")
```

## 响应字段说明

发送成功响应示例：

```json
{
  "success": true,
  "message_id": "om_xxxxx",
  "matched_user": null,
  "chat_id": "oc_a78f223fb1c88d81241f174f680f83f9",
  "callback_id": null,
  "open_message_id": "script_20260701_220000_12345",
  "callback_url": null,
  "error": null
}
```

| 字段 | 说明 |
|------|------|
| `success` | 发送是否成功 |
| `message_id` | 飞书返回的消息 ID（用于按 message_id 更新卡片） |
| `chat_id` | 群聊 ID |
| `open_message_id` | 自定义消息标识（发送时传入的值） |
| `error` | 错误信息（成功时为 null） |

## 后续更新卡片

发送时传 `open_message_id` 后，可通过以下接口原地更新卡片（无需记住飞书 `message_id`）：

```bash
curl -X PATCH "${API_BASE}/api/v1/feishu/notify-by-open-id/${OPEN_MESSAGE_ID}" \
  -H "Content-Type: application/json" \
  -d "$(jq -n --argjson card "$NEW_CARD_JSON" '{card_content: $card}')"
```

典型场景：状态从 `running` 更新为 `success` / `failed`。

## 注意事项

1. **免认证前提**：该接口当前在 [EXCLUDE_PATHS](backend/app/core/auth_middleware.py#L67-L84) 白名单内，内网任意主机可直连 8000 端口调用。如后续调整认证策略需同步更新该白名单。
2. **依赖**：示例依赖 `jq`；如内网无 jq，可改用 `python3 -c 'import json; ...'` 或 `curl --data @payload.json` 配合外部 JSON 文件。
3. **API 地址**：验证接口直接走 8000 端口，不重启后端。
4. **依赖外部回调**：如果卡片带按钮且希望脚本接收点击事件，发送时再传 `callback_url` 指向脚本暴露的 HTTP 接口（需同时提供 `open_message_id`，仅支持 http/https 协议）。
5. **卡片格式参考**：[飞书卡片开发文档](https://open.feishu.cn/document/uAjLw4CM/ukzMukzMukzM/feishu-cards/card-components/interactive-components/button)

## 相关文件

| 文件 | 说明 |
|------|------|
| [backend/app/api/v1/feishu_notifications.py](backend/app/api/v1/feishu_notifications.py) | 飞书通知 API：POST /notify, PATCH 更新接口 |
| [backend/app/core/auth_middleware.py](backend/app/core/auth_middleware.py) | 认证中间件：EXCLUDE_PATHS 白名单（第 80 行包含 `/api/v1/feishu/notify`） |
| [backend/app/integrations/feishu/service.py](backend/app/integrations/feishu/service.py) | 飞书服务：send_message_to_user（支持 receive_id_type） |
| [feishu-notify-api.md](feishu-notify-api.md) | 飞书通知 API 完整文档 |
