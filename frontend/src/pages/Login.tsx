import { useState } from 'react';
import { Form, Input, Button, Card, message, Typography, Space, Divider } from 'antd';
import { UserOutlined, LockOutlined, SafetyOutlined, DatabaseOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { authApi } from '../services/auth';
import { useAuthStore } from '../stores/authStore';

const { Title, Text } = Typography;

const Login = () => {
  const navigate = useNavigate();
  const { setAuth } = useAuthStore();
  const [loading, setLoading] = useState(false);

  const onFinish = async (values: { username: string; password: string }) => {
    setLoading(true);
    try {
      const tokenData = await authApi.login(values);
      const user = await authApi.getCurrentUser();
      setAuth(user, tokenData.accessToken);
      message.success('登录成功，欢迎回来！');
      navigate('/');
    } catch (error: any) {
      message.error(error.response?.data?.message || '登录失败，请检查用户名和密码');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Background Pattern */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: `
            radial-gradient(circle at 20% 80%, rgba(120, 119, 198, 0.3) 0%, transparent 50%),
            radial-gradient(circle at 80% 20%, rgba(255, 255, 255, 0.1) 0%, transparent 50%)
          `,
        }}
      />

      {/* Left Side - Branding */}
      <div
        style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          padding: '48px',
          color: '#fff',
          position: 'relative',
          zIndex: 1,
        }}
      >
        <div
          style={{
            width: 120,
            height: 120,
            borderRadius: '24px',
            background: 'rgba(255,255,255,0.15)',
            backdropFilter: 'blur(20px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginBottom: 32,
            boxShadow: '0 8px 32px rgba(0,0,0,0.2)',
          }}
        >
          <DatabaseOutlined style={{ fontSize: 64, color: '#fff' }} />
        </div>
        <Title level={1} style={{ color: '#fff', marginBottom: 16, fontSize: 48 }}>
          OpsManager
        </Title>
        <Text style={{ color: 'rgba(255,255,255,0.85)', fontSize: 18, textAlign: 'center', maxWidth: 400 }}>
          现代化的运维管理平台，让运维工作更高效、更智能
        </Text>
        <Space size={32} style={{ marginTop: 48 }}>
          <div style={{ textAlign: 'center' }}>
            <SafetyOutlined style={{ fontSize: 32, color: '#fff', marginBottom: 8 }} />
            <div style={{ color: 'rgba(255,255,255,0.8)', fontSize: 14 }}>安全可靠</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <DatabaseOutlined style={{ fontSize: 32, color: '#fff', marginBottom: 8 }} />
            <div style={{ color: 'rgba(255,255,255,0.8)', fontSize: 14 }}>资产管理</div>
          </div>
        </Space>
      </div>

      {/* Right Side - Login Form */}
      <div
        style={{
          width: 480,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          padding: '48px',
          position: 'relative',
          zIndex: 1,
        }}
      >
        <Card
          style={{
            width: '100%',
            maxWidth: 400,
            borderRadius: 'var(--radius-lg)',
            boxShadow: 'var(--shadow-lg)',
            border: 'none',
          }}
          bodyStyle={{ padding: '40px' }}
        >
          <div style={{ textAlign: 'center', marginBottom: 32 }}>
            <Title level={3} style={{ marginBottom: 8 }}>欢迎登录</Title>
            <Text type="secondary">请输入您的账号和密码</Text>
          </div>

          <Form
            name="login"
            initialValues={{ remember: true }}
            onFinish={onFinish}
            autoComplete="off"
            layout="vertical"
            size="large"
          >
            <Form.Item
              name="username"
              rules={[{ required: true, message: '请输入用户名' }]}
            >
              <Input
                prefix={<UserOutlined style={{ color: '#bfbfbf' }} />}
                placeholder="用户名"
                style={{ borderRadius: 'var(--radius-md)' }}
              />
            </Form.Item>

            <Form.Item
              name="password"
              rules={[{ required: true, message: '请输入密码' }]}
            >
              <Input.Password
                prefix={<LockOutlined style={{ color: '#bfbfbf' }} />}
                placeholder="密码"
                style={{ borderRadius: 'var(--radius-md)' }}
              />
            </Form.Item>

            <Form.Item style={{ marginBottom: 0, marginTop: 24 }}>
              <Button
                type="primary"
                htmlType="submit"
                loading={loading}
                block
                size="large"
                style={{
                  borderRadius: 'var(--radius-md)',
                  height: 48,
                  fontSize: 16,
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  border: 'none',
                }}
              >
                登 录
              </Button>
            </Form.Item>
          </Form>

          <Divider style={{ margin: '24px 0' }}>
            <Text type="secondary" style={{ fontSize: 12 }}>OpsManager V2</Text>
          </Divider>
        </Card>
      </div>
    </div>
  );
};

export default Login;
