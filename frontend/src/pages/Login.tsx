import { useState } from 'react';
import { Form, Input, Button, Card, message, Typography, Space } from 'antd';
import { UserOutlined, LockOutlined, DatabaseOutlined } from '@ant-design/icons';
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
        background: 'var(--bg-primary)',
        position: 'relative',
        overflow: 'hidden',
      }}
      className="tech-grid"
    >
      {/* Animated Background Elements */}
      <div
        style={{
          position: 'absolute',
          top: '10%',
          left: '10%',
          width: 300,
          height: 300,
          background: 'radial-gradient(circle, rgba(0,212,255,0.15) 0%, transparent 70%)',
          borderRadius: '50%',
          animation: 'float 6s ease-in-out infinite',
        }}
      ></div>
      <div
        style={{
          position: 'absolute',
          bottom: '20%',
          right: '5%',
          width: 400,
          height: 400,
          background: 'radial-gradient(circle, rgba(168,85,247,0.1) 0%, transparent 70%)',
          borderRadius: '50%',
          animation: 'float 8s ease-in-out infinite reverse',
        }}
      ></div>

      {/* Left Side - Branding */}
      <div
        style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          padding: '48px',
          position: 'relative',
          zIndex: 1,
        }}
      >
        <div
          style={{
            width: 120,
            height: 120,
            borderRadius: '24px',
            background: 'linear-gradient(135deg, rgba(0,212,255,0.2), rgba(168,85,247,0.2))',
            backdropFilter: 'blur(20px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginBottom: 32,
            border: '1px solid rgba(0,212,255,0.3)',
            boxShadow: '0 0 40px rgba(0,212,255,0.2)',
            animation: 'float 4s ease-in-out infinite',
          }}
        >
          <DatabaseOutlined style={{ fontSize: 56, color: 'var(--primary-500)' }} />
        </div>
        <Title
          level={1}
          style={{
            color: '#fff',
            marginBottom: 16,
            fontSize: 52,
            fontFamily: 'var(--font-display)',
            fontWeight: 700,
            letterSpacing: '-0.02em',
          }}
          className="text-gradient"
        >
          OpsManager
        </Title>
        <Text
          style={{
            color: 'var(--text-secondary)',
            fontSize: 18,
            textAlign: 'center',
            maxWidth: 400,
            lineHeight: 1.6,
          }}
        >
          现代化的运维管理平台
          <br />
          <span style={{ color: 'var(--primary-400)', fontFamily: 'var(--font-mono)', fontSize: 14 }}>
            Modern Ops Management Platform
          </span>
        </Text>

        {/* Feature Pills */}
        <Space size={16} style={{ marginTop: 48 }}>
          {['资产管理', '监控告警', '自动化运维'].map((feature, index) => (
            <div
              key={index}
              style={{
                padding: '8px 16px',
                background: 'rgba(0,212,255,0.1)',
                border: '1px solid rgba(0,212,255,0.2)',
                borderRadius: '20px',
                color: 'var(--primary-400)',
                fontSize: 13,
                fontFamily: 'var(--font-mono)',
              }}
            >
              {feature}
            </div>
          ))}
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
            background: 'var(--bg-card)',
            border: '1px solid var(--border-color)',
            borderRadius: 'var(--radius-lg)',
            boxShadow: 'var(--shadow-card)',
          }}
          bodyStyle={{ padding: '40px' }}
        >
          <div style={{ textAlign: 'center', marginBottom: 32 }}>
            <div
              style={{
                width: 60,
                height: 60,
                borderRadius: 'var(--radius-md)',
                background: 'linear-gradient(135deg, var(--primary-500), var(--accent-purple))',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 16px',
              }}
            >
              <UserOutlined style={{ fontSize: 28, color: '#fff' }} />
            </div>
            <Title
              level={3}
              style={{
                marginBottom: 8,
                color: 'var(--text-primary)',
                fontFamily: 'var(--font-display)',
              }}
            >
              欢迎登录
            </Title>
            <Text style={{ color: 'var(--text-secondary)' }}>
              请输入您的账号和密码
            </Text>
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
                prefix={<UserOutlined style={{ color: 'var(--text-tertiary)' }} />}
                placeholder="用户名"
                style={{
                  background: 'var(--bg-tertiary)',
                  border: '1px solid var(--border-color)',
                  borderRadius: 'var(--radius-md)',
                  color: 'var(--text-primary)',
                }}
              />
            </Form.Item>

            <Form.Item
              name="password"
              rules={[{ required: true, message: '请输入密码' }]}
            >
              <Input.Password
                prefix={<LockOutlined style={{ color: 'var(--text-tertiary)' }} />}
                placeholder="密码"
                style={{
                  background: 'var(--bg-tertiary)',
                  border: '1px solid var(--border-color)',
                  borderRadius: 'var(--radius-md)',
                  color: 'var(--text-primary)',
                }}
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
                  height: 48,
                  fontSize: 16,
                  fontWeight: 600,
                  background: 'linear-gradient(135deg, var(--primary-500), var(--primary-600))',
                  border: 'none',
                  borderRadius: 'var(--radius-md)',
                  boxShadow: '0 0 20px rgba(0,212,255,0.3)',
                }}
              >
                登 录
              </Button>
            </Form.Item>
          </Form>

          <div
            style={{
              marginTop: 24,
              textAlign: 'center',
              paddingTop: 24,
              borderTop: '1px solid var(--border-color)',
            }}
          >
            <Text style={{ color: 'var(--text-muted)', fontSize: 12, fontFamily: 'var(--font-mono)' }}>
              OpsManager V2.0.0
            </Text>
          </div>
        </Card>
      </div>
    </div>
  );
};

export default Login;
