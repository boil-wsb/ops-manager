import { useEffect } from 'react';
import {
  Modal,
  Form,
  Input,
  message,
} from 'antd';
import { roleApi, type Role, type CreateRoleRequest, type UpdateRoleRequest } from '../../services/permissions';

interface RoleFormModalProps {
  visible: boolean;
  onCancel: () => void;
  onSuccess: () => void;
  role: Role | null;
}

const RoleFormModal = ({ visible, onCancel, onSuccess, role }: RoleFormModalProps) => {
  const [form] = Form.useForm();
  const isEditing = !!role;

  useEffect(() => {
    if (visible && role) {
      form.setFieldsValue({
        name: role.name,
        description: role.description,
      });
    } else {
      form.resetFields();
    }
  }, [visible, role, form]);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();

      if (isEditing) {
        // Update existing role
        const updateData: UpdateRoleRequest = {
          name: values.name,
          description: values.description,
        };
        await roleApi.updateRole(role!.id, updateData);
        message.success('角色更新成功');
      } else {
        // Create new role
        const createData: CreateRoleRequest = {
          name: values.name,
          description: values.description,
          permission_ids: [],
        };
        await roleApi.createRole(createData);
        message.success('角色创建成功');
      }

      onSuccess();
    } catch (error: any) {
      message.error(error.response?.data?.detail || '操作失败');
    }
  };

  return (
    <Modal
      title={isEditing ? '编辑角色' : '创建角色'}
      open={visible}
      onOk={handleSubmit}
      onCancel={onCancel}
      okText={isEditing ? '更新' : '创建'}
      cancelText="取消"
      destroyOnHidden
    >
      <Form
        form={form}
        layout="vertical"
        style={{ marginTop: 20 }}
      >
        <Form.Item
          name="name"
          label="角色名称"
          rules={[
            { required: true, message: '请输入角色名称' },
            { min: 2, message: '角色名称至少2个字符' },
            { max: 50, message: '角色名称最多50个字符' },
          ]}
        >
          <Input placeholder="请输入角色名称" />
        </Form.Item>

        <Form.Item
          name="description"
          label="描述"
          rules={[{ max: 255, message: '描述最多255个字符' }]}
        >
          <Input.TextArea
            rows={3}
            placeholder="请输入角色描述（可选）"
          />
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default RoleFormModal;
