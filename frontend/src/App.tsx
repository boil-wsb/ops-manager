import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { ConfigProvider, App as AntApp } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useEffect } from 'react';

import { useAuthStore } from './stores/authStore';
import { useThemeStore } from './stores/themeStore';
import { usePermission } from './hooks/usePermission';
import { authApi } from './services/auth';
import { getRoutePermission } from './config/routePermissions';
import { lightTheme, darkTheme } from './config/theme';
import Login from './pages/Login';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import AssetList from './pages/Assets/AssetList';
import AssetDetail from './pages/Assets/AssetDetail';
import AssetDiscovery from './pages/Assets/AssetDiscovery';
import DeploymentList from './pages/Ops/DeploymentList';
import CertificateList from './pages/Ops/CertificateList';
import ITManagement from './pages/Ops/ITManagement';
import ScheduledTaskList from './pages/Ops/ScheduledTaskList';
import HealthCheckList from './pages/Ops/HealthCheckList';
import HealthCheckDetail from './pages/Ops/HealthCheckDetail';
import RoleList from './pages/Roles/RoleList';
import UserList from './pages/Users/UserList';
import Profile from './pages/Profile/Profile';
import NavigationList from './pages/System/NavigationList';
import NotificationGroupList from './pages/System/NotificationGroupList';
import NotificationRecordList from './pages/System/NotificationRecordList';
import Forbidden from './pages/Forbidden';
import AlertManager from './pages/Alerts/AlertManager';
import AlertSilenceList from './pages/Alerts/AlertSilenceList';
import AlertTemplateList from './pages/Alerts/AlertTemplateList';
import AlertHistory from './pages/Alerts/AlertHistory';
import SuggestionSubmit from './pages/Suggestions/SuggestionSubmit';
import SuggestionList from './pages/Suggestions/SuggestionList';
import SuggestionDetail from './pages/Suggestions/SuggestionDetail';
import SuggestionTrack from './pages/Suggestions/SuggestionTrack';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

const ThemeProvider = ({ children }: { children: React.ReactNode }) => {
  const { mode } = useThemeStore();

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', mode);
  }, [mode]);

  const currentTheme = mode === 'dark' ? darkTheme : lightTheme;

  return (
    <ConfigProvider
      locale={zhCN}
      theme={currentTheme}
    >
      {children}
    </ConfigProvider>
  );
};

const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const location = useLocation();
  const { hasAnyPermission } = usePermission();

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  const permission = getRoutePermission(location.pathname);

  if (permission !== undefined && permission.length > 0) {
    const permissionList = Array.isArray(permission) ? permission : [permission];
    if (!hasAnyPermission(permissionList)) {
      return <Forbidden />;
    }
  }

  return <>{children}</>;
};

function App() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const storePermissionVersion = useAuthStore((s) => s.permissionVersion);
  const setPermissions = useAuthStore((s) => s.setPermissions);

  // 已登录用户启动时 / 刷新时，调 /auth/me 获取最新权限版本，
  // 与本地缓存版本比对，不一致则刷新缓存。
  useEffect(() => {
    if (!isAuthenticated) return;
    let cancelled = false;
    (async () => {
      try {
        const user = await authApi.getCurrentUser();
        if (cancelled) return;
        const remoteVersion = user.permissionVersion || '';
        if (remoteVersion && remoteVersion !== storePermissionVersion) {
          setPermissions(user.permissions || [], remoteVersion);
        }
      } catch {
        // 网络错误 / 401 静默处理，下次刷新页面再试
      }
    })();
    return () => { cancelled = true; };
  }, [isAuthenticated, storePermissionVersion, setPermissions]);
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <AntApp>
          <BrowserRouter>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route
                path="/"
                element={
                  <ProtectedRoute>
                    <Layout />
                  </ProtectedRoute>
                }
              >
                <Route index element={<Dashboard />} />
                <Route path="assets" element={<AssetList />} />
                <Route path="assets/discovery" element={<AssetDiscovery />} />
                <Route path="assets/:id" element={<AssetDetail />} />
                <Route path="ops/domains" element={<CertificateList />} />
                <Route path="ops/deployments" element={<DeploymentList />} />
                <Route path="ops/it-management" element={<ITManagement />} />
                <Route path="ops/scheduled-tasks" element={<ScheduledTaskList />} />
                <Route path="ops/health-check" element={<HealthCheckList />} />
                <Route path="ops/health-check/:id" element={<HealthCheckDetail />} />
                <Route path="system/users" element={<UserList />} />
                <Route path="system/roles" element={<RoleList />} />
                <Route path="system/navigation" element={<NavigationList />} />
                <Route path="system/notification-groups" element={<NotificationGroupList />} />
                <Route path="system/notification-records" element={<NotificationRecordList />} />
                <Route path="profile" element={<Profile />} />
                <Route path="alerts/alertmanager" element={<AlertManager />} />
                <Route path="alerts/alertmanager/silences" element={<AlertSilenceList />} />
                <Route path="alerts/alertmanager/templates" element={<AlertTemplateList />} />
                <Route path="alerts/alertmanager/history" element={<AlertHistory />} />
                <Route path="suggestions/submit" element={<SuggestionSubmit />} />
                <Route path="suggestions/manage" element={<SuggestionList />} />
                <Route path="suggestions/manage/:id" element={<SuggestionDetail />} />
                <Route path="suggestions/track" element={<SuggestionTrack />} />
              </Route>
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </BrowserRouter>
        </AntApp>
      </QueryClientProvider>
    </ThemeProvider>
  );
}

export default App;
