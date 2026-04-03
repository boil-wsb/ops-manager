import { useState } from 'react';
import { Table, Button, Select, Tag, Space, Card } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { PlusOutlined } from '@ant-design/icons';
import { opsApi } from '../../services/ops';
import StatusTag from '../../components/StatusTag';

const DeploymentList = () => {
  const [filter, setFilter] = useState({
    environment: undefined as string | undefined,
    status: undefined as string | undefined,
  });
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
  });

  const { data, isLoading } = useQuery({
    queryKey: ['deployments', filter, pagination],
    queryFn: () =>
      opsApi.getDeployments({
        skip: (pagination.current - 1) * pagination.pageSize,
        limit: pagination.pageSize,
        environment: filter.environment,
        status: filter.status,
      }),
  });
  const columns = [
    {
      title: '项目',
      dataIndex: 'projectName',
      key: 'projectName',
      sorter: (a: Record<string, unknown>, b: Record<string, unknown>) => (a.projectName as string || '').localeCompare(b.projectName as string || ''),
    },
    {
      title: '版本',
      dataIndex: 'version',
      key: 'version',
      sorter: (a: Record<string, unknown>, b: Record<string, unknown>) => (a.version as string || '').localeCompare(b.version as string || ''),
      render: (version: string) => <Tag>{version || '-'}</Tag>,
    },
    {
      title: '环境',
      dataIndex: 'environment',
      key: 'environment',
      sorter: (a: Record<string, unknown>, b: Record<string, unknown>) => (a.environment as string || '').localeCompare(b.environment as string || ''),
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
        return <Tag color={colorMap[env]}>{labelMap[env] || env}</Tag>;
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      sorter: (a: Record<string, unknown>, b: Record<string, unknown>) => (a.status as string || '').localeCompare(b.status as string || ''),
      render: (status: string) => <StatusTag status={status} type="deployment" />,
    },
    {
      title: '发布人',
      dataIndex: 'deployerName',
      key: 'deployerName',
      sorter: (a: Record<string, unknown>, b: Record<string, unknown>) => (a.deployerName as string || '').localeCompare(b.deployerName as string || ''),
    },
    {
      title: '发布时间',
      dataIndex: 'deployTime',
      key: 'deployTime',
      sorter: (a: Record<string, unknown>, b: Record<string, unknown>) => {
        const aTime = a.deployTime as string | undefined;
        const bTime = b.deployTime as string | undefined;
        if (!aTime && !bTime) return 0;
        if (!aTime) return 1;
        if (!bTime) return -1;
        return new Date(aTime).getTime() - new Date(bTime).getTime();
      },
      render: (time: string) => (time ? new Date(time).toLocaleString() : '-'),
    },
    {
      title: '耗时',
      dataIndex: 'durationSeconds',
      key: 'durationSeconds',
      sorter: (a: Record<string, unknown>, b: Record<string, unknown>) => (a.durationSeconds as number || 0) - (b.durationSeconds as number || 0),
      render: (seconds: number) => (seconds ? `${seconds}s` : '-'),
    },
  ];

  return (
    <div>
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

export default DeploymentList;
