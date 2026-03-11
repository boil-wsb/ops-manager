import { useState } from 'react';
import { Table, Button, Select, Tag, Space, Card, Modal, message } from 'antd';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { CheckCircleOutlined, EyeOutlined } from '@ant-design/icons';
import type { Alert } from '../../types';

// Mock API for now
const mockAlerts: Alert[] = [
  {
    id: 1,
    monitorId: 2,
    monitorName: 'Database Server',
    severity: 'critical',
    status: 'firing',
    title: 'Database connection timeout',
    message: 'Connection timeout after 10 seconds',
    startedAt: '2024-01-15T10:25:00Z',
    notificationSent: true,
  },
  {
    id: 2,
    monitorId: 1,
    monitorName: 'Web Server 01',
    severity: 'warning',
    status: 'acknowledged',
    title: 'High response time',
    message: 'Response time exceeded 1000ms',
    startedAt: '2024-01-15T09:30:00Z',
    acknowledgedAt: '2024-01-15T09:35:00Z',
    acknowledgedBy: 1,
    notificationSent: true,
  },
];

const alertApi = {
  getAlerts: async () => ({ total: mockAlerts.length, items: mockAlerts }),
  acknowledgeAlert: async (id: number) => {
    const alert = mockAlerts.find((a) => a.id === id);
    if (alert) {
      alert.status = 'acknowledged';
      alert.acknowledgedAt = new Date().toISOString();
    }
  },
  resolveAlert: async (id: number) => {
    const alert = mockAlerts.find((a) => a.id === id);
    if (alert) {
      alert.status = 'resolved';
      alert.resolvedAt = new Date().toISOString();
    }
  },
};

const AlertList = () => {
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState({
    status: undefined as string | undefined,
    severity: undefined as string | undefined,
  });

  const { data, isLoading } = useQuery({
    queryKey: ['alerts', filter],
    queryFn: () => alertApi.getAlerts(),
  });

  const acknowledgeMutation = useMutation({
    mutationFn: alertApi.acknowledgeAlert,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
      message.success('告警已确认');
    },
  });

  const resolveMutation = useMutation({
    mutationFn: alertApi.resolveAlert,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
      message.success('告警已解决');
    },
  });

  const columns = [
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
    },
    {
      title: '监控项',
      dataIndex: 'monitorName',
      key: 'monitorName',
    },
    {
      title: '级别',
      dataIndex: 'severity',
      key: 'severity',
      render: (severity: string) => {
        const colorMap: Record<string, string> = {
          info: 'blue',
          warning: 'orange',
          critical: 'red',
        };
        const labelMap: Record<string, string> = {
          info: '信息',
          warning: '警告',
          critical: '严重',
        };
        return <Tag color={colorMap[severity]}>{labelMap[severity]}</Tag>;
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const colorMap: Record<string, string> = {
          firing: 'red',
          acknowledged: 'blue',
          resolved: 'green',
          suppressed: 'gray',
        };
        const labelMap: Record<string, string> = {
          firing: '触发中',
          acknowledged: '已确认',
          resolved: '已解决',
          suppressed: '已抑制',
        };
        return <Tag color={colorMap[status]}>{labelMap[status]}</Tag>;
      },
    },
    {
      title: '开始时间',
      dataIndex: 'startedAt',
      key: 'startedAt',
      render: (time: string) => new Date(time).toLocaleString(),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: Alert) => (
        <Space size="small">
          <Button
            type="text"
            icon={<EyeOutlined />}
            onClick={() =>
              Modal.info({
                title: '告警详情',
                content: (
                  <div>
                    <p><strong>标题:</strong> {record.title}</p>
                    <p><strong>消息:</strong> {record.message}</p>
                    <p><strong>监控项:</strong> {record.monitorName}</p>
                    <p><strong>开始时间:</strong> {new Date(record.startedAt).toLocaleString()}</p>
                  </div>
                ),
              })
            }
          />
          {record.status === 'firing' && (
            <Button
              type="text"
              icon={<CheckCircleOutlined />}
              onClick={() => acknowledgeMutation.mutate(record.id)}
            >
              确认
            </Button>
          )}
          {(record.status === 'firing' || record.status === 'acknowledged') && (
            <Button
              type="text"
              onClick={() => resolveMutation.mutate(record.id)}
            >
              解决
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <h1>告警事件</h1>

      <Card style={{ marginBottom: 24 }}>
        <Space wrap>
          <Select
            placeholder="状态"
            value={filter.status}
            onChange={(value) => setFilter({ ...filter, status: value })}
            style={{ width: 120 }}
            allowClear
          >
            <Select.Option value="firing">触发中</Select.Option>
            <Select.Option value="acknowledged">已确认</Select.Option>
            <Select.Option value="resolved">已解决</Select.Option>
          </Select>
          <Select
            placeholder="级别"
            value={filter.severity}
            onChange={(value) => setFilter({ ...filter, severity: value })}
            style={{ width: 120 }}
            allowClear
          >
            <Select.Option value="info">信息</Select.Option>
            <Select.Option value="warning">警告</Select.Option>
            <Select.Option value="critical">严重</Select.Option>
          </Select>
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

export default AlertList;
