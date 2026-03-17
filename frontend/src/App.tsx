import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { ConfigProvider, theme, App as AntApp } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useEffect } from 'react';

import { useAuthStore } from './stores/authStore';
import { useThemeStore } from './stores/themeStore';
import { usePermission } from './hooks/usePermission';
import { getRoutePermission } from './config/routePermissions';
import { lightTheme, darkTheme } from './config/theme';
import Login from './pages/Login';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import AssetList from './pages/Assets/AssetList';
import AssetDetail from './pages/Assets/AssetDetail';
import AssetDiscovery from './pages/Assets/AssetDiscovery';
import MonitorList from './pages/Monitor/MonitorList';
import AlertList from './pages/Monitor/AlertList';
import DeploymentList from './pages/Ops/DeploymentList';
import CertificateList from './pages/Ops/CertificateList';
import RoleList from './pages/Roles/RoleList';
import UserList from './pages/Users/UserList';
import Profile from './pages/Profile/Profile';
import NavigationList from './pages/System/NavigationList';
import Forbidden from './pages/Forbidden';

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
  const algorithm = mode === 'dark' ? theme.darkAlgorithm : theme.defaultAlgorithm;

  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        ...currentTheme,
        algorithm,
      }}
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
                <Route path="monitor/list" element={<MonitorList />} />
                <Route path="monitor/alerts" element={<AlertList />} />
                <Route path="monitor/domains" element={<CertificateList />} />
                <Route path="ops/deployments" element={<DeploymentList />} />
                <Route path="system/users" element={<UserList />} />
                <Route path="system/roles" element={<RoleList />} />
                <Route path="system/navigation" element={<NavigationList />} />
                <Route path="profile" element={<Profile />} />
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
