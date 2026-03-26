import { useState } from 'react';
import { Table, Button, Space, Card } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { PlusOutlined } from '@ant-design/icons';
import { monitorApi } from '../../services/monitor';
import StatusTag from '../../components/StatusTag';

const MonitorList = () => {
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
  });

  const { data, isLoading } = useQuery({
    queryKey: ['my-terminals', pagination],
    queryFn: () =>
      monitorApi.getMyTerminals({
        skip: (pagination.current - 1) * pagination.pageSize,
        limit: pagination.pageSize,
      }),
  });

  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '资产ID',
      dataIndex: 'assetId',
      key: 'assetId',
    },
    {
      title: 'IP地址',
      dataIndex: 'ipAddress',
      key: 'ipAddress',
      render: (ip: string | null) => ip || '-',
    },
    {
      title: '主机名',
      dataIndex: 'hostname',
      key: 'hostname',
      render: (hostname: string | null) => hostname || '-',
    },
    {
      title: '负责人',
      dataIndex: 'ownerName',
      key: 'ownerName',
      render: (name: string | null) => name || '-',
    },
    {
      title: '状态',
      dataIndex: 'currentStatus',
      key: 'currentStatus',
      render: (status: string) => <StatusTag status={status} type="monitor" />,
    },
    {
      title: '监控项',
      dataIndex: 'monitorName',
      key: 'monitorName',
      render: (name: string | null) => name || '-',
    },
    {
      title: '最后检查',
      dataIndex: 'lastCheckAt',
      key: 'lastCheckAt',
      render: (time: string | null) => (time ? new Date(time).toLocaleString() : '-'),
    },
  ];

  return (
    <div>
      <Card style={{ marginBottom: 24 }}>
        <Space wrap>
          <Button type="primary" icon={<PlusOutlined />}>
            新增监控
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

export default MonitorList;
