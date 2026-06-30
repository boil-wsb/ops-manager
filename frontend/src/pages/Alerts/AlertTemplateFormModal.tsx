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
        bodyTemplate: template.bodyTemplate,
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
        bodyTemplate: values.bodyTemplate,
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
          noStyle
          shouldUpdate={(prev, cur) => prev.templateType !== cur.templateType}
        >
          {({ getFieldValue }) => {
            const templateType = getFieldValue('templateType');
            return (
              <>
                <Form.Item
                  name="subjectTemplate"
                  label={templateType === 'email' ? '邮件主题' : '卡片标题'}
                  rules={[{ required: true, message: '请输入主题模板' }]}
                  extra={
                    <span style={{ color: 'var(--text-color-secondary)', fontSize: 12 }}>
                      支持 Go 模板语法，使用 {'{{'} .alertname {'}}'}、{'{{'} .severity {'}}'} 等变量
                    </span>
                  }
                >
                  <Input placeholder="如：【{{.severity}}】{{.alertname}}" />
                </Form.Item>

                <Form.Item
                  name="bodyTemplate"
                  label={templateType === 'email' ? '邮件正文' : '消息内容模板'}
                  extra={
                    <span style={{ color: 'var(--text-color-secondary)', fontSize: 12 }}>
                      {templateType === 'feishu'
                        ? '支持 Markdown 和 Go 模板语法。留空则使用下方卡片配置。可用变量：{{.alertname}}, {{.status}}, {{.severity}}, {{.instance}}, {{.description}}, {{.startsAt}}, {{.endsAt}}, {{.labels}}, {{.annotations}}'
                        : '支持 Go 模板语法，使用 {{.xxx}} 访问变量'}
                    </span>
                  }
                >
                  <TextArea
                    placeholder={
                      templateType === 'feishu'
                        ? '**[Prometheus告警信息]({{.generatorURL}})**\n事       件：**[{{.alertname}}]({{.externalURL}})**\n告警级别：{{.severity}}   告警状态：{{.status}}\n开始时间：{{.startsAt}}\n{{if eq .status "resolved"}}\n结束时间：{{.endsAt}}\n<font color="green">**该告警已恢复😀**</font>\n{{end}}'
                        : '告警名称：{{.alertname}}\n告警级别：{{.severity}}\n故障主机：{{.instance}}'
                    }
                    rows={10}
                    style={{ fontFamily: 'monospace' }}
                  />
                </Form.Item>

                {templateType === 'feishu' && (
                  <Form.Item
                    name="cardConfig"
                    label="卡片配置（可选）"
                    extra={
                      <span style={{ color: 'var(--text-color-secondary)', fontSize: 12 }}>
                        JSON 格式的飞书交互式卡片配置，可包含按钮等交互元素。如果配置此项，将优先使用卡片配置，消息内容模板可通过 {'{{'} .body {'}}'} 引用。留空则使用消息内容模板自动生成卡片。
                      </span>
                    }
                  >
                    <TextArea
                      placeholder='{"schema":"2.0","header":{"title":{"tag":"plain_text","content":"【{{.severity}}】{{.alertname}}"},"template":"red"},"body":{"elements":[{"tag":"div","text":{"tag":"lark_md","content":"{{.body}}"}}]}}'
                      rows={8}
                      style={{ fontFamily: 'monospace' }}
                    />
                  </Form.Item>
                )}
              </>
            );
          }}
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