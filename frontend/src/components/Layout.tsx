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
} from '@ant-design/icons';
import { useState } from 'react';
import { useAuthStore } from '../stores/authStore';

const { Header, Sider, Content } = AntLayout;

const Layout = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuthStore();
  const [collapsed, setCollapsed] = useState(false);

  const menuItems = [
    {
      key: '/',
      icon: <DashboardOutlined />,
      label: '仪表盘',
    },
    {
      key: '/assets',
      icon: <DatabaseOutlined />,
      label: '资产管理',
    },
    {
      key: '/monitors',
      icon: <MonitorOutlined />,
      label: '监控管理',
    },
    {
      key: '/alerts',
      icon: <AlertOutlined />,
      label: (
        <Space>
          告警事件
          <Badge count={2} size="small" style={{ backgroundColor: '#ff4d4f' }} />
        </Space>
      ),
    },
    {
      key: '/deployments',
      icon: <DeploymentUnitOutlined />,
      label: '发布记录',
    },
    {
      key: '/certificates',
      icon: <SafetyCertificateOutlined />,
      label: '证书管理',
    },
    {
      key: '/roles',
      icon: <SafetyOutlined />,
      label: '角色管理',
    },
  ];

  const userMenuItems = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: '个人中心',
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: '系统设置',
    },
    {
      type: 'divider' as const,
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      danger: true,
      onClick: () => {
        logout();
        navigate('/login');
      },
    },
  ];

  return (
    <AntLayout style={{ minHeight: '100vh', background: 'var(--bg-color)' }}>
      <Sider
        theme="light"
        width={220}
        collapsed={collapsed}
        collapsedWidth={80}
        style={{
          boxShadow: 'var(--shadow-md)',
          zIndex: 100,
          background: 'linear-gradient(180deg, #ffffff 0%, #f8fafc 100%)',
        }}
      >
        <div
          style={{
            height: 64,
            display: 'flex',
            alignItems: 'center',
            justifyContent: collapsed ? 'center' : 'flex-start',
            padding: collapsed ? 0 : '0 20px',
            borderBottom: '1px solid rgba(0,0,0,0.06)',
            background: 'linear-gradient(135deg, #1890ff 0%, #36cfc9 100%)',
          }}
        >
          {!collapsed && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: 'var(--radius-md)',
                  background: 'rgba(255,255,255,0.2)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  backdropFilter: 'blur(10px)',
                }}
              >
                <DatabaseOutlined style={{ color: '#fff', fontSize: 20 }} />
              </div>
              <div>
                <h2
                  style={{
                    margin: 0,
                    fontSize: 18,
                    fontWeight: 600,
                    color: '#fff',
                    letterSpacing: '0.5px',
                  }}
                >
                  OpsManager
                </h2>
                <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.8)' }}>
                  运维管理平台
                </span>
              </div>
            </div>
          )}
          {collapsed && (
            <div
              style={{
                width: 40,
                height: 40,
                borderRadius: 'var(--radius-md)',
                background: 'rgba(255,255,255,0.2)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <DatabaseOutlined style={{ color: '#fff', fontSize: 24 }} />
            </div>
          )}
        </div>
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{
            borderRight: 0,
            padding: '12px 8px',
            background: 'transparent',
          }}
          theme="light"
        />
      </Sider>
      <AntLayout style={{ background: 'var(--bg-color)' }}>
        <Header
          style={{
            background: '#fff',
            padding: '0 24px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            borderBottom: '1px solid rgba(0,0,0,0.06)',
            boxShadow: 'var(--shadow-sm)',
            zIndex: 99,
          }}
        >
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed(!collapsed)}
            style={{ fontSize: 16 }}
          />
          <Space size={24}>
            <Tooltip title="通知">
              <Badge count={5} size="small">
                <Button type="text" icon={<BellOutlined style={{ fontSize: 18 }} />} />
              </Badge>
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
            background: '#fff',
            borderRadius: 'var(--radius-lg)',
            minHeight: 280,
            boxShadow: 'var(--shadow-sm)',
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
