import { useState } from 'react';
import { Table, Button, Space, Card } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { PlusOutlined } from '@ant-design/icons';
import { monitorApi } from '../../services/monitor';
import StatusTag from '../../components/StatusTag';
import type { MonitorTerminal } from '../../types';

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
      sorter: (a: MonitorTerminal, b: MonitorTerminal) => (a.name || '').localeCompare(b.name || ''),
    },
    {
      title: '资产ID',
      dataIndex: 'assetId',
      key: 'assetId',
      sorter: (a: MonitorTerminal, b: MonitorTerminal) => (a.assetId || '').localeCompare(b.assetId || ''),
    },
    {
      title: 'IP地址',
      dataIndex: 'ipAddress',
      key: 'ipAddress',
      sorter: (a: MonitorTerminal, b: MonitorTerminal) => (a.ipAddress || '').localeCompare(b.ipAddress || ''),
      render: (ip: string | null) => ip || '-',
    },
    {
      title: '主机名',
      dataIndex: 'hostname',
      key: 'hostname',
      sorter: (a: MonitorTerminal, b: MonitorTerminal) => (a.hostname || '').localeCompare(b.hostname || ''),
      render: (hostname: string | null) => hostname || '-',
    },
    {
      title: '负责人',
      dataIndex: 'ownerName',
      key: 'ownerName',
      sorter: (a: MonitorTerminal, b: MonitorTerminal) => (a.ownerName || '').localeCompare(b.ownerName || ''),
      render: (name: string | null) => name || '-',
    },
    {
      title: '状态',
      dataIndex: 'currentStatus',
      key: 'currentStatus',
      sorter: (a: MonitorTerminal, b: MonitorTerminal) => (a.currentStatus || '').localeCompare(b.currentStatus || ''),
      render: (status: string) => <StatusTag status={status} type="monitor" />,
    },
    {
      title: '监控项',
      dataIndex: 'monitorName',
      key: 'monitorName',
      sorter: (a: MonitorTerminal, b: MonitorTerminal) => (a.monitorName || '').localeCompare(b.monitorName || ''),
      render: (name: string | null) => name || '-',
    },
    {
      title: '最后检查',
      dataIndex: 'lastCheckAt',
      key: 'lastCheckAt',
      sorter: (a: MonitorTerminal, b: MonitorTerminal) => {
        if (!a.lastCheckAt && !b.lastCheckAt) return 0;
        if (!a.lastCheckAt) return 1;
        if (!b.lastCheckAt) return -1;
        return new Date(a.lastCheckAt).getTime() - new Date(b.lastCheckAt).getTime();
      },
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
