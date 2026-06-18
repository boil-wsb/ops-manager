# 资产拓扑可视化 - 研究发现

> 创建时间: 2026-06-18

## 项目现状

### 后端
- Asset 模型有 idc/region/rack 三级拓扑字段，idc 有独立索引
- `GET /assets/tree` 接口已实现 IDC→Region→Rack→Asset 层级聚合
- Asset 类型: SERVER/VM/NETWORK/STORAGE/TERMINAL
- Asset 状态: ACTIVE/OFFLINE/MAINTENANCE/RETIRED
- 资产有 owner_id FK → users.id
- 资产有 terminal_metrics relationship

### 前端
- 资产页面: AssetList.tsx (列表), AssetDetail.tsx (详情), AssetDiscovery.tsx (发现), AssetFormModal.tsx (表单)
- 路由: /assets, /assets/discovery, /assets/:id
- 无任何可视化库安装
- 使用 antd 5.22 + React 19 + react-router-dom 7
- 状态管理: zustand + @tanstack/react-query

### API 端点
- GET /assets — 列表（分页/过滤，已排除RETIRED）
- GET /assets/tree — 树形结构（已实现但前端未使用）
- GET /assets/terminals — 终端列表
- GET /assets/{id}/metrics — 实时指标

## 技术选型研究

### React Flow (@xyflow/react 12.x)
- 内置: 拖拽、缩放、连线、MiniMap、Controls
- 自定义节点和边
- 与 React 19 兼容
- 包体积 ~150KB gzip
- MIT 许可证

### dagre
- DAG 自动布局算法
- 包体积 ~30KB gzip
- 适合树形/层次布局

## 关键设计决策

1. 关联关系存储在独立表 asset_relations，不修改 assets 表
2. 自动推断边不存入数据库，每次请求实时计算
3. 手动边存入数据库，auto_inferred=false
4. 节点位置保存到 localStorage，不存后端
