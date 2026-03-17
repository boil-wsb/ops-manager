import { Layout as AntLayout, Menu, Button, Avatar, Dropdown, Badge, Space, Tooltip } from 'antd';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import {
  DashboardOutlined,
  DatabaseOutlined,
  MonitorOutlined,
  AlertOutlined,
  DeploymentUnitOutlined,
  SafetyCertificateOutlined,
  LogoutOutlined,
  UserOutlined,
  BellOutlined,
  SettingOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  SafetyOutlined,
  TeamOutlined,
  LinkOutlined,
  SunOutlined,
  MoonOutlined,
} from '@ant-design/icons';
import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAuthStore } from '../stores/authStore';
import { usePermission } from '../hooks/usePermission';
import { useThemeStore } from '../stores/themeStore';
import api from '../services/api';

const { Header, Sider, Content } = AntLayout;

interface MenuItemType {
  key: string;
  icon?: React.ReactNode;
  label?: React.ReactNode;
  permission?: string;
  children?: MenuItemType[];
}

const Layout = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuthStore();
  const { hasPermission } = usePermission();
  const { mode, toggleMode } = useThemeStore();
  const [collapsed, setCollapsed] = useState(false);

  const { data: alertData } = useQuery({
    queryKey: ['alerts-count'],
    queryFn: async () => {
      try {
        const response = await api.get('/monitor/alerts?status=firing');
        return response.data;
      } catch (error) {
        return { total: 0 };
      }
    },
    refetchInterval: 60000,
  });

  const firingAlertsCount = alertData?.total || 0;

  const menuItems: MenuItemType[] = useMemo(
    () => [
      {
        key: '/dashboard',
        icon: <DashboardOutlined />,
        label: '仪表盘',
      },
      {
        key: '/assets',
        icon: <DatabaseOutlined />,
        label: '资产管理',
        permission: 'asset:read',
      },
      {
        key: '/monitor',
        icon: <MonitorOutlined />,
        label: '监控管理',
        permission: 'monitor:read',
        children: [
          { key: '/monitor/list', label: '监控列表' },
          { key: '/monitor/alerts', label: '告警管理' },
          { key: '/monitor/domains', label: '域名监控' },
        ],
      },
      {
        key: '/ops',
        icon: <DeploymentUnitOutlined />,
        label: '运维管理',
        permission: 'deployment:read',
        children: [
          { key: '/ops/deployments', label: '发布记录' },
        ],
      },
      {
        key: '/system',
        icon: <SettingOutlined />,
        label: '系统管理',
        permission: 'setting:read',
        children: [
          { key: '/system/users', label: '用户管理', permission: 'user:read' },
          { key: '/system/roles', label: '角色管理', permission: 'role:read' },
          { key: '/system/navigation', label: '导航管理', permission: 'navigation:read' },
        ],
      },
    ],
    [hasPermission]
  );

  const filterMenuItems = (items: MenuItemType[]): MenuItemType[] => {
    return items
      .filter((item) => !item.permission || hasPermission(item.permission))
      .map((item) => ({
        ...item,
        children: item.children ? filterMenuItems(item.children) : undefined,
      }));
  };

  const filteredMenuItems = filterMenuItems(menuItems);

  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key);
  };

  const getSelectedKeys = () => {
    const path = location.pathname;
    if (path === '/') return ['/dashboard'];
    return [path];
  };

  const getOpenKeys = () => {
    const path = location.pathname;
    const parts = path.split('/').filter(Boolean);
    if (parts.length > 1) {
      return ['/' + parts[0]];
    }
    return [];
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const userMenuItems = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: '个人设置',
      onClick: () => navigate('/profile'),
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      onClick: handleLogout,
    },
  ];

  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        style={{
          overflow: 'auto',
          height: '100vh',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
          background: '#001529',
        }}
      >
        <div
          style={{
            height: 64,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderBottom: '1px solid rgba(255,255,255,0.1)',
          }}
        >
          <SafetyOutlined style={{ fontSize: 24, color: '#1890ff' }} />
          {!collapsed && (
            <span
              style={{
                marginLeft: 12,
                fontSize: 18,
                fontWeight: 'bold',
                color: '#fff',
              }}
            >
              OpsManager
            </span>
          )}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={getSelectedKeys()}
          defaultOpenKeys={getOpenKeys()}
          items={filteredMenuItems}
          onClick={handleMenuClick}
        />
      </Sider>
      <AntLayout style={{ marginLeft: collapsed ? 80 : 200, transition: 'margin-left 0.2s' }}>
        <Header
          style={{
            position: 'sticky',
            top: 0,
            zIndex: 100,
            padding: '0 24px',
            background: 'var(--header-bg)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: '1px solid var(--border-color)',
            boxShadow: 'var(--shadow-sm)',
          }}
        >
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed(!collapsed)}
            style={{ fontSize: 16 }}
          />
          <Space size={24}>
            <Tooltip title="告警">
              <Badge count={firingAlertsCount} size="small">
                <Button type="text" icon={<BellOutlined style={{ fontSize: 18 }} />} />
              </Badge>
            </Tooltip>
            <Tooltip title={mode === 'dark' ? '切换到浅色模式' : '切换到深色模式'}>
              <Button
                type="text"
                icon={mode === 'dark' ? <SunOutlined style={{ fontSize: 18 }} /> : <MoonOutlined style={{ fontSize: 18 }} />}
                onClick={toggleMode}
              />
            </Tooltip>
            <Dropdown menu={{ items: userMenuItems }} placement="bottomRight" arrow>
              <Button
                type="text"
                style={{
                  height: 40,
                  padding: '4px 12px',
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--bg-color)',
                }}
              >
                <Space>
                  <Avatar
                    icon={<UserOutlined />}
                    size="small"
                    style={{
                      background: 'linear-gradient(135deg, #1890ff 0%, #36cfc9 100%)',
                    }}
                  />
                  <span style={{ fontWeight: 500 }}>{user?.username || '用户'}</span>
                </Space>
              </Button>
            </Dropdown>
          </Space>
        </Header>
        <Content
          style={{
            margin: 24,
            padding: 24,
            background: 'var(--bg-card)',
            borderRadius: 'var(--radius-lg)',
            minHeight: 'calc(100vh - 112px)',
            boxShadow: 'var(--shadow-sm)',
            overflow: 'auto',
          }}
        >
          <div className="animate-fade-in">
            <Outlet />
          </div>
        </Content>
      </AntLayout>
    </AntLayout>
  );
};

export default Layout;
