import { useState } from 'react';
import { Table, Button, Select, Space, Card, Modal, message } from 'antd';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { CheckCircleOutlined, EyeOutlined } from '@ant-design/icons';
import type { Alert } from '../../types';
import { monitorApi } from '../../services/monitor';
import StatusTag from '../../components/StatusTag';

const AlertList = () => {
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState({
    status: undefined as string | undefined,
    severity: undefined as string | undefined,
  });

  const { data, isLoading } = useQuery({
    queryKey: ['alerts', filter],
    queryFn: () => monitorApi.getAlerts(filter),
  });

  const acknowledgeMutation = useMutation({
    mutationFn: (id: number) => monitorApi.alertAction(id, 'acknowledge'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
      message.success('告警已确认');
    },
  });

  const resolveMutation = useMutation({
    mutationFn: (id: number) => monitorApi.alertAction(id, 'resolve'),
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
      render: (severity: string) => <StatusTag status={severity} type="alertSeverity" />,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => <StatusTag status={status} type="alert" />,
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
