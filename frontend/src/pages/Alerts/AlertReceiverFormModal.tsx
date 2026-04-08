import { useEffect } from 'react';
import { Modal, Form, Input, Select, Switch, App } from 'antd';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import type { AlertReceiver, AlertReceiverCreate, AlertReceiverUpdate } from '../../types';
import alertApi from '../../services/alert';

interface AlertReceiverFormModalProps {
  visible: boolean;
  receiver: AlertReceiver | null;
  onClose: () => void;
}

const AlertReceiverFormModal = ({ visible, receiver, onClose }: AlertReceiverFormModalProps) => {
  const [form] = Form.useForm();
  const queryClient = useQueryClient();
  const { message } = App.useApp();
  const isEdit = !!receiver;

  useEffect(() => {
    if (visible && receiver) {
      form.setFieldsValue({
        name: receiver.name,
        webhookUrl: receiver.webhookUrl,
        authType: receiver.authType,
        authSecret: receiver.authSecret,
        isActive: receiver.isActive,
      });
    } else if (visible) {
      form.resetFields();
      form.setFieldsValue({
        authType: 'none',
        isActive: true,
      });
    }
  }, [visible, receiver, form]);

  const createMutation = useMutation({
    mutationFn: (data: AlertReceiverCreate) => alertApi.createReceiver(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alert-receivers'] });
      message.success('接收配置创建成功');
      onClose();
    },
    onError: () => {
      message.error('创建失败');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: AlertReceiverUpdate }) =>
      alertApi.updateReceiver(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alert-receivers'] });
      message.success('接收配置更新成功');
      onClose();
    },
    onError: () => {
      message.error('更新失败');
    },
  });

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      const data: AlertReceiverCreate | AlertReceiverUpdate = {
        name: values.name,
        webhookUrl: values.webhookUrl,
        authType: values.authType,
        authSecret: values.authSecret,
        isActive: values.isActive,
      };

      if (isEdit && receiver) {
        updateMutation.mutate({ id: receiver.id, data });
      } else {
        createMutation.mutate(data as AlertReceiverCreate);
      }
    } catch {
      // validation failed
    }
  };

  const isLoading = createMutation.isPending || updateMutation.isPending;

  return (
    <Modal
      title={isEdit ? '编辑接收配置' : '创建接收配置'}
      open={visible}
      onOk={handleSubmit}
      onCancel={onClose}
      confirmLoading={isLoading}
      width={600}
      destroyOnHidden
    >
      <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
        <Form.Item
          name="name"
          label="配置名称"
          rules={[{ required: true, message: '请输入配置名称' }]}
        >
          <Input placeholder="请输入配置名称" />
        </Form.Item>

        <Form.Item
          name="webhookUrl"
          label="Webhook URL"
          rules={[
            { required: true, message: '请输入 Webhook URL' },
            { type: 'url', message: '请输入有效的 URL' },
          ]}
          extra="接收 Alertmanager 告警的 Webhook 地址"
        >
          <Input placeholder="https://example.com/webhook/alertmanager" />
        </Form.Item>

        <Form.Item
          name="authType"
          label="认证方式"
          rules={[{ required: true, message: '请选择认证方式' }]}
        >
          <Select placeholder="请选择认证方式">
            <Select.Option value="none">无</Select.Option>
            <Select.Option value="secret">密钥 (Secret)</Select.Option>
            <Select.Option value="token">Token</Select.Option>
          </Select>
        </Form.Item>

        <Form.Item
          noStyle
          shouldUpdate={(prevValues, currentValues) =>
            prevValues.authType !== currentValues.authType
          }
        >
          {({ getFieldValue }) =>
            getFieldValue('authType') !== 'none' && (
              <Form.Item
                name="authSecret"
                label="认证密钥"
                rules={[{ required: true, message: '请输入认证密钥' }]}
              >
                <Input.Password placeholder="请输入认证密钥" />
              </Form.Item>
            )
          }
        </Form.Item>

        <Form.Item name="isActive" label="启用状态" valuePropName="checked">
          <Switch />
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default AlertReceiverFormModal;