import { useState } from 'react';
import { Table, Button, Space, Card, Popconfirm, App } from 'antd';
import { PlusOutlined, DeleteOutlined, EditOutlined } from '@ant-design/icons';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useListQuery } from '../../hooks/useListQuery';
import type { AlertSilence, PaginationParams } from '../../types';
import alertApi from '../../services/alert';
import AlertSilenceFormModal from './AlertSilenceFormModal';

const AlertSilenceList = () => {
  const queryClient = useQueryClient();
  const { message } = App.useApp();
  const [formVisible, setFormVisible] = useState(false);
  const [editingSilence, setEditingSilence] = useState<AlertSilence | null>(null);

  const { data, isLoading, pagination, setPagination } = useListQuery<
    AlertSilence,
    Record<string, unknown>
  >({
    queryKey: 'alert-silences',
    queryFn: async (params) => {
      const page = (params.skip ?? 0) / (params.limit ?? 20) + 1;
      return alertApi.getSilences({ page, pageSize: params.limit ?? 20 } as PaginationParams);
    },
    initialFilter: {},
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => alertApi.deleteSilence(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alert-silences'] });
      message.success('抑制规则已删除');
    },
    onError: () => {
      message.error('删除失败');
    },
  });

  const handleEdit = (record: AlertSilence) => {
    setEditingSilence(record);
    setFormVisible(true);
  };

  const handleAdd = () => {
    setEditingSilence(null);
    setFormVisible(true);
  };

  const handleFormClose = () => {
    setFormVisible(false);
    setEditingSilence(null);
  };

  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '匹配标签',
      dataIndex: 'matchLabels',
      key: 'matchLabels',
      render: (labels: Record<string, string>) => (
        <Space wrap>
          {Object.entries(labels).map(([key, value]) => (
            <span
              key={key}
              style={{
                padding: '2px 8px',
                backgroundColor: 'var(--bg-color)',
                borderRadius: 4,
                fontSize: 12,
              }}
            >
              {key}={value}
            </span>
          ))}
        </Space>
      ),
    },
    {
      title: '开始时间',
      dataIndex: 'startsAt',
      key: 'startsAt',
      render: (time: string) => new Date(time).toLocaleString(),
    },
    {
      title: '结束时间',
      dataIndex: 'endsAt',
      key: 'endsAt',
      render: (time: string) => new Date(time).toLocaleString(),
    },
    {
      title: '状态',
      dataIndex: 'isActive',
      key: 'isActive',
      render: (isActive: boolean) => (isActive ? '活跃' : '已过期'),
    },
    {
      title: '创建人',
      dataIndex: 'createdBy',
      key: 'createdBy',
    },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: AlertSilence) => (
        <Space size="small">
          <Button
            type="text"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          />
          <Popconfirm
            title="确定删除此抑制规则？"
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
        <h2>抑制规则</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
          创建抑制规则
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

      <AlertSilenceFormModal
        visible={formVisible}
        silence={editingSilence}
        onClose={handleFormClose}
      />
    </div>
  );
};

export default AlertSilenceList;
