import { useEffect } from 'react';
import { Modal, Form, Input, DatePicker, Switch, Space, Tag, App } from 'antd';
import { PlusOutlined, MinusCircleOutlined } from '@ant-design/icons';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import type { AlertSilence, AlertSilenceCreate, AlertSilenceUpdate } from '../../types';
import alertApi from '../../services/alert';

interface AlertSilenceFormModalProps {
  visible: boolean;
  silence: AlertSilence | null;
  onClose: () => void;
}

const AlertSilenceFormModal = ({ visible, silence, onClose }: AlertSilenceFormModalProps) => {
  const [form] = Form.useForm();
  const queryClient = useQueryClient();
  const { message } = App.useApp();
  const isEdit = !!silence;

  useEffect(() => {
    if (visible && silence) {
      form.setFieldsValue({
        name: silence.name,
        matchLabels: Object.entries(silence.matchLabels).map(([key, value]) => ({ key, value })),
        startsAt: dayjs(silence.startsAt),
        endsAt: dayjs(silence.endsAt),
        isActive: silence.isActive,
      });
    } else if (visible) {
      form.resetFields();
      form.setFieldsValue({
        matchLabels: [{ key: '', value: '' }],
        isActive: true,
        startsAt: dayjs(),
        endsAt: dayjs().add(1, 'hour'),
      });
    }
  }, [visible, silence, form]);

  const createMutation = useMutation({
    mutationFn: (data: AlertSilenceCreate) => alertApi.createSilence(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alert-silences'] });
      message.success('抑制规则创建成功');
      onClose();
    },
    onError: () => {
      message.error('创建失败');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: AlertSilenceUpdate }) =>
      alertApi.updateSilence(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alert-silences'] });
      message.success('抑制规则更新成功');
      onClose();
    },
    onError: () => {
      message.error('更新失败');
    },
  });

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      const matchLabels: Record<string, string> = {};
      values.matchLabels?.forEach(({ key, value }: { key: string; value: string }) => {
        if (key && value) {
          matchLabels[key] = value;
        }
      });

      const data: AlertSilenceCreate | AlertSilenceUpdate = {
        name: values.name,
        matchLabels,
        startsAt: values.startsAt.toISOString(),
        endsAt: values.endsAt.toISOString(),
        isActive: values.isActive,
      };

      if (isEdit && silence) {
        updateMutation.mutate({ id: silence.id, data });
      } else {
        createMutation.mutate(data as AlertSilenceCreate);
      }
    } catch {
      // validation failed
    }
  };

  const isLoading = createMutation.isPending || updateMutation.isPending;

  return (
    <Modal
      title={isEdit ? '编辑抑制规则' : '创建抑制规则'}
      open={visible}
      onOk={handleSubmit}
      onCancel={onClose}
      confirmLoading={isLoading}
      width={600}
      destroyOnClose
    >
      <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
        <Form.Item
          name="name"
          label="规则名称"
          rules={[{ required: true, message: '请输入规则名称' }]}
        >
          <Input placeholder="请输入规则名称" />
        </Form.Item>

        <Form.List name="matchLabels">
          {(fields, { add, remove }) => (
            <>
              <Form.Item label="匹配标签">
                <Space direction="vertical" style={{ width: '100%' }}>
                  {fields.map(({ key, name, ...rest }) => (
                    <Space key={key} style={{ width: '100%' }} {...rest}>
                      <Form.Item
                        name={[name, 'key']}
                        noStyle
                        rules={[{ required: true, message: '请输入标签键' }]}
                      >
                        <Input placeholder="标签键，如：severity" style={{ width: 200 }} />
                      </Form.Item>
                      <span>=</span>
                      <Form.Item
                        name={[name, 'value']}
                        noStyle
                        rules={[{ required: true, message: '请输入标签值' }]}
                      >
                        <Input placeholder="标签值，如：critical" style={{ width: 200 }} />
                      </Form.Item>
                      {fields.length > 1 && (
                        <MinusCircleOutlined onClick={() => remove(name)} />
                      )}
                    </Space>
                  ))}
                </Space>
              </Form.Item>
              <Form.Item>
                <Space>
                  <Tag icon={<PlusOutlined />} onClick={() => add({ key: '', value: '' })}>
                    添加标签
                  </Tag>
                </Space>
              </Form.Item>
            </>
          )}
        </Form.List>

        <Form.Item
          name="startsAt"
          label="开始时间"
          rules={[{ required: true, message: '请选择开始时间' }]}
        >
          <DatePicker showTime style={{ width: '100%' }} />
        </Form.Item>

        <Form.Item
          name="endsAt"
          label="结束时间"
          rules={[{ required: true, message: '请选择结束时间' }]}
        >
          <DatePicker showTime style={{ width: '100%' }} />
        </Form.Item>

        <Form.Item name="isActive" label="启用状态" valuePropName="checked">
          <Switch />
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default AlertSilenceFormModal;