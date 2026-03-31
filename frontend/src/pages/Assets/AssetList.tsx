import { useState } from 'react';
import { Table, Button, Input, Select, Tag, Space, Card, Popconfirm, Tooltip, Tabs, App, Alert } from 'antd';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { PlusOutlined, SearchOutlined, DeleteOutlined, EditOutlined, SyncOutlined, CloudOutlined, CompassOutlined, UserOutlined, DesktopOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { assetApi } from '../../services/assets';
import { PermissionGuard } from '../../components/PermissionGuard';
import StatusTag from '../../components/StatusTag';
import AssetFormModal from './AssetFormModal';
import type { Asset } from '../../types';
import type { TablePaginationConfig } from 'antd';
import { useAuthStore } from '../../stores/authStore';

const { Option } = Select;

const LinkButton: React.FC<{ text: string; record: Asset; onClick: (id: number) => void }> = ({
  text,
  record,
  onClick,
}) => (
  <Button type="link" onClick={() => onClick(record.id)}>
    {text}
  </Button>
);

const AssetList = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { message } = App.useApp();
  const user = useAuthStore((state) => state.user);
  const isViewer = user?.roles?.some(role => role.name === 'viewer') ?? false;
  const [activeTab, setActiveTab] = useState('servers');
  const [searchParams, setSearchParams] = useState({
    keyword: '',
    status: undefined as string | undefined,
  });
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 20,
  });
  const [modalOpen, setModalOpen] = useState(false);
  const [editingAsset, setEditingAsset] = useState<Asset | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['assets', searchParams, pagination, activeTab],
    queryFn: () => {
      if (activeTab === 'terminals') {
        return assetApi.getTerminals({
          ...searchParams,
          skip: (pagination.current - 1) * pagination.pageSize,
          limit: pagination.pageSize,
        });
      }
      return assetApi.getAssets({
        ...searchParams,
        skip: (pagination.current - 1) * pagination.pageSize,
        limit: pagination.pageSize,
      });
    },
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

  const syncMutation = useMutation({
    mutationFn: assetApi.syncAssetsFromPrometheus,
    onSuccess: () => {
      message.success('同步任务已触发');
      queryClient.invalidateQueries({ queryKey: ['assets'] });
    },
    onError: () => {
      message.error('同步失败');
    },
  });

  const syncTerminalsMutation = useMutation({
    mutationFn: assetApi.syncTerminalsFromPcInfo,
    onSuccess: (data) => {
      message.success(`终端同步完成: 发现 ${data.totalDiscovered} 台, 新增 ${data.created} 台, 更新 ${data.updated} 台`);
      queryClient.invalidateQueries({ queryKey: ['assets'] });
    },
    onError: () => {
      message.error('终端同步失败');
    },
  });

  const handleAddAsset = () => {
    setEditingAsset(null);
    setModalOpen(true);
  };

  const handleEditAsset = (asset: Asset) => {
    setEditingAsset(asset);
    setModalOpen(true);
  };

  const handleModalClose = () => {
    setModalOpen(false);
    setEditingAsset(null);
  };

  const handleTableChange = (paginationConfig: TablePaginationConfig) => {
    setPagination({
      current: paginationConfig.current || 1,
      pageSize: paginationConfig.pageSize || 20,
    });
  };

  const handleTabChange = (key: string) => {
    setActiveTab(key);
    setPagination({ current: 1, pageSize: 20 });
    setSearchParams({ keyword: '', status: undefined });
  };

  const serverColumns = [
    {
      title: '资产名称',
      dataIndex: 'name',
      key: 'name',
      sorter: (a: Asset, b: Asset) => a.name.localeCompare(b.name),
      render: (text: string, record: Asset) => (
        <LinkButton text={text || '-'} record={record} onClick={(id) => navigate(`/assets/${id}`)} />
      ),
    },
    {
      title: '类型',
      dataIndex: 'assetType',
      key: 'assetType',
      sorter: (a: Asset, b: Asset) => (a.assetType || '').localeCompare(b.assetType || ''),
      render: (assetType: string) => {
        const typeMap: Record<string, { label: string; color: string }> = {
          SERVER: { label: '物理机', color: 'blue' },
          VM: { label: '虚拟机', color: 'cyan' },
          NETWORK: { label: '网络设备', color: 'purple' },
          STORAGE: { label: '存储设备', color: 'orange' },
        };
        const typeInfo = typeMap[assetType] || { label: assetType || '-', color: 'default' };
        return <Tag color={typeInfo.color}>{typeInfo.label}</Tag>;
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      sorter: (a: Asset, b: Asset) => (a.status || '').localeCompare(b.status || ''),
      render: (status: string) => <StatusTag status={status} type="asset" />,
    },
    {
      title: 'IP地址',
      dataIndex: 'ipAddress',
      key: 'ipAddress',
      sorter: (a: Asset, b: Asset) => (a.ipAddress || '').localeCompare(b.ipAddress || ''),
      render: (ipAddress: string) => ipAddress || '-',
    },
    {
      title: '配置',
      key: 'specs',
      render: (_: unknown, record: Asset) => {
        const parts = [];
        if (record.cpuCores) parts.push(`${record.cpuCores}核`);
        if (record.memoryGb) parts.push(`${record.memoryGb}GB`);
        if (parts.length === 0) return '-';
        return <span style={{ color: 'var(--text-secondary)' }}>{parts.join(' / ')}</span>;
      },
    },
    {
      title: '操作系统',
      key: 'os',
      render: (_: unknown, record: Asset) => {
        if (!record.osType && !record.osVersion) return '-';
        return (
          <Tooltip title={record.osVersion || ''}>
            <span>{record.osType || '-'}</span>
          </Tooltip>
        );
      },
    },
    {
      title: '负责人',
      dataIndex: 'ownerName',
      key: 'ownerName',
      sorter: (a: Asset, b: Asset) => {
        return (a.ownerName || '').localeCompare(b.ownerName || '');
      },
      render: (ownerName: string | null | undefined) => {
        if (!ownerName) return <span style={{ color: 'var(--text-tertiary)' }}>未分配</span>;
        return (
          <Space>
            <UserOutlined style={{ color: '#1890ff' }} />
            <span>{ownerName}</span>
          </Space>
        );
      },
    },
    {
      title: '数据来源',
      dataIndex: 'source',
      key: 'source',
      sorter: (a: Asset, b: Asset) => (a.source || '').localeCompare(b.source || ''),
      render: (source: string) => {
        if (source === 'PROMETHEUS') {
          return (
            <Tooltip title="从 Prometheus 自动同步">
              <Tag icon={<CloudOutlined />} color="blue">Prometheus</Tag>
            </Tooltip>
          );
        }
        return <Tag>手动录入</Tag>;
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_: unknown, record: Asset) => (
        <Space size="small">
          <PermissionGuard permissions="asset:write">
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => handleEditAsset(record)}
            />
          </PermissionGuard>
          <PermissionGuard permissions="asset:delete">
            <Popconfirm
              title="确认删除"
              description="确定要删除这个资产吗？"
              onConfirm={() => deleteMutation.mutate(record.id)}
              okText="确定"
              cancelText="取消"
            >
              <Button type="text" danger icon={<DeleteOutlined />} />
            </Popconfirm>
          </PermissionGuard>
        </Space>
      ),
    },
  ];

  const terminalColumns = [
    {
      title: '主机名',
      dataIndex: 'name',
      key: 'name',
      width: 150,
      sorter: (a: Asset, b: Asset) => a.name.localeCompare(b.name),
      render: (text: string, record: Asset) => (
        <LinkButton text={text || '-'} record={record} onClick={(id) => navigate(`/assets/${id}`)} />
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 80,
      render: (status: string) => <StatusTag status={status} type="terminal" />,
    },
    {
      title: '序列号',
      dataIndex: 'serialNumber',
      key: 'serialNumber',
      width: 120,
      render: (serialNumber: string) => serialNumber || '-',
    },
    {
      title: 'UUID',
      dataIndex: 'uuid',
      key: 'uuid',
      width: 180,
      ellipsis: true,
      render: (uuid: string) => uuid ? (
        <Tooltip title={uuid}>
          <span style={{ fontFamily: 'monospace', fontSize: 12 }}>{uuid}</span>
        </Tooltip>
      ) : '-',
    },
    {
      title: '用户',
      dataIndex: 'customer',
      key: 'customer',
      width: 100,
      render: (customer: string) => customer ? <Tag color="blue">{customer}</Tag> : '-',
    },
    {
      title: 'IP地址',
      key: 'ipAddress',
      width: 130,
      render: (_: unknown, record: Asset) => {
        const labelsData = record.labelsData as Record<string, string | number | boolean> | undefined;
        const ipAddress = labelsData?.ipAddress || labelsData?.ip_address as string | undefined;
        return ipAddress || record.ipAddress || '-';
      },
    },
    {
      title: '操作系统',
      key: 'os',
      width: 150,
      render: (_: unknown, record: Asset) => {
        const labelsData = record.labelsData as Record<string, string> | undefined;
        const osCaption = labelsData?.osCaption || labelsData?.os_caption;
        const osType = record.osType;
        const osVersion = record.osVersion;
        
        if (!osCaption && !osType && !osVersion) return '-';
        
        const displayText = osCaption || osType || '-';
        const tooltipText = osVersion || osCaption || '';
        
        return (
          <Tooltip title={tooltipText}>
            <span>{displayText}</span>
          </Tooltip>
        );
      },
    },
    {
      title: '所有标签',
      key: 'labels',
      width: 250,
      render: (_: unknown, record: Asset) => {
        const labelsData = record.labelsData;
        if (!labelsData || Object.keys(labelsData).length === 0) return '-';
        const displayLabels = Object.entries(labelsData)
          .filter(([key]) => !['hostname', 'serial', 'uuid', 'customer', 'instance', 'job', '__name__'].includes(key))
          .slice(0, 5);
        if (displayLabels.length === 0) return '-';
        return (
          <Tooltip
            title={
              <div>
                {Object.entries(labelsData).map(([key, value]) => (
                  <div key={key}><strong>{key}</strong>: {String(value)}</div>
                ))}
              </div>
            }
          >
            <Space size={4} wrap>
              {displayLabels.map(([key, value]) => (
                <Tag key={key} style={{ fontSize: 11 }}>
                  {key}: {String(value).substring(0, 15)}{String(value).length > 15 ? '...' : ''}
                </Tag>
              ))}
            </Space>
          </Tooltip>
        );
      },
    },
    {
      title: '上次同步',
      dataIndex: 'lastSyncTime',
      key: 'lastSyncTime',
      width: 120,
      render: (lastSyncTime: string) => {
        if (!lastSyncTime) return '-';
        return new Date(lastSyncTime).toLocaleString('zh-CN');
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_: unknown, record: Asset) => (
        <Space size="small">
          <PermissionGuard permissions="asset:write">
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => handleEditAsset(record)}
            />
          </PermissionGuard>
          <PermissionGuard permissions="asset:delete">
            <Popconfirm
              title="确认删除"
              description="确定要删除这个终端吗？"
              onConfirm={() => deleteMutation.mutate(record.id)}
              okText="确定"
              cancelText="取消"
            >
              <Button type="text" danger icon={<DeleteOutlined />} />
            </Popconfirm>
          </PermissionGuard>
        </Space>
      ),
    },
  ];

  const tabItems = [
    {
      key: 'servers',
      label: (
        <span>
          <CloudOutlined style={{ marginRight: 8 }} />
          服务器资产
        </span>
      ),
      children: (
        <>
          <Card style={{ marginBottom: 16 }}>
            <Space wrap>
              <Input
                placeholder="搜索资产名称/IP"
                prefix={<SearchOutlined />}
                value={searchParams.keyword}
                onChange={(e) => {
                  setSearchParams({ ...searchParams, keyword: e.target.value });
                  setPagination({ ...pagination, current: 1 });
                }}
                style={{ width: 250 }}
                allowClear
              />
              <Select
                placeholder="状态"
                value={searchParams.status}
                onChange={(value) => {
                  setSearchParams({ ...searchParams, status: value });
                  setPagination({ ...pagination, current: 1 });
                }}
                style={{ width: 120 }}
                allowClear
              >
                <Option value="ACTIVE">运行中</Option>
                <Option value="OFFLINE">离线</Option>
                <Option value="MAINTENANCE">维护中</Option>
                <Option value="RETIRED">已退役</Option>
              </Select>
              <PermissionGuard permissions="asset:write">
                <Button type="primary" icon={<PlusOutlined />} onClick={handleAddAsset}>
                  新增资产
                </Button>
              </PermissionGuard>
              <PermissionGuard permissions="asset:admin">
                <Button
                  icon={<SyncOutlined spin={syncMutation.isPending} />}
                  onClick={() => syncMutation.mutate()}
                  loading={syncMutation.isPending}
                >
                  从 Prometheus 同步
                </Button>
              </PermissionGuard>
              <PermissionGuard permissions="asset:write">
                <Button
                  icon={<CompassOutlined />}
                  onClick={() => navigate('/assets/discovery')}
                >
                  发现资产
                </Button>
              </PermissionGuard>
            </Space>
          </Card>
          <Table
            columns={serverColumns}
            dataSource={data?.items || []}
            rowKey="id"
            loading={isLoading}
            pagination={{
              current: pagination.current,
              pageSize: pagination.pageSize,
              total: data?.total || 0,
              showSizeChanger: true,
              showQuickJumper: true,
              showTotal: (total) => `共 ${total} 条`,
              pageSizeOptions: ['10', '20', '50', '100'],
            }}
            onChange={handleTableChange}
            scroll={{ x: 1400 }}
          />
        </>
      ),
    },
    {
      key: 'terminals',
      label: (
        <span>
          <DesktopOutlined style={{ marginRight: 8 }} />
          终端资产
        </span>
      ),
      children: (
        <>
          <Card style={{ marginBottom: 16 }}>
            <Space wrap>
              <Input
                placeholder="搜索主机名/序列号"
                prefix={<SearchOutlined />}
                value={searchParams.keyword}
                onChange={(e) => {
                  setSearchParams({ ...searchParams, keyword: e.target.value });
                  setPagination({ ...pagination, current: 1 });
                }}
                style={{ width: 250 }}
                allowClear
              />
              <Select
                placeholder="状态"
                value={searchParams.status}
                onChange={(value) => {
                  setSearchParams({ ...searchParams, status: value });
                  setPagination({ ...pagination, current: 1 });
                }}
                style={{ width: 120 }}
                allowClear
              >
                <Option value="ACTIVE">在线</Option>
                <Option value="OFFLINE">离线</Option>
              </Select>
              <PermissionGuard permissions="asset:admin">
                <Button
                  type="primary"
                  icon={<SyncOutlined spin={syncTerminalsMutation.isPending} />}
                  onClick={() => syncTerminalsMutation.mutate()}
                  loading={syncTerminalsMutation.isPending}
                >
                  从 pc_info 同步
                </Button>
              </PermissionGuard>
            </Space>
          </Card>
          <Table
            columns={terminalColumns}
            dataSource={data?.items || []}
            rowKey="id"
            loading={isLoading}
            pagination={{
              current: pagination.current,
              pageSize: pagination.pageSize,
              total: data?.total || 0,
              showSizeChanger: true,
              showQuickJumper: true,
              showTotal: (total) => `共 ${total} 条`,
              pageSizeOptions: ['10', '20', '50', '100'],
            }}
            onChange={handleTableChange}
            scroll={{ x: 1200 }}
          />
        </>
      ),
    },
  ];

  return (
    <div>
      {isViewer && activeTab === 'servers' && (
        <Alert
          message="视图模式"
          description="您正在查看由您负责的服务器资产。如需查看全部资产，请联系管理员。"
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}
      <Tabs
        activeKey={activeTab}
        items={tabItems}
        onChange={handleTabChange}
      />
      <AssetFormModal
        open={modalOpen}
        onClose={handleModalClose}
        asset={editingAsset}
      />
    </div>
  );
};

export default AssetList;
