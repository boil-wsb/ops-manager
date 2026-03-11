import { useState } from 'react';
import { Table, Button, Select, Tag, Space, Card, Switch, message } from 'antd';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { PlusOutlined, PlayCircleOutlined, PauseCircleOutlined } from '@ant-design/icons';
import type { Monitor } from '../../types';

// Mock API for now
const mockMonitors: Monitor[] = [
  {
    id: 1,
    name: 'Web Server 01',
    monitorType: 'http',
    target: 'http://192.168.1.10:8080',
    intervalSeconds: 60,
    timeoutSeconds: 10,
    retryCount: 3,
    isEnabled: true,
    currentStatus: 'up',
    lastCheckAt: '2024-01-15T10:30:00Z',
    lastCheckResult: 'HTTP 200 OK',
    lastCheckDurationMs: 45,
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-15T10:30:00Z',
  },
  {
    id: 2,
    name: 'Database Server',
    monitorType: 'tcp',
    target: '192.168.1.20:3306',
    intervalSeconds: 30,
    timeoutSeconds: 5,
    retryCount: 3,
    isEnabled: true,
    currentStatus: 'up',
    lastCheckAt: '2024-01-15T10:30:00Z',
    lastCheckResult: 'TCP port 3306 open',
    lastCheckDurationMs: 12,
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-15T10:30:00Z',
  },
];

const monitorApi = {
  getMonitors: async () => ({ total: mockMonitors.length, items: mockMonitors }),
  toggleMonitor: async (id: number, enabled: boolean) => {
    const monitor = mockMonitors.find((m) => m.id === id);
    if (monitor) {
      monitor.isEnabled = enabled;
    }
  },
};

const MonitorList = () => {
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState({
    monitorType: undefined as string | undefined,
    status: undefined as string | undefined,
  });

  const { data, isLoading } = useQuery({
    queryKey: ['monitors', filter],
    queryFn: () => monitorApi.getMonitors(),
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, enabled }: { id: number; enabled: boolean }) =>
      monitorApi.toggleMonitor(id, enabled),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['monitors'] });
      message.success('状态已更新');
    },
  });

  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '类型',
      dataIndex: 'monitorType',
      key: 'monitorType',
      render: (type: string) => type.toUpperCase(),
    },
    {
      title: '目标',
      dataIndex: 'target',
      key: 'target',
    },
    {
      title: '状态',
      dataIndex: 'currentStatus',
      key: 'currentStatus',
      render: (status: string) => {
        const colorMap: Record<string, string> = {
          up: 'green',
          down: 'red',
          unknown: 'gray',
          paused: 'orange',
        };
        return <Tag color={colorMap[status] || 'default'}>{status.toUpperCase()}</Tag>;
      },
    },
    {
      title: '响应时间',
      dataIndex: 'lastCheckDurationMs',
      key: 'lastCheckDurationMs',
      render: (ms: number) => (ms ? `${ms}ms` : '-'),
    },
    {
      title: '最后检查',
      dataIndex: 'lastCheckAt',
      key: 'lastCheckAt',
      render: (time: string) => (time ? new Date(time).toLocaleString() : '-'),
    },
    {
      title: '启用',
      key: 'isEnabled',
      render: (_: any, record: Monitor) => (
        <Switch
          checked={record.isEnabled}
          onChange={(checked) => toggleMutation.mutate({ id: record.id, enabled: checked })}
          checkedChildren={<PlayCircleOutlined />}
          unCheckedChildren={<PauseCircleOutlined />}
        />
      ),
    },
  ];

  return (
    <div>
      <h1>监控管理</h1>

      <Card style={{ marginBottom: 24 }}>
        <Space wrap>
          <Select
            placeholder="监控类型"
            value={filter.monitorType}
            onChange={(value) => setFilter({ ...filter, monitorType: value })}
            style={{ width: 120 }}
            allowClear
          >
            <Select.Option value="ping">PING</Select.Option>
            <Select.Option value="http">HTTP</Select.Option>
            <Select.Option value="tcp">TCP</Select.Option>
            <Select.Option value="udp">UDP</Select.Option>
          </Select>
          <Select
            placeholder="状态"
            value={filter.status}
            onChange={(value) => setFilter({ ...filter, status: value })}
            style={{ width: 120 }}
            allowClear
          >
            <Select.Option value="up">正常</Select.Option>
            <Select.Option value="down">故障</Select.Option>
          </Select>
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
          total: data?.total || 0,
          showSizeChanger: true,
          showTotal: (total) => `共 ${total} 条`,
        }}
      />
    </div>
  );
};

export default MonitorList;
