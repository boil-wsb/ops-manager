import { Card, Form, Input, Button, App, Descriptions, Divider } from 'antd';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { UserOutlined, LockOutlined, SaveOutlined } from '@ant-design/icons';
import { useAuthStore } from '../../stores/authStore';
import { userApi } from '../../services/users';
import type { User } from '../../types';

const Profile = () => {
  const { user, setUser } = useAuthStore();
  const queryClient = useQueryClient();
  const { message } = App.useApp();
  const [passwordForm] = Form.useForm();
  const [profileForm] = Form.useForm();

  const updateProfileMutation = useMutation({
    mutationFn: (data: Partial<User>) => {
      if (!user) throw new Error('User not found');
      return userApi.updateUser(user.id, data);
    },
    onSuccess: (updatedUser) => {
      message.success('个人信息更新成功');
      setUser(updatedUser);
      queryClient.invalidateQueries({ queryKey: ['user'] });
    },
    onError: () => {
      message.error('更新失败');
    },
  });

  const changePasswordMutation = useMutation({
    mutationFn: ({ newPassword }: { oldPassword: string; newPassword: string }) => {
      if (!user) throw new Error('User not found');
      return userApi.resetPassword(user.id, newPassword);
    },
    onSuccess: () => {
      message.success('密码修改成功');
      passwordForm.resetFields();
    },
    onError: () => {
      message.error('密码修改失败');
    },
  });

  const handleProfileSubmit = async () => {
    try {
      const values = await profileForm.validateFields();
      updateProfileMutation.mutate(values);
    } catch (error) {
      console.error('Validation failed:', error);
    }
  };

  const handlePasswordSubmit = async () => {
    try {
      const values = await passwordForm.validateFields();
      if (values.newPassword !== values.confirmPassword) {
        message.error('两次输入的密码不一致');
        return;
      }
      changePasswordMutation.mutate({
        oldPassword: values.oldPassword,
        newPassword: values.newPassword,
      });
    } catch (error) {
      console.error('Validation failed:', error);
    }
  };

  if (!user) {
    return <div>请先登录</div>;
  }

  return (
    <div>
      <Card style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
          <div
            style={{
              width: 80,
              height: 80,
              borderRadius: '50%',
              background: 'linear-gradient(135deg, #1890ff 0%, #36cfc9 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <UserOutlined style={{ fontSize: 40, color: '#fff' }} />
          </div>
          <div>
            <h2 style={{ margin: 0, marginBottom: 8 }}>{user.fullName || user.username}</h2>
            <p style={{ margin: 0, color: 'var(--text-secondary)' }}>{user.email}</p>
            <p style={{ margin: 0, color: 'var(--text-tertiary)', fontSize: 12 }}>
              {user.isSuperuser ? '超级管理员' : '普通用户'}
            </p>
          </div>
        </div>
      </Card>

      <Card>
        <Descriptions bordered column={2}>
          <Descriptions.Item label="用户名">{user.username}</Descriptions.Item>
          <Descriptions.Item label="邮箱">{user.email}</Descriptions.Item>
          <Descriptions.Item label="姓名">{user.fullName || '-'}</Descriptions.Item>
          <Descriptions.Item label="状态">
            {user.isActive ? '启用' : '禁用'}
          </Descriptions.Item>
          <Descriptions.Item label="超级管理员">
            {user.isSuperuser ? '是' : '否'}
          </Descriptions.Item>
          <Descriptions.Item label="最后登录">
            {user.lastLogin ? new Date(user.lastLogin).toLocaleString() : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="创建时间">
            {new Date(user.createdAt).toLocaleString()}
          </Descriptions.Item>
          <Descriptions.Item label="更新时间">
            {new Date(user.updatedAt).toLocaleString()}
          </Descriptions.Item>
        </Descriptions>

        <Divider />

        <h3>修改个人信息</h3>
        <Form
          form={profileForm}
          layout="vertical"
          initialValues={{
            email: user.email,
            fullName: user.fullName,
          }}
          style={{ marginTop: 24 }}
        >
          <Form.Item
            name="email"
            label="邮箱"
            rules={[
              { required: true, message: '请输入邮箱' },
              { type: 'email', message: '请输入有效的邮箱地址' },
            ]}
          >
            <Input placeholder="请输入邮箱" />
          </Form.Item>

          <Form.Item
            name="fullName"
            label="姓名"
          >
            <Input placeholder="请输入姓名" />
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              onClick={handleProfileSubmit}
              loading={updateProfileMutation.isPending}
            >
              保存修改
            </Button>
          </Form.Item>
        </Form>

        <Divider />

        <h3>修改密码</h3>
        <Form
          form={passwordForm}
          layout="vertical"
          style={{ marginTop: 24 }}
        >
          <Form.Item
            name="oldPassword"
            label="当前密码"
            rules={[{ required: true, message: '请输入当前密码' }]}
          >
            <Input.Password placeholder="请输入当前密码" prefix={<LockOutlined />} />
          </Form.Item>

          <Form.Item
            name="newPassword"
            label="新密码"
            rules={[
              { required: true, message: '请输入新密码' },
              { min: 8, message: '密码至少8个字符' },
            ]}
          >
            <Input.Password placeholder="请输入新密码" prefix={<LockOutlined />} />
          </Form.Item>

          <Form.Item
            name="confirmPassword"
            label="确认新密码"
            rules={[
              { required: true, message: '请确认新密码' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('newPassword') === value) {
                    return Promise.resolve();
                  }
                  return Promise.reject(new Error('两次输入的密码不一致'));
                },
              }),
            ]}
          >
            <Input.Password placeholder="请再次输入新密码" prefix={<LockOutlined />} />
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              icon={<LockOutlined />}
              onClick={handlePasswordSubmit}
              loading={changePasswordMutation.isPending}
            >
              修改密码
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
};

export default Profile;
