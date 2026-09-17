# OpsManager 前端

运维管理平台前端，基于 React 18 + TypeScript + Ant Design 5。

## 技术栈

- **React 18** - UI 框架
- **TypeScript** - 类型安全
- **Vite** - 构建工具
- **Ant Design 5.x** - UI 组件库
- **Zustand** - 状态管理
- **React Query** - 数据请求与缓存
- **React Router 6** - 路由管理

## 开发

```bash
npm install      # 安装依赖
npm run dev      # 启动开发服务器（默认 5173）
npm run build    # 生产构建，产物输出至 dist/
npm run preview  # 本地预览生产构建
```

## 环境变量

`VITE_API_BASE_URL`：后端 API 基础地址（如 `http://192.168.23.36:8000/api`），见 `.env.example`。

## 目录结构

```
src/
├── components/        # 通用组件（Layout, PermissionGuard 等）
├── config/            # 配置（菜单权限、路由权限、主题）
├── hooks/             # 自定义 Hooks（useFormModal, usePermission 等）
├── pages/             # 页面组件（Alerts, Assets, Ops, System, Users 等）
├── services/          # API 服务层
├── stores/            # Zustand 状态管理
├── types/             # TypeScript 类型定义
├── utils/             # 工具函数
├── App.tsx            # 应用入口与路由
└── main.tsx           # 挂载入口
```

## 约定

- API 封装统一在 `services/`，后端接口路径以 `/api/v1` 为前缀；
- 页面级权限由路由权限与菜单权限配置控制（`config/`）；
- 登录态使用 JWT（`/api/v1/auth/login`），请求拦截器自动携带 `Authorization: Bearer <token>`。