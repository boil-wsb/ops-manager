import { useState } from 'react';
import { Card, Table, Button, Tag, Space, Select } from 'antd';
import { EyeOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { suggestionApi } from '../../services/suggestion';
import type { SuggestionInfo } from '../../services/suggestion';

const statusConfig: Record<string, { color: string; text: string }> = {
  pending: { color: 'orange', text: '待审批' },
  approved: { color: 'blue', text: '已审批' },
  archived: { color: 'green', text: '已存档' },
  rejected: { color: 'default', text: '已驳回' },
};

const SuggestionList = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useState({
    page: 1,
    pageSize: 10,
    status: undefined as string | undefined,
  });

  const { data, isLoading } = useQuery({
    queryKey: ['suggestions', 'list', searchParams],
    queryFn: () => suggestionApi.getList({
      page: searchParams.page,
      pageSize: searchParams.pageSize,
      status: searchParams.status,
    }),
  });

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 60,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const cfg = statusConfig[status] || { color: 'default', text: status };
        return <Tag color={cfg.color}>{cfg.text}</Tag>;
      },
    },
    {
      title: '意见内容',
      dataIndex: 'content',
      key: 'content',
      ellipsis: true,
      render: (content: string) => (
        <span title={content}>
          {content.length > 50 ? content.substring(0, 50) + '...' : content}
        </span>
      ),
    },
    {
      title: '查询码',
      dataIndex: 'queryCode',
      key: 'queryCode',
      width: 100,
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      key: 'createdAt',
      width: 180,
      sorter: (a: SuggestionInfo, b: SuggestionInfo) =>
        new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime(),
      render: (time: string) => new Date(time).toLocaleString('zh-CN'),
    },
    {
      title: '存档时间',
      dataIndex: 'archivedAt',
      key: 'archivedAt',
      width: 180,
      render: (time: string | null) => time ? new Date(time).toLocaleString('zh-CN') : '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 80,
      render: (_: unknown, record: SuggestionInfo) => (
        <Button
          type="link"
          icon={<EyeOutlined />}
          onClick={() => navigate(`/suggestions/manage/${record.id}`)}
        >
          详情
        </Button>
      ),
    },
  ];

  return (
    <div>
      <Card style={{ marginBottom: 16 }}>
        <Space wrap>
          <Select
            placeholder="状态筛选"
            value={searchParams.status}
            onChange={(value) => setSearchParams({ ...searchParams, status: value, page: 1 })}
            style={{ width: 150 }}
            allowClear
          >
            <Select.Option value="pending">待审批</Select.Option>
            <Select.Option value="approved">已审批</Select.Option>
            <Select.Option value="archived">已存档</Select.Option>
            <Select.Option value="rejected">已驳回</Select.Option>
          </Select>
        </Space>
      </Card>

      <Table
        columns={columns}
        dataSource={data?.items || []}
        rowKey="id"
        loading={isLoading}
        pagination={{
          current: searchParams.page,
          pageSize: searchParams.pageSize,
          total: data?.total || 0,
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total) => `共 ${total} 条`,
          onChange: (page, pageSize) => {
            setSearchParams((prev) => ({ ...prev, page, pageSize }));
          },
        }}
      />
    </div>
  );
};

export default SuggestionList;
