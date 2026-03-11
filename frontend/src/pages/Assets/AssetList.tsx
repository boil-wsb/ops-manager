import { useState } from 'react';
import { Table, Button, Input, Select, Tag, Space, Card, message, Popconfirm } from 'antd';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { PlusOutlined, SearchOutlined, DeleteOutlined, EditOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { assetApi } from '../../services/assets';
import type { Asset } from '../../types';

const { Option } = Select;

const AssetList = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useState({
    keyword: '',
    assetType: undefined as string | undefined,
    status: undefined as string | undefined,
  });

  const { data, isLoading } = useQuery({
    queryKey: ['assets', searchParams],
    queryFn: () => assetApi.getAssets(searchParams),
  });

  const deleteMutation = useMutation({
    mutationFn: assetApi.deleteAsset,
    onSuccess: () => {
      message.success('删除成功');
      queryClient.invalidateQueries({ queryKey: ['assets'] });
    },
    onError: () => {
      message.error('删除失败');
    },
  });

  const columns = [
    {
      title: '资产编号',
      dataIndex: 'assetId',
      key: 'assetId',
    },
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: Asset) => (
        <a onClick={() => navigate(`/assets/${record.id}`)}>{text}</a>
      ),
    },
    {
      title: '类型',
      dataIndex: 'assetType',
      key: 'assetType',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const colorMap: Record<string, string> = {
          active: 'green',
          offline: 'red',
          maintenance: 'orange',
          retired: 'gray',
        };
        const labelMap: Record<string, string> = {
          active: '运行中',
          offline: '离线',
          maintenance: '维护中',
          retired: '已退役',
        };
        return <Tag color={colorMap[status] || 'default'}>{labelMap[status] || status}</Tag>;
      },
    },
    {
      title: 'IP地址',
      dataIndex: 'ipAddress',
      key: 'ipAddress',
    },
    {
      title: 'IDC',
      dataIndex: 'idc',
      key: 'idc',
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: Asset) => (
        <Space size="small">
          <Button
            type="text"
            icon={<EditOutlined />}
            onClick={() => navigate(`/assets/${record.id}`)}
          />
          <Popconfirm
            title="确认删除"
            description="确定要删除这个资产吗？"
            onConfirm={() => deleteMutation.mutate(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="text" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <h1>资产管理</h1>
      
      <Card style={{ marginBottom: 24 }}>
        <Space wrap>
          <Input
            placeholder="搜索资产编号/名称/IP"
            prefix={<SearchOutlined />}
            value={searchParams.keyword}
            onChange={(e) => setSearchParams({ ...searchParams, keyword: e.target.value })}
            style={{ width: 250 }}
            allowClear
          />
          <Select
            placeholder="资产类型"
            value={searchParams.assetType}
            onChange={(value) => setSearchParams({ ...searchParams, assetType: value })}
            style={{ width: 120 }}
            allowClear
          >
            <Option value="server">物理机</Option>
            <Option value="vm">虚拟机</Option>
            <Option value="network">网络设备</Option>
            <Option value="storage">存储设备</Option>
          </Select>
          <Select
            placeholder="状态"
            value={searchParams.status}
            onChange={(value) => setSearchParams({ ...searchParams, status: value })}
            style={{ width: 120 }}
            allowClear
          >
            <Option value="active">运行中</Option>
            <Option value="offline">离线</Option>
            <Option value="maintenance">维护中</Option>
            <Option value="retired">已退役</Option>
          </Select>
          <Button type="primary" icon={<PlusOutlined />}>
            新增资产
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
          showQuickJumper: true,
          showTotal: (total) => `共 ${total} 条`,
        }}
      />
    </div>
  );
};

export default AssetList;
