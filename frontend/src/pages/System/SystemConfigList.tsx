import { useState } from 'react';
import { Table, Button, Select, Tag, Space, Card, App, Modal, Form, Input, Switch, Popconfirm } from 'antd';
import { useQuery, useMutation } from '@tanstack/react-query';
import { ReloadOutlined, EditOutlined, PlusOutlined, DeleteOutlined, SearchOutlined } from '@ant-design/icons';
import { systemConfigApi, type SystemConfig, type SystemConfigCreateParams, type SystemConfigUpdateParams } from '../../services/systemConfig';
import { fuzzyFilterOption } from '../../utils/selectFilter';

const groupColorMap: Record<string, string> = {
  scheduler: 'blue',
  minio: 'cyan',
  feishu: 'green',
  itreporter: 'purple',
};

const SystemConfigList = () => {
  const { message } = App.useApp();
  const [filter, setFilter] = useState({
    group: undefined as string | undefined,
    key: undefined as string | undefined,
  });
  const [pagination, setPagination] = useState({ current: 1, pageSize: 20 });
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [editingConfig, setEditingConfig] = useState<SystemConfig | null>(null);
  const [editForm] = Form.useForm();
  const [createForm] = Form.useForm();

  const { data: groups } = useQuery({
    queryKey: ['systemConfigGroups'],
    queryFn: () => systemConfigApi.getConfigGroups(),
  });

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['systemConfigs', filter, pagination],
    queryFn: async () => {
      const result = await systemConfigApi.getSystemConfigs({
        skip: (pagination.current - 1) * pagination.pageSize,
        limit: pagination.pageSize,
        group: filter.group,
        key: filter.key,
      });
      return {
        items: Array.isArray(result) ? result : result?.items ?? [],
        total: Array.isArray(result) ? result.length : result?.total ?? 0,
      };
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ key, data }: { key: string; data: SystemConfigUpdateParams }) =>
      systemConfigApi.updateSystemConfig(key, data),
    onSuccess: () => {
      message.success('更新成功');
      setEditModalOpen(false);
      setEditingConfig(null);
      editForm.resetFields();
      refetch();
    },
    onError: () => message.error('更新失败'),
  });

  const createMutation = useMutation({
    mutationFn: (data: SystemConfigCreateParams) => systemConfigApi.createSystemConfig(data),
    onSuccess: () => {
      message.success('创建成功');
      setCreateModalOpen(false);
      createForm.resetFields();
      refetch();
    },
    onError: (error: Error) => message.error(`创建失败: ${error.message || '未知错误'}`),
  });

  const deleteMutation = useMutation({
    mutationFn: systemConfigApi.deleteSystemConfig,
    onSuccess: () => {
      message.success('删除成功');
      refetch();
    },
    onError: () => message.error('删除失败'),
  });

  const handleEdit = (record: SystemConfig) => {
    setEditingConfig(record);
    editForm.setFieldsValue({
      value: record.value,
      description: record.description ?? '',
      isSecret: record.isSecret,
    });
    setEditModalOpen(true);
  };

  const handleSave = async () => {
    try {
      const values = await editForm.validateFields();
      if (!editingConfig) return;
      updateMutation.mutate({ key: editingConfig.key, data: values });
    } catch { /* validation failed */ }
  };

  const handleCreate = async () => {
    try {
      const values = await createForm.validateFields();
      createMutation.mutate(values);
    } catch { /* validation failed */ }
  };

  const maskValue = (value: string, isSecret: boolean) => {
    if (!isSecret) return value;
    if (value.length <= 8) return '****';
    return value.slice(0, 4) + '****' + value.slice(-4);
  };

  const columns = [
    {
      title: '配置键',
      dataIndex: 'key',
      key: 'key',
      render: (key: string) => <code style={{ fontSize: 13 }}>{key}</code>,
    },
    {
      title: '配置值',
      dataIndex: 'value',
      key: 'value',
      ellipsis: true,
      render: (value: string, record: SystemConfig) => (
        <code style={{ fontSize: 13 }}>{maskValue(value, record.isSecret)}</code>
      ),
    },
    {
      title: '分组',
      dataIndex: 'group',
      key: 'group',
      render: (group: string) => (
        <Tag color={groupColorMap[group] || 'default'}>{group}</Tag>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (desc: string | null) => desc || '-',
    },
    {
      title: '敏感',
      dataIndex: 'isSecret',
      key: 'isSecret',
      render: (isSecret: boolean) => isSecret ? <Tag color="red">是</Tag> : <Tag>否</Tag>,
    },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: SystemConfig) => (
        <Space>
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)}>
            编辑
          </Button>
          <Popconfirm
            title="确定删除此配置项？"
            onConfirm={() => deleteMutation.mutate(record.key)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Card style={{ marginBottom: 16 }}>
        <Space wrap>
          <Input.Search
            placeholder="搜索配置键"
            value={filter.key}
            onChange={(e) => setFilter({ ...filter, key: e.target.value || undefined })}
            onSearch={(value) => setFilter({ ...filter, key: value || undefined })}
            style={{ width: 240 }}
            allowClear
            enterButton={<SearchOutlined />}
          />
          <Select
            placeholder="配置分组"
            value={filter.group}
            onChange={(value) => setFilter({ ...filter, group: value })}
            style={{ width: 160 }}
            allowClear
            showSearch
            filterOption={fuzzyFilterOption}
          >
            {(groups || []).map((g) => (
              <Select.Option key={g} value={g}>{g}</Select.Option>
            ))}
          </Select>
          <Button icon={<ReloadOutlined />} onClick={() => refetch()}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModalOpen(true)}>
            新增配置
          </Button>
        </Space>
      </Card>

      <Table
        columns={columns}
        dataSource={data?.items || []}
        rowKey="key"
        loading={isLoading}
        pagination={{
          current: pagination.current,
          pageSize: pagination.pageSize,
          total: data?.total || 0,
          showSizeChanger: true,
          showTotal: (total: number) => `共 ${total} 条`,
          onChange: (page: number, pageSize: number) => setPagination({ current: page, pageSize }),
        }}
      />

      <Modal
        title={`编辑配置 - ${editingConfig?.key}`}
        open={editModalOpen}
        onOk={handleSave}
        onCancel={() => { setEditModalOpen(false); setEditingConfig(null); editForm.resetFields(); }}
        confirmLoading={updateMutation.isPending}
        destroyOnHidden
        width={600}
      >
        <Form form={editForm} layout="vertical">
          <Form.Item label="配置值" name="value" rules={[{ required: true, message: '请输入配置值' }]}>
            <Input.TextArea rows={4} />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item label="敏感配置" name="isSecret" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="新增配置"
        open={createModalOpen}
        onOk={handleCreate}
        onCancel={() => { setCreateModalOpen(false); createForm.resetFields(); }}
        confirmLoading={createMutation.isPending}
        destroyOnHidden
        width={600}
      >
        <Form form={createForm} layout="vertical">
          <Form.Item label="配置键" name="key" rules={[{ required: true, message: '请输入配置键' }]}>
            <Input placeholder="如: scheduler.task_mapping.my-task" />
          </Form.Item>
          <Form.Item label="配置值" name="value" rules={[{ required: true, message: '请输入配置值' }]}>
            <Input.TextArea rows={4} />
          </Form.Item>
          <Form.Item label="分组" name="group" rules={[{ required: true, message: '请输入分组' }]}>
            <Select placeholder="选择或输入分组" showSearch filterOption={fuzzyFilterOption} allowClear>
              {(groups || []).map((g) => (
                <Select.Option key={g} value={g}>{g}</Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item label="描述" name="description">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item label="敏感配置" name="isSecret" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default SystemConfigList;
