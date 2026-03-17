import { useState } from 'react';
import { Table, Button, Select, Tag, Space, Card, Switch, message } from 'antd';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { PlusOutlined, PlayCircleOutlined, PauseCircleOutlined } from '@ant-design/icons';
import { monitorApi } from '../../services/monitor';
import StatusTag from '../../components/StatusTag';
import type { Monitor } from '../../types';

const MonitorList = () => {
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState({
    monitorType: undefined as string | undefined,
    status: undefined as string | undefined,
  });
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
  });

  const { data, isLoading } = useQuery({
    queryKey: ['monitors', filter, pagination],
    queryFn: () =>
      monitorApi.getMonitors({
        skip: (pagination.current - 1) * pagination.pageSize,
        limit: pagination.pageSize,
        monitor_type: filter.monitorType,
        status: filter.status,
      }),
  });

  const toggleMutation = useMutation({
    mutationFn: (id: number) => monitorApi.toggleMonitor(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['monitors'] });
      message.success('状态已更新');
    },
    onError: () => {
      message.error('操作失败');
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
      render: (type: string) => type?.toUpperCase() || '-',
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
      render: (status: string) => <StatusTag status={status} type="monitor" />,
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
          onChange={() => toggleMutation.mutate(record.id)}
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
