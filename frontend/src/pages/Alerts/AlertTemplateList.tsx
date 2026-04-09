import { useState } from 'react';
import { Table, Button, Space, Card, Popconfirm, App, Tag, Switch, Modal, Input } from 'antd';
import { PlusOutlined, DeleteOutlined, EditOutlined, EyeOutlined } from '@ant-design/icons';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useListQuery } from '../../hooks/useListQuery';
import type { AlertTemplate, PaginationParams } from '../../types';
import alertApi from '../../services/alert';
import AlertTemplateFormModal from './AlertTemplateFormModal';

const { TextArea } = Input;

const AlertTemplateList = () => {
  const queryClient = useQueryClient();
  const { message } = App.useApp();
  const [formVisible, setFormVisible] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<AlertTemplate | null>(null);
  const [previewVisible, setPreviewVisible] = useState(false);
  const [previewData, setPreviewData] = useState<{
    template?: AlertTemplate;
    labels?: Record<string, string>;
    annotations?: Record<string, string>;
  }>({});

  const { data, isLoading, pagination, setPagination } = useListQuery<
    AlertTemplate,
    Record<string, unknown>
  >({
    queryKey: 'alert-templates',
    queryFn: async (params) => {
      const page = (params.skip ?? 0) / (params.limit ?? 20) + 1;
      return alertApi.getTemplates({ page, pageSize: params.limit ?? 20 } as PaginationParams);
    },
    initialFilter: {},
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => alertApi.deleteTemplate(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alert-templates'] });
      message.success('模板已删除');
    },
    onError: () => {
      message.error('删除失败');
    },
  });

  const setDefaultMutation = useMutation({
    mutationFn: ({ id, isDefault }: { id: number; isDefault: boolean }) =>
      alertApi.updateTemplate(id, { is_default: isDefault } as never),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alert-templates'] });
      message.success('已设为默认模板');
    },
    onError: () => {
      message.error('设置默认模板失败');
    },
  });

  const handleEdit = (record: AlertTemplate) => {
    setEditingTemplate(record);
    setFormVisible(true);
  };

  const handleAdd = () => {
    setEditingTemplate(null);
    setFormVisible(true);
  };

  const handleFormClose = () => {
    setFormVisible(false);
    setEditingTemplate(null);
  };

  const handlePreview = (record: AlertTemplate) => {
    setPreviewData({
      template: record,
      labels: { severity: 'critical', alertname: 'TestAlert', instance: 'server01' },
      annotations: { summary: '测试告警摘要', description: '这是一条测试告警描述' },
    });
    setPreviewVisible(true);
  };

  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '类型',
      dataIndex: 'templateType',
      key: 'templateType',
      render: (type: string) => (
        <Tag color={type === 'email' ? 'blue' : 'green'}>
          {type === 'email' ? '邮件' : '飞书'}
        </Tag>
      ),
    },
    {
      title: '默认',
      dataIndex: 'isDefault',
      key: 'isDefault',
      render: (isDefault: boolean, record: AlertTemplate) => (
        <Switch
          checked={isDefault}
          onChange={(checked) => {
            setDefaultMutation.mutate({ id: record.id, isDefault: checked });
          }}
        />
      ),
    },
    {
      title: '状态',
      dataIndex: 'isActive',
      key: 'isActive',
      render: (isActive: boolean) => (
        <Tag color={isActive ? 'success' : 'default'}>{isActive ? '启用' : '禁用'}</Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      key: 'createdAt',
      render: (time: string) => new Date(time).toLocaleString(),
    },
    {
      title: '操作',
      key: 'action',
      width: 180,
      render: (_: unknown, record: AlertTemplate) => (
        <Space size="small">
          <Button type="text" icon={<EyeOutlined />} onClick={() => handlePreview(record)} />
          <Button type="text" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          <Popconfirm
            title="确定删除此模板？"
            onConfirm={() => deleteMutation.mutate(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="text" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'flex-end' }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
          创建模板
        </Button>
      </div>

      <Card>
        <Table
          columns={columns}
          dataSource={data?.items || []}
          rowKey="id"
          loading={isLoading}
          pagination={{
            ...pagination,
            total: data?.total || 0,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
            onChange: (page, pageSize) => setPagination({ current: page, pageSize }),
          }}
        />
      </Card>

      <AlertTemplateFormModal
        visible={formVisible}
        template={editingTemplate}
        onClose={handleFormClose}
      />

      <Modal
        title="模板预览"
        open={previewVisible}
        onCancel={() => setPreviewVisible(false)}
        footer={null}
        width={700}
      >
        {previewData.template && (
          <div>
            <h4>模板信息</h4>
            <p>
              <strong>名称：</strong> {previewData.template.name}
            </p>
            <p>
              <strong>类型：</strong> {previewData.template.templateType}
            </p>

            <div style={{ fontSize: 16, fontWeight: 500, marginTop: 16 }}>输入数据</div>
            <div style={{ marginBottom: 16 }}>
              <p>
                <strong>Labels：</strong>
              </p>
              <pre
                style={{
                  backgroundColor: 'var(--bg-color)',
                  padding: 8,
                  borderRadius: 4,
                }}
              >
                {JSON.stringify(previewData.labels || {}, null, 2)}
              </pre>
            </div>
            <div style={{ marginBottom: 16 }}>
              <p>
                <strong>Annotations：</strong>
              </p>
              <pre
                style={{
                  backgroundColor: 'var(--bg-color)',
                  padding: 8,
                  borderRadius: 4,
                }}
              >
                {JSON.stringify(previewData.annotations || {}, null, 2)}
              </pre>
            </div>

            {previewData.template.subjectTemplate && (
              <div style={{ marginBottom: 16 }}>
                <p>
                  <strong>主题渲染结果：</strong>
                </p>
                <TextArea
                  value={previewData.template.subjectTemplate
                    .replace('{{ .Labels.summary }}', previewData.annotations?.summary || '')
                    .replace('{{ .Labels.alertname }}', previewData.labels?.alertname || '')}
                  readOnly
                  rows={2}
                />
              </div>
            )}

            {previewData.template.cardConfig && (
              <div>
                <p>
                  <strong>卡片配置：</strong>
                </p>
                <TextArea
                  value={JSON.stringify(previewData.template.cardConfig, null, 2)}
                  readOnly
                  rows={10}
                />
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};

export default AlertTemplateList;