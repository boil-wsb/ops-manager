import { useState } from 'react';
import { Table, Button, Select, Tag, Space, Card, App } from 'antd';
import { useQuery, useMutation } from '@tanstack/react-query';
import { ReloadOutlined, SyncOutlined } from '@ant-design/icons';
import { opsApi } from '../../services/ops';
import StatusTag from '../../components/StatusTag';
import type { Certificate } from '../../types';

const CertificateList = () => {
  const { message } = App.useApp();
  const [filter, setFilter] = useState({
    status: undefined as string | undefined,
    expiringSoon: undefined as boolean | undefined,
  });
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
  });

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['certificates', filter, pagination],
    queryFn: async () => {
    const result = await opsApi.getCertificates({
      skip: (pagination.current - 1) * pagination.pageSize,
      limit: pagination.pageSize,
      status: filter.status,
      expiring_soon: filter.expiringSoon,
    });
    return {
      items: Array.isArray(result) ? result : [],
      total: Array.isArray(result) ? result.length : 0,
    };
  },
  });

  const syncMutation = useMutation({
    mutationFn: opsApi.syncCertificates,
    onSuccess: (data) => {
      message.success(`同步完成: 共 ${data.total} 个证书, 新增 ${data.created} 个, 更新 ${data.updated} 个`);
      refetch();
    },
    onError: () => {
      message.error('同步失败，请检查 Prometheus 连接');
    },
  });

  const columns = [
    {
      title: '域名',
      dataIndex: 'domain',
      key: 'domain',
    },
    {
      title: '颁发者',
      dataIndex: 'issuer',
      key: 'issuer',
    },
    {
      title: '过期时间',
      dataIndex: 'valid_until',
      key: 'valid_until',
      render: (date: string) => (date ? new Date(date).toLocaleDateString() : '-'),
    },
    {
      title: '剩余天数',
      key: 'days_until_expiry',
      render: (_: any, record: Certificate) => {
        const days = record.days_until_expiry;
        if (days === null || days === undefined) return '-';
        return (
          <Tag color={days < 0 ? 'red' : days < 30 ? 'orange' : 'green'}>
            {days < 0 ? '已过期' : `${days}天`}
          </Tag>
        );
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => <StatusTag status={status} type="certificate" />,
    },
    {
      title: '自动续期',
      dataIndex: 'is_auto_renewal',
      key: 'is_auto_renewal',
      render: (isAutoRenewal: boolean) => (
        <Tag color={isAutoRenewal ? 'green' : 'default'}>
          {isAutoRenewal ? '是' : '否'}
        </Tag>
      ),
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      key: 'updated_at',
      render: (time: string) => (time ? new Date(time).toLocaleString() : '-'),
    },
  ];

  return (
    <div>
      <h1>证书管理</h1>

      <Card style={{ marginBottom: 24 }}>
        <Space wrap>
          <Select
            placeholder="状态"
            value={filter.status}
            onChange={(value) => setFilter({ ...filter, status: value })}
            style={{ width: 120 }}
            allowClear
          >
            <Select.Option value="active">有效</Select.Option>
            <Select.Option value="expired">已过期</Select.Option>
            <Select.Option value="expiring">即将过期</Select.Option>
          </Select>
          <Select
            placeholder="即将过期"
            value={filter.expiringSoon}
            onChange={(value) => setFilter({ ...filter, expiringSoon: value })}
            style={{ width: 120 }}
            allowClear
          >
            <Select.Option value={true}>30天内</Select.Option>
            <Select.Option value={false}>30天外</Select.Option>
          </Select>
          <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
            刷新
          </Button>
          <Button 
            type="default" 
            icon={<SyncOutlined spin={syncMutation.isPending} />} 
            loading={syncMutation.isPending}
            onClick={() => syncMutation.mutate()}
          >
            从Prometheus同步
          </Button>
        </Space>
      </Card>

      <Table
        columns={columns}
        dataSource={data?.items || []}
        rowKey="id"
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
    </div>
  );
};

export default CertificateList;
