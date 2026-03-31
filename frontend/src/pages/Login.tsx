import { useState, useRef } from 'react';
import { Form, Input, Button, Card, Typography, Space, App, Modal, Select } from 'antd';
import { UserOutlined, LockOutlined, DatabaseOutlined, DownloadOutlined, MessageOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { authApi } from '../services/auth';
import { useAuthStore } from '../stores/authStore';
import { itFeedbackApi } from '../services/itFeedback';

const { Title, Text } = Typography;
const { TextArea } = Input;

interface FeedbackFormValues {
  computerType: string;
  usageYears: string;
  lagLevel: string;
  lagScenarios?: string[];
  description?: string;
  contact?: string;
}

const Login = () => {
  const navigate = useNavigate();
  const { setAuth } = useAuthStore();
  const { message } = App.useApp();
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [feedbackVisible, setFeedbackVisible] = useState(false);
  const [feedbackSubmitting, setFeedbackSubmitting] = useState(false);
  const [loginVisible, setLoginVisible] = useState(false);
  const [feedbackForm] = Form.useForm();
  const pendingDownloadRef = useRef(false);

  const handleDownload = async () => {
    const { user, token } = useAuthStore.getState();

    if (!user?.username || !token) {
      setLoginVisible(true);
      pendingDownloadRef.current = true;
      return;
    }

    pendingDownloadRef.current = false;
    setDownloading(true);
    try {
      const response = await fetch('/api/v1/pc-client-version/download', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('下载失败');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `pcinfo_${user.username}.zip`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch {
      message.error('下载失败，请重试');
    } finally {
      setDownloading(false);
    }
  };

  const onFinish = async (values: { username: string; password: string }) => {
    setLoading(true);
    try {
      const tokenData = await authApi.login(values);
      
      if (tokenData.user) {
        setAuth(tokenData.user, tokenData.accessToken, tokenData.refreshToken, tokenData.permissions || []);
      } else {
        const user = await authApi.getCurrentUser();
        setAuth(user, tokenData.accessToken, tokenData.refreshToken, user.permissions || []);
      }
      
      message.success('登录成功，欢迎回来！');
      
      setLoginVisible(false);
      if (pendingDownloadRef.current) {
        pendingDownloadRef.current = false;
        setTimeout(() => {
          handleDownload();
        }, 100);
      } else {
        navigate('/');
      }
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : '登录失败，请检查用户名和密码';
      message.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleFeedbackSubmit = async (values: FeedbackFormValues) => {
    if (feedbackSubmitting) return;
    setFeedbackSubmitting(true);
    try {
      const submitData = {
        ...values,
        lagScenarios: values.lagScenarios?.join(',') || undefined,
      };
      await itFeedbackApi.createITFeedback(submitData);
      message.success('感谢您的反馈，我们会尽快处理！');
      setFeedbackVisible(false);
      feedbackForm.resetFields();
    } catch {
      message.error('提交反馈失败');
    } finally {
      setFeedbackSubmitting(false);
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
          styles={{ body: { padding: '40px' } }}
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
            <Space direction="vertical" size={8}>
              <Space size={16}>
                <Button
                  type="link"
                  loading={downloading}
                  onClick={handleDownload}
                  style={{
                    color: 'var(--primary-400)',
                    fontSize: 13,
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 6,
                    padding: 0,
                  }}
                >
                  <DownloadOutlined />
                  下载 PC 信息采集工具
                </Button>
                <a
                  onClick={() => setFeedbackVisible(true)}
                  style={{
                    color: 'var(--primary-400)',
                    fontSize: 13,
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 6,
                    cursor: 'pointer',
                  }}
                >
                  <MessageOutlined />
                  反馈卡顿问题
                </a>
              </Space>
              <Text style={{ color: 'var(--text-muted)', fontSize: 12, fontFamily: 'var(--font-mono)' }}>
                OpsManager V2.0.0
              </Text>
            </Space>
          </div>
        </Card>
      </div>

      {/* Feedback Modal */}
      <Modal
        title={
          <Space>
            <MessageOutlined />
            <span>反馈办公卡顿问题</span>
          </Space>
        }
        open={feedbackVisible}
        onCancel={() => setFeedbackVisible(false)}
        footer={null}
        width={500}
        styles={{
          body: { paddingTop: 16 },
          mask: { backdropFilter: 'blur(4px)' }
        }}
      >
        <Form
          form={feedbackForm}
          layout="vertical"
          onFinish={handleFeedbackSubmit}
          style={{ marginTop: 16 }}
        >
          <Form.Item
            name="computerType"
            label="电脑类型"
            rules={[{ required: true, message: '请选择电脑类型' }]}
          >
            <Select placeholder="请选择电脑类型">
              <Select.Option value="desktop">台式机</Select.Option>
              <Select.Option value="laptop">笔记本</Select.Option>
              <Select.Option value="workstation">工作站</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="usageYears"
            label="电脑使用年限"
            rules={[{ required: true, message: '请选择使用年限' }]}
          >
            <Select placeholder="请选择使用年限">
              <Select.Option value="less1">1年以内</Select.Option>
              <Select.Option value="1-3">1-3年</Select.Option>
              <Select.Option value="3-5">3-5年</Select.Option>
              <Select.Option value="more5">5年以上</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="lagLevel"
            label="卡顿程度"
            rules={[{ required: true, message: '请选择卡顿程度' }]}
          >
            <Select placeholder="请选择卡顿程度">
              <Select.Option value="1">轻微卡顿 - 偶尔卡顿，不影响工作</Select.Option>
              <Select.Option value="2">一般卡顿 - 经常卡顿，影响工作效率</Select.Option>
              <Select.Option value="3">严重卡顿 - 频繁卡顿，严重影响工作</Select.Option>
              <Select.Option value="4">无法使用 - 基本无法正常工作</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="lagScenarios"
            label="卡顿场景（可多选）"
          >
            <Select mode="multiple" placeholder="请选择卡顿场景">
              <Select.Option value="startup">开机启动</Select.Option>
              <Select.Option value="office">办公软件（Word/Excel等）</Select.Option>
              <Select.Option value="browser">浏览器使用</Select.Option>
              <Select.Option value="video">视频会议/播放</Select.Option>
              <Select.Option value="file">文件操作（复制/打开等）</Select.Option>
              <Select.Option value="multitask">多任务切换</Select.Option>
              <Select.Option value="other">其他</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="description"
            label="详细描述"
          >
            <TextArea
              rows={4}
              placeholder="请详细描述卡顿情况，例如：具体在什么操作时卡顿、卡顿持续多长时间等"
              maxLength={500}
              showCount
            />
          </Form.Item>

          <Form.Item
            name="contact"
            label="联系方式（选填）"
          >
            <Input placeholder="请输入手机号或邮箱，方便我们联系您" />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0, marginTop: 24 }}>
            <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
              <Button onClick={() => setFeedbackVisible(false)} disabled={feedbackSubmitting}>
                取消
              </Button>
              <Button type="primary" htmlType="submit" loading={feedbackSubmitting}>
                提交反馈
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* Login Modal for Download */}
      <Modal
        title={
          <Space>
            <UserOutlined />
            <span>请先登录</span>
          </Space>
        }
        open={loginVisible}
        onCancel={() => {
          setLoginVisible(false);
          pendingDownloadRef.current = false;
        }}
        footer={null}
        width={400}
        styles={{
          body: { paddingTop: 16 },
          mask: { backdropFilter: 'blur(4px)' }
        }}
      >
        <Form
          name="login-modal"
          initialValues={{ remember: true }}
          onFinish={onFinish}
          autoComplete="off"
          layout="vertical"
          size="large"
          style={{ marginTop: 16 }}
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
            <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
              <Button onClick={() => setLoginVisible(false)}>
                取消
              </Button>
              <Button type="primary" htmlType="submit" loading={loading}>
                登录并下载
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default Login;
