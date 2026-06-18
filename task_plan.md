# 资产拓扑可视化 - 实现计划

> 设计文档: docs/plans/2026-06-18-asset-topology-design.md
> 创建时间: 2026-06-18

## 目标

在 /assets 页面新增"拓扑视图"Tab，使用 React Flow 实现交互式资产拓扑图，按类型分组，支持自动推断+手动编辑关联关系。

## Phase 1: 后端 - 数据模型与迁移 [pending]

- [ ] 创建 `backend/app/models/asset_relation.py` — AssetRelation 模型
- [ ] 在 `backend/app/models/asset.py` 添加 relations relationship
- [ ] 创建 Alembic 迁移脚本 `backend/alembic/versions/XXXX_create_asset_relations.py`
- [ ] 执行迁移，验证表创建成功

## Phase 2: 后端 - Schema 与 CRUD [pending]

- [ ] 创建 `backend/app/schemas/asset_relation.py` — Pydantic schema
- [ ] 创建 `backend/app/crud/crud_asset_relation.py` — CRUD 操作
- [ ] 实现自动推断逻辑（同网段→CONNECTED，同IDC→LOCATED_IN）

## Phase 3: 后端 - API 端点 [pending]

- [ ] 在 `backend/app/api/v1/assets.py` 新增 `GET /assets/topology`
- [ ] 新增 `POST /assets/topology/edges`
- [ ] 新增 `DELETE /assets/topology/edges/{edgeId}`
- [ ] 通过 8000 端口测试 3 个 API

## Phase 4: 前端 - 依赖安装与 API 封装 [pending]

- [ ] 安装 `@xyflow/react` 和 `dagre` 依赖
- [ ] 创建 `frontend/src/services/topology.ts` — API 封装
- [ ] 创建 TypeScript 类型定义

## Phase 5: 前端 - 自定义节点与边 [pending]

- [ ] 创建 `frontend/src/components/Topology/AssetNode.tsx` — 自定义节点
- [ ] 创建 `frontend/src/components/Topology/AssetEdge.tsx` — 自定义边
- [ ] 节点含状态色点、IP、CPU/内存/磁盘进度条、负责人/OS/配置
- [ ] 边区分自动推断（虚线）和手动（实线）

## Phase 6: 前端 - 拓扑主组件 [pending]

- [ ] 创建 `frontend/src/pages/Assets/AssetTopology.tsx`
- [ ] 集成 ReactFlow 画布 + MiniMap + Controls
- [ ] 实现 dagre 自动布局
- [ ] 实现工具栏（自动布局/编辑关联/适应画布/筛选）
- [ ] 实现查看模式与编辑模式切换
- [ ] 实现侧边详情面板

## Phase 7: 前端 - Tab 集成与构建 [pending]

- [ ] 在 `AssetList.tsx` 新增"拓扑视图"Tab
- [ ] `npm run build` 验证构建
- [ ] 浏览器验证功能

## Errors Encountered

| Error | Attempt | Resolution |
|-------|---------|------------|
| (空) | | |

## Decisions

| 决策 | 理由 |
|------|------|
| 使用 React Flow (@xyflow/react) | 内置拖拽/缩放/连线，与React 19兼容 |
| Tab 集成而非独立页面 | 复用现有路由，用户体验连贯 |
| 混合模式关联 | 自动推断减少手动工作，手动修正保证灵活性 |
| dagre 自动布局 | 成熟稳定，包体积小 |
