import { useState } from 'react';
import { Table, Button, Select, Tag, Space, Card, Timeline } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { PlusOutlined, DeploymentUnitOutlined } from '@ant-design/icons';
import type { Deployment } from '../../types';

// Mock API for now
const mockDeployments: Deployment[] = [
  {
    id: 1,
    projectName: 'ops-manager-web',
    version: 'v2.1.0',
    environment: 'prod',
    status: 'success',
    deployerName: 'admin',
    deployTime: '2024-01-15T10:00:00Z',
    durationSeconds: 180,
    createdAt: '2024-01-15T10:00:00Z',
  },
  {
    id: 2,
    projectName: 'ops-manager-api',
    version: 'v2.1.0',
    environment: 'prod',
    status: 'running',
    deployerName: 'admin',
    deployTime: '2024-01-15T10:05:00Z',
    createdAt: '2024-01-15T10:05:00Z',
  },
];

const deploymentApi = {
  getDeployments: async () => ({ total: mockDeployments.length, items: mockDeployments }),
};

const DeploymentList = () => {
  const [filter, setFilter] = useState({
    environment: undefined as string | undefined,
    status: undefined as string | undefined,
  });

  const { data, isLoading } = useQuery({
    queryKey: ['deployments', filter],
    queryFn: () => deploymentApi.getDeployments(),
  });

  const columns = [
    {
      title: '项目',
      dataIndex: 'projectName',
      key: 'projectName',
    },
    {
      title: '版本',
      dataIndex: 'version',
      key: 'version',
      render: (version: string) => <Tag>{version}</Tag>,
    },
    {
      title: '环境',
      dataIndex: 'environment',
      key: 'environment',
      render: (env: string) => {
        const colorMap: Record<string, string> = {
          dev: 'blue',
          test: 'cyan',
          staging: 'orange',
          prod: 'red',
        };
        const labelMap: Record<string, string> = {
          dev: '开发',
          test: '测试',
          staging: '预发布',
          prod: '生产',
        };
        return <Tag color={colorMap[env]}>{labelMap[env]}</Tag>;
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const colorMap: Record<string, string> = {
          pending: 'default',
          running: 'processing',
          success: 'success',
          failed: 'error',
          rollback: 'warning',
        };
        const labelMap: Record<string, string> = {
          pending: '等待中',
          running: '发布中',
          success: '成功',
          failed: '失败',
          rollback: '已回滚',
        };
        return <Tag color={colorMap[status]}>{labelMap[status]}</Tag>;
      },
    },
    {
      title: '发布人',
      dataIndex: 'deployerName',
      key: 'deployerName',
    },
    {
      title: '发布时间',
      dataIndex: 'deployTime',
      key: 'deployTime',
      render: (time: string) => (time ? new Date(time).toLocaleString() : '-'),
    },
    {
      title: '耗时',
      dataIndex: 'durationSeconds',
      key: 'durationSeconds',
      render: (seconds: number) => (seconds ? `${seconds}s` : '-'),
    },
  ];

  return (
    <div>
      <h1>发布记录</h1>

      <Card style={{ marginBottom: 24 }}>
        <Space wrap>
          <Select
            placeholder="环境"
            value={filter.environment}
            onChange={(value) => setFilter({ ...filter, environment: value })}
            style={{ width: 120 }}
            allowClear
          >
            <Select.Option value="dev">开发</Select.Option>
            <Select.Option value="test">测试</Select.Option>
            <Select.Option value="staging">预发布</Select.Option>
            <Select.Option value="prod">生产</Select.Option>
          </Select>
          <Select
            placeholder="状态"
            value={filter.status}
            onChange={(value) => setFilter({ ...filter, status: value })}
            style={{ width: 120 }}
            allowClear
          >
            <Select.Option value="pending">等待中</Select.Option>
            <Select.Option value="running">发布中</Select.Option>
            <Select.Option value="success">成功</Select.Option>
            <Select.Option value="failed">失败</Select.Option>
          </Select>
          <Button type="primary" icon={<PlusOutlined />}>
            新建发布
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

export default DeploymentList;
