import { useState } from 'react';
import { Table, Button, Space, Card, Popconfirm, App, Tag } from 'antd';
import { PlusOutlined, DeleteOutlined, EditOutlined, SendOutlined } from '@ant-design/icons';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useListQuery } from '../../hooks/useListQuery';
import type { AlertReceiver, PaginationParams } from '../../types';
import alertApi from '../../services/alert';
import AlertReceiverFormModal from './AlertReceiverFormModal';

const AlertReceiverList = () => {
  const queryClient = useQueryClient();
  const { message: msg } = App.useApp();
  const [formVisible, setFormVisible] = useState(false);
  const [editingReceiver, setEditingReceiver] = useState<AlertReceiver | null>(null);

  const { data, isLoading, pagination, setPagination } = useListQuery<
    AlertReceiver,
    Record<string, unknown>
  >({
    queryKey: 'alert-receivers',
    queryFn: async (params) => {
      const page = (params.skip ?? 0) / (params.limit ?? 20) + 1;
      return alertApi.getReceivers({ page, pageSize: params.limit ?? 20 } as PaginationParams);
    },
    initialFilter: {},
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => alertApi.deleteReceiver(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alert-receivers'] });
      msg.success('接收配置已删除');
    },
    onError: () => {
      msg.error('删除失败');
    },
  });

  const testMutation = useMutation({
    mutationFn: (id: number) => alertApi.testReceiver(id),
    onSuccess: (res) => {
      if (res.success) {
        msg.success('测试消息发送成功');
      } else {
        msg.error(`测试失败: ${res.message}`);
      }
    },
    onError: () => {
      msg.error('测试发送失败');
    },
  });

  const handleEdit = (record: AlertReceiver) => {
    setEditingReceiver(record);
    setFormVisible(true);
  };

  const handleAdd = () => {
    setEditingReceiver(null);
    setFormVisible(true);
  };

  const handleFormClose = () => {
    setFormVisible(false);
    setEditingReceiver(null);
  };

  const getAuthTypeLabel = (type: string) => {
    switch (type) {
      case 'none':
        return <Tag>无</Tag>;
      case 'secret':
        return <Tag color="orange">密钥</Tag>;
      case 'token':
        return <Tag color="blue">Token</Tag>;
      default:
        return <Tag>{type}</Tag>;
    }
  };

  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'Webhook URL',
      dataIndex: 'webhookUrl',
      key: 'webhookUrl',
      ellipsis: true,
      render: (url: string) => (
        <span style={{ fontFamily: 'monospace', fontSize: 12 }}>{url}</span>
      ),
    },
    {
      title: '认证方式',
      dataIndex: 'authType',
      key: 'authType',
      render: (type: string) => getAuthTypeLabel(type),
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
      render: (_: unknown, record: AlertReceiver) => (
        <Space size="small">
          <Button
            type="text"
            icon={<SendOutlined />}
            onClick={() => testMutation.mutate(record.id)}
            loading={testMutation.isPending}
          />
          <Button type="text" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          <Popconfirm
            title="确定删除此接收配置？"
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
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <h2>接收配置</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
          创建接收配置
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

      <AlertReceiverFormModal
        visible={formVisible}
        receiver={editingReceiver}
        onClose={handleFormClose}
      />
    </div>
  );
};

export default AlertReceiverList;