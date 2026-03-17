import { useEffect, useState } from 'react';
import { Modal, Form, Input, Select, Switch, App } from 'antd';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { userApi } from '../../services/users';
import { roleApi, type Role } from '../../services/roles';
import type { User } from '../../types';

const { Option } = Select;

interface UserFormModalProps {
  open: boolean;
  onClose: () => void;
  user?: User | null;
}

const UserFormModal: React.FC<UserFormModalProps> = ({ open, onClose, user }) => {
  const [form] = Form.useForm();
  const queryClient = useQueryClient();
  const { message } = App.useApp();
  const isEdit = !!user;

  const { data: rolesData } = useQuery({
    queryKey: ['roles'],
    queryFn: () => roleApi.getRoles(),
  });

  const [selectedRoleIds, setSelectedRoleIds] = useState<number[]>([]);

  useEffect(() => {
    if (open) {
      if (user) {
        form.setFieldsValue({
          username: user.username,
          email: user.email,
          fullName: user.fullName,
          isActive: user.isActive ?? true,
          isSuperuser: user.isSuperuser ?? false,
        });
        setSelectedRoleIds(user.roles?.map((r: { id: number; name: string }) => r.id) || []);
      } else {
        form.setFieldsValue({
          username: '',
          email: '',
          full_name: '',
          is_active: true,
          is_superuser: false,
        });
        setSelectedRoleIds([]);
      }
    }
  }, [open, user, form]);

  const createMutation = useMutation({
    mutationFn: userApi.createUser,
    onSuccess: () => {
      message.success('用户创建成功');
      queryClient.invalidateQueries({ queryKey: ['users'] });
      handleClose();
    },
    onError: () => {
      message.error('用户创建失败');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<User> }) =>
      userApi.updateUser(id, data),
    onSuccess: () => {
      message.success('用户更新成功');
      queryClient.invalidateQueries({ queryKey: ['users'] });
      handleClose();
    },
    onError: () => {
      message.error('用户更新失败');
    },
  });

  const handleClose = () => {
    form.resetFields();
    setSelectedRoleIds([]);
    onClose();
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      const userData = {
        ...values,
        role_ids: selectedRoleIds,
      };

      if (isEdit && user) {
        updateMutation.mutate({ id: user.id, data: userData });
      } else {
        createMutation.mutate(userData);
      }
    } catch (error) {
      console.error('Validation failed:', error);
    }
  };

  const isLoading = createMutation.isPending || updateMutation.isPending;

  const roles = rolesData?.items || [];

  return (
    <Modal
      title={isEdit ? '编辑用户' : '新增用户'}
      open={open}
      onCancel={handleClose}
      onOk={handleSubmit}
      confirmLoading={isLoading}
      width={600}
      destroyOnHidden
      mask={{ closable: false }}
      keyboard={false}
    >
      <Form form={form} layout="vertical" preserve={false}>
        <Form.Item
          name="username"
          label="用户名"
          rules={[{ required: true, message: '请输入用户名' }]}
        >
          <Input placeholder="请输入用户名" disabled={isEdit} />
        </Form.Item>

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
          name="full_name"
          label="姓名"
        >
          <Input placeholder="请输入姓名" />
        </Form.Item>

        {!isEdit && (
          <Form.Item
            name="password"
            label="密码"
            rules={[
              { required: true, message: '请输入密码' },
              { min: 8, message: '密码至少8个字符' },
            ]}
          >
            <Input.Password placeholder="请输入密码" />
          </Form.Item>
        )}

        <Form.Item
          name="is_active"
          label="状态"
          valuePropName="checked"
          initialValue={true}
        >
          <Switch checkedChildren="启用" unCheckedChildren="禁用" />
        </Form.Item>

        <Form.Item
          name="is_superuser"
          label="超级管理员"
          valuePropName="checked"
          initialValue={false}
        >
          <Switch checkedChildren="是" unCheckedChildren="否" />
        </Form.Item>

        <Form.Item label="角色">
          <Select
            mode="multiple"
            placeholder="请选择角色"
            value={selectedRoleIds}
            onChange={setSelectedRoleIds}
            style={{ width: '100%' }}
          >
            {roles.map((role: Role) => (
              <Option key={role.id} value={role.id}>
                {role.name}
              </Option>
            ))}
          </Select>
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default UserFormModal;
