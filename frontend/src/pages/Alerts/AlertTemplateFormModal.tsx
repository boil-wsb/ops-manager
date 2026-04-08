import { useEffect } from 'react';
import { Modal, Form, Input, Select, Switch, App } from 'antd';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import type { AlertTemplate, AlertTemplateCreate, AlertTemplateUpdate, AlertTemplateType } from '../../types';
import alertApi from '../../services/alert';

const { TextArea } = Input;

interface AlertTemplateFormModalProps {
  visible: boolean;
  template: AlertTemplate | null;
  onClose: () => void;
}

const AlertTemplateFormModal = ({ visible, template, onClose }: AlertTemplateFormModalProps) => {
  const [form] = Form.useForm();
  const queryClient = useQueryClient();
  const { message } = App.useApp();
  const isEdit = !!template;

  useEffect(() => {
    if (visible && template) {
      form.setFieldsValue({
        name: template.name,
        templateType: template.templateType,
        subjectTemplate: template.subjectTemplate,
        cardConfig: template.cardConfig ? JSON.stringify(template.cardConfig, null, 2) : '',
        isDefault: template.isDefault,
        isActive: template.isActive,
      });
    } else if (visible) {
      form.resetFields();
      form.setFieldsValue({
        templateType: 'email',
        isDefault: false,
        isActive: true,
      });
    }
  }, [visible, template, form]);

  const createMutation = useMutation({
    mutationFn: (data: AlertTemplateCreate) => alertApi.createTemplate(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alert-templates'] });
      message.success('模板创建成功');
      onClose();
    },
    onError: () => {
      message.error('创建失败');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: AlertTemplateUpdate }) =>
      alertApi.updateTemplate(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alert-templates'] });
      message.success('模板更新成功');
      onClose();
    },
    onError: () => {
      message.error('更新失败');
    },
  });

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      const cardConfig = values.cardConfig ? JSON.parse(values.cardConfig) : undefined;
      const data: AlertTemplateCreate | AlertTemplateUpdate = {
        name: values.name,
        templateType: values.templateType as AlertTemplateType,
        subjectTemplate: values.subjectTemplate,
        cardConfig,
        isDefault: values.isDefault,
        isActive: values.isActive,
      };

      if (isEdit && template) {
        updateMutation.mutate({ id: template.id, data });
      } else {
        createMutation.mutate(data as AlertTemplateCreate);
      }
    } catch {
      // validation failed
    }
  };

  const isLoading = createMutation.isPending || updateMutation.isPending;

  return (
    <Modal
      title={isEdit ? '编辑模板' : '创建模板'}
      open={visible}
      onOk={handleSubmit}
      onCancel={onClose}
      confirmLoading={isLoading}
      width={700}
      destroyOnHidden
    >
      <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
        <Form.Item
          name="name"
          label="模板名称"
          rules={[{ required: true, message: '请输入模板名称' }]}
        >
          <Input placeholder="请输入模板名称" />
        </Form.Item>

        <Form.Item
          name="templateType"
          label="模板类型"
          rules={[{ required: true, message: '请选择模板类型' }]}
        >
          <Select placeholder="请选择模板类型">
            <Select.Option value="email">邮件</Select.Option>
            <Select.Option value="feishu">飞书</Select.Option>
          </Select>
        </Form.Item>

        <Form.Item
          name="subjectTemplate"
          label="主题模板"
          rules={[{ required: true, message: '请输入主题模板' }]}
          extra={
            <span style={{ color: 'var(--text-color-secondary)', fontSize: 12 }}>
              支持 Go 模板语法，使用 {'{{'} .Labels.xxx {'}}'} 和 {'{{'} .Annotations.xxx {'}}'}{' '}
              访问标签和注释
            </span>
          }
        >
          <Input placeholder="如：{{ .Labels.summary }} - [{{ .Labels.severity }}]" />
        </Form.Item>

        <Form.Item
          name="cardConfig"
          label="卡片配置"
          rules={[{ required: true, message: '请输入卡片配置' }]}
          extra={
            <span style={{ color: 'var(--text-color-secondary)', fontSize: 12 }}>
              输入 JSON 格式的飞书卡片配置
            </span>
          }
        >
          <TextArea
            placeholder='{"schema":"2.0","header":{"title":{"content":"【{{.Severity}}】{{.Alertname}}"},"template":"red"},"body":{"elements":[...]}}'
            rows={6}
            style={{ fontFamily: 'monospace' }}
          />
        </Form.Item>

        <Form.Item name="isDefault" label="设为默认" valuePropName="checked">
          <Switch />
        </Form.Item>

        <Form.Item name="isActive" label="启用状态" valuePropName="checked">
          <Switch />
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default AlertTemplateFormModal;