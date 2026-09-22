# 匿名建议业务逻辑流程图

## 概述

匿名建议模块支持员工匿名提交意见，通过飞书卡片流转至部门负责人审批、市场部存档，全流程对提交者隐藏身份（仅用 `submitter_id` 做审计、用 `query_code` 做进度查询）。

- **后端 API**: [backend/app/api/v1/suggestions.py](../backend/app/api/v1/suggestions.py)
- **业务服务**: [backend/app/services/suggestion_service.py](../backend/app/services/suggestion_service.py)
- **飞书回调**: [backend/app/integrations/feishu/callback_handler.py](../backend/app/integrations/feishu/callback_handler.py)
- **数据模型**: [backend/app/models/suggestion.py](../backend/app/models/suggestion.py)

## 状态机

```mermaid
stateDiagram-v2
    [*] --> PENDING: 提交建议
    PENDING --> APPROVED: 部门负责人审批通过
    PENDING --> REJECTED: 部门负责人驳回
    APPROVED --> ARCHIVED: 市场部填写执行结果存档
    REJECTED --> [*]
    ARCHIVED --> [*]

    note right of PENDING
        status='pending'
        已发送飞书待审批卡片
        含【审批通过】【驳回】按钮
    end note

    note right of APPROVED
        status='approved'
        原卡片更新为"已审批"
        发送市场部卡片（含输入表单）
    end note

    note right of ARCHIVED
        status='archived'
        市场部卡片更新为"已存档"
        记录 market_result
    end note

    note right of REJECTED
        status='rejected'
        原卡片更新为"已驳回"
        记录 reject_reason
    end note
```

## 完整业务流程

```mermaid
flowchart TD
    User([员工]) -->|提交建议| SubmitAPI[POST /api/v1/suggestions]

    subgraph SubmitStage [阶段 1: 提交建议]
        SubmitAPI --> Validate{校验<br/>department_id 或<br/>assignee_user_id}
        Validate -->|缺失| Err400[400: 请至少选择一个]
        Validate -->|通过| GenCode[生成 6 位查询码<br/>generate_query_code]

        GenCode -->|IntegrityError<br/>unique 冲突| RetryCode{重试 < 3 次?}
        RetryCode -->|是| GenCode
        RetryCode -->|否| Err500[500: 生成查询码失败]

        GenCode -->|成功| CreateSuggestion[创建 Suggestion<br/>status=pending]
        CreateSuggestion --> CollectRecipients[收集接收人]

        CollectRecipients --> HasDept{有 department_id?}
        HasDept -->|是| LoadDept[查询部门负责人<br/>校验 leader.feishu_open_id]
        LoadDept -->|无 open_id| Err400b[400: 部门未配置负责人]
        HasDept -->|否| HasUser{有 assignee_user_id?}

        LoadDept --> HasUser
        HasUser -->|是| LoadUser[查询指派人<br/>校验 feishu_open_id]
        LoadUser --> Dedup[去重 by open_id]
        HasUser -->|否| Dedup

        Dedup --> HasRecipients{有接收人?}
        HasRecipients -->|否| Err400c[400: 无可用接收人]
        HasRecipients -->|是| CreateAssignments[创建 SuggestionAssignment 记录]
        CreateAssignments --> CommitDB[提交 DB]
    end

    CommitDB --> BgTask[后台任务: _send_cards_task]
    BgTask --> SendCard[发送飞书待审批卡片<br/>send_pending_card<br/>3 次指数退避重试]
    SendCard --> UpdateMsgId[更新 assignment.open_message_id]
    UpdateMsgId --> ReturnCode[返回 query_code 给用户]

    User -->|凭 query_code 查询| TrackAPI[GET /suggestions/track/&#123;code&#125;]
    TrackAPI --> CheckOwner{校验 submitter_id<br/>== 当前用户?}
    CheckOwner -->|否| Err403[403: 无权查询]
    CheckOwner -->|是| ReturnStatus[返回状态/执行结果]

    SendCard -.->|飞书推送| Approver[部门负责人/指派人]

    subgraph ApproveStage [阶段 2: 审批通过 - 飞书卡片回调]
        Approver -->|点击【审批通过】| Callback1[飞书回调<br/>suggestion_approve_]
        Callback1 --> Thread1[启动线程 _handle_suggestion_approve]
        Thread1 --> UpdateAssign1[UPDATE assignment<br/>SET status=approved<br/>WHERE status=pending]
        UpdateAssign1 --> RowCount1{rowcount=1?}
        RowCount1 -->|否| Skip1[跳过 - 已被其他线程处理]
        RowCount1 -->|是| UpdateSugg1[UPDATE suggestion<br/>SET status=approved]
        UpdateSugg1 --> UpdateCard1[更新原卡片为"已审批"<br/>蓝色无按钮]
        UpdateCard1 --> SendMarketCard[发送市场部卡片<br/>含输入表单]
        SendMarketCard --> MarketTeam[市场部通知组成员]
    end

    subgraph RejectStage [阶段 2: 驳回 - 飞书卡片回调]
        Approver -->|点击【驳回】| Callback2[飞书回调<br/>suggestion_reject_]
        Callback2 --> Thread2[启动线程 _handle_suggestion_reject]
        Thread2 --> UpdateAssign2[UPDATE assignment<br/>SET status=rejected<br/>WHERE status=pending]
        UpdateAssign2 --> RowCount2{rowcount=1?}
        RowCount2 -->|否| Skip2[跳过 - 已被其他线程处理]
        RowCount2 -->|是| UpdateSugg2[UPDATE suggestion<br/>SET status=rejected<br/>reject_reason=审批人驳回]
        UpdateSugg2 --> UpdateCard2[更新原卡片为"已驳回"<br/>灰色无按钮]
    end

    subgraph ArchiveStage [阶段 3: 存档 - 飞书卡片回调]
        MarketTeam -->|填写执行结果<br/>点击【提交存档】| Callback3[飞书回调<br/>suggestion_archive_]
        Callback3 --> CheckResult{market_result 非空?}
        CheckResult -->|否| ErrToast[toast: 请填写执行结果]
        CheckResult -->|是| Truncate[I-24: 截断到 2000 字符]
        Truncate --> Thread3[启动线程 _handle_suggestion_archive]
        Thread3 --> UpdateSugg3[UPDATE suggestion<br/>SET status=archived<br/>market_result, archived_at<br/>WHERE status=approved]
        UpdateSugg3 --> RowCount3{rowcount=1?}
        RowCount3 -->|否| Skip3[跳过 - 已被其他线程处理]
        RowCount3 -->|是| UpdateCard3[更新市场部卡片为"已存档"<br/>绿色无按钮]
    end

    UpdateCard1 -.->|卡片状态变化| Approver
    UpdateCard2 -.->|卡片状态变化| Approver
    UpdateCard3 -.->|卡片状态变化| MarketTeam

    classDef apiCall fill:#e1f5ff,stroke:#0288d1
    classDef feishuCall fill:#fff4e1,stroke:#f57c00
    classDef dbOp fill:#e8f5e9,stroke:#388e3c
    classDef error fill:#ffebee,stroke:#c62828
    classDef success fill:#f3e5f5,stroke:#7b1fa2

    class SubmitAPI,TrackAPI apiCall
    class SendCard,UpdateCard1,UpdateCard2,UpdateCard3,SendMarketCard feishuCall
    class CreateSuggestion,CreateAssignments,CommitDB,UpdateAssign1,UpdateSugg1,UpdateAssign2,UpdateSugg2,UpdateSugg3 dbOp
    class Err400,Err400b,Err400c,Err500,Err403,ErrToast error
    class ReturnCode,ReturnStatus success
```

## 关键不变式与修复点

### 一致性（C-07/C-08: 并发幂等）

```mermaid
sequenceDiagram
    participant U1 as 审批人 A
    participant U2 as 审批人 B（并发）
    participant FS as 飞书回调
    participant DB as DB

    U1->>FS: 点击【审批通过】
    U2->>FS: 点击【审批通过】（并发）
    par 线程 1
        FS->>DB: UPDATE assignment SET status=approved<br/>WHERE id=X AND status='pending'
        DB-->>FS: rowcount=1（成功）
        FS->>DB: UPDATE suggestion SET status=approved
        FS->>FS: 发送市场部卡片
    and 线程 2
        FS->>DB: UPDATE assignment SET status=approved<br/>WHERE id=X AND status='pending'
        DB-->>FS: rowcount=0（已被处理）
        FS-->>FS: 跳过（不重复发送市场部卡片）
    end
```

### 重试机制

| 场景 | 函数 | 重试策略 |
|---|---|---|
| query_code unique 冲突 | `submit_suggestion` 捕获 `IntegrityError` | 最多 3 次，每次重新生成 |
| query_code 生成查重 | `generate_query_code` | 30 次 + 50 次（仍 6 字符） |
| 飞书卡片发送 | `_send_with_retry` | 3 次指数退避（1s→2s→4s） |
| 飞书卡片更新 | `_update_card_with_retry` | 3 次指数退避（1s→2s→4s） |

## API 端点

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| POST | `/api/v1/suggestions` | `suggestion:submit` | 提交匿名建议，返回 `query_code` |
| GET | `/api/v1/suggestions/track/{query_code}` | `suggestion:submit` | 凭查询码查询进度（校验归属） |
| GET | `/api/v1/suggestions/my-codes/list` | `suggestion:submit` | 获取当前用户历史查询码列表 |
| GET | `/api/v1/suggestions` | `suggestion:read` | 管理端建议列表（分页） |
| GET | `/api/v1/suggestions/{id}` | `suggestion:read` | 建议详情 |
| PUT | `/api/v1/suggestions/{id}/archive` | `suggestion:archive` | 市场部存档（API 路径，与飞书回调对称） |

## 数据模型

```mermaid
erDiagram
    suggestions ||--o{ suggestion_assignments : has
    suggestion_assignments }o--|| departments : "指派部门（可选）"
    suggestion_assignments }o--|| users : "指派人（可选）"
    suggestions }o--|| users : "submitter_id（审计）"
    suggestions }o--|| users : "market_reviewer_id（存档人）"
    suggestions }o--|| users : "rejected_by（驳回人）"

    suggestions {
        int id PK
        text content "意见内容"
        text highlights "项目亮点"
        text innovation_ideas "创新idea"
        varchar_20 status "pending/approved/archived/rejected"
        varchar_6 query_code UK "匿名查询码"
        int submitter_id FK "审计用，不展示"
        varchar_45 client_ip "提交IP"
        text market_result "市场部执行结果"
        int market_reviewer_id FK
        datetime archived_at
        text reject_reason
        int rejected_by FK
        datetime rejected_at
        datetime created_at
    }

    suggestion_assignments {
        int id PK
        int suggestion_id FK
        int department_id FK "可空"
        int assignee_user_id FK "可空"
        varchar_64 assignee_open_id "飞书open_id"
        varchar_100 open_message_id "飞书卡片消息ID"
        varchar_20 status "pending/approved/rejected"
        datetime reviewed_at
        text review_comment
    }
```

## 飞书卡片流转

```mermaid
flowchart LR
    subgraph S1 [待审批卡片 - 橙色]
        S1Title[【匿名建议待审批】]
        S1Content[意见内容/亮点/idea/部门]
        S1Btn1[✅ 审批通过]
        S1Btn2[❌ 驳回]
    end

    subgraph S2 [已审批卡片 - 蓝色]
        S2Title[【匿名建议已审批】]
        S2Content[审批人/审批时间]
        S2Status[已审批通过，转市场部处理中]
    end

    subgraph S3 [市场部卡片 - 蓝色]
        S3Title[【匿名建议待执行】]
        S3Content[意见内容/亮点/idea/审批人/时间]
        S3Form[输入框: 执行结果]
        S3Btn[📦 提交存档]
    end

    subgraph S4 [已存档卡片 - 绿色]
        S4Title[【匿名建议已存档】]
        S4Content[执行结果/存档时间]
        S4Status[已存档]
    end

    subgraph S5 [已驳回卡片 - 灰色]
        S5Title[【匿名建议已驳回】]
        S5Content[驳回原因]
        S5Status[已驳回]
    end

    S1 -->|点击审批通过| S2
    S2 -.->|同步发送| S3
    S3 -->|点击提交存档| S4
    S1 -->|点击驳回| S5
```
