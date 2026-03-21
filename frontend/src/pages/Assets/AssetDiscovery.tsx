import { useState } from 'react';
import { Card, Table, Button, Tag, Space, App, Alert, Statistic, Row, Col, Popconfirm } from 'antd';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { CloudOutlined, ImportOutlined, ReloadOutlined, ArrowLeftOutlined, CheckSquareOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { assetApi } from '../../services/assets';

const AssetDiscovery = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { message } = App.useApp();
  const [importingInstances, setImportingInstances] = useState<Set<string>>(new Set());
  const [selectedInstances, setSelectedInstances] = useState<string[]>([]);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['prometheus-discovery'],
    queryFn: () => assetApi.discoverPrometheusAssets(),
  });

  const importMutation = useMutation({
    mutationFn: async (instance: string) => {
      setImportingInstances(prev => new Set(prev).add(instance));
      try {
        const result = await assetApi.importPrometheusAsset(instance);
        return result;
      } finally {
        setImportingInstances(prev => {
          const newSet = new Set(prev);
          newSet.delete(instance);
          return newSet;
        });
      }
    },
    onSuccess: (result) => {
      message.success(`成功导入资产: ${result.asset.name}`);
      queryClient.invalidateQueries({ queryKey: ['prometheus-discovery'] });
      queryClient.invalidateQueries({ queryKey: ['assets'] });
    },
    onError: (error: Error) => {
      message.error(`导入失败: ${error.message || '未知错误'}`);
    },
  });

  const batchImportMutation = useMutation({
    mutationFn: async (instances: string[]) => {
      const results = [];
      const errors = [];

      for (const instance of instances) {
        setImportingInstances(prev => new Set(prev).add(instance));
        try {
          const result = await assetApi.importPrometheusAsset(instance);
          results.push(result);
        } catch (error: unknown) {
          const err = error as Error;
          errors.push({ instance, error: err.message || '未知错误' });
        } finally {
          setImportingInstances(prev => {
            const newSet = new Set(prev);
            newSet.delete(instance);
            return newSet;
          });
        }
      }

      return { results, errors };
    },
    onSuccess: ({ results, errors }) => {
      if (results.length > 0) {
        message.success(`成功导入 ${results.length} 个资产`);
      }
      if (errors.length > 0) {
        message.warning(`${errors.length} 个资产导入失败`);
        console.error('导入失败的资产:', errors);
      }
      setSelectedInstances([]);
      queryClient.invalidateQueries({ queryKey: ['prometheus-discovery'] });
      queryClient.invalidateQueries({ queryKey: ['assets'] });
    },
    onError: (error: Error) => {
      message.error(`批量导入失败: ${error.message || '未知错误'}`);
    },
  });

  const handleBatchImport = () => {
    if (selectedInstances.length === 0) {
      message.warning('请先选择要导入的节点');
      return;
    }
    batchImportMutation.mutate(selectedInstances);
  };

  const columns = [
    {
      title: 'IP地址',
      dataIndex: 'ipAddress',
      key: 'ipAddress',
    },
    {
      title: '主机名',
      dataIndex: 'nodename',
      key: 'nodename',
      render: (text: string) => text || '-',
    },
    {
      title: '操作系统',
      key: 'os',
      render: (_: unknown, record: Record<string, unknown>) => (
        <Space size={0}>
          <span>{(record.sysname as string) || '-'}</span>
          <span style={{ fontSize: 12, color: '#999' }}>{(record.release as string) || ''}</span>
        </Space>
      ),
    },
    {
      title: '架构',
      dataIndex: 'machine',
      key: 'machine',
      render: (text: string) => text || '-',
    },
    {
      title: 'Job',
      dataIndex: 'job',
      key: 'job',
      render: (text: string) => <Tag color="blue">{text}</Tag>,
    },
    {
      title: '环境',
      dataIndex: 'env',
      key: 'env',
      render: (text: string) => text ? <Tag color="green">{text}</Tag> : '-',
    },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: Record<string, unknown>) => {
        const instanceId = record.instance as string;
        return (
          <Button
            type="primary"
            size="small"
            icon={<ImportOutlined />}
            onClick={() => importMutation.mutate(instanceId)}
            loading={importingInstances.has(instanceId)}
            disabled={importingInstances.has(instanceId)}
          >
            导入
          </Button>
        );
      },
    },
  ];

  const rowSelection = {
    selectedRowKeys: selectedInstances,
    onChange: (selectedRowKeys: React.Key[]) => {
      setSelectedInstances(selectedRowKeys as string[]);
    },
  };

  return (
    <div>
      <Space style={{ marginBottom: 24 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/assets')}>
          返回资产列表
        </Button>
      </Space>

      <Card
        title={
          <Space>
            <CloudOutlined />
            Prometheus 资产发现
          </Space>
        }
        extra={
          <Button icon={<ReloadOutlined />} onClick={() => refetch()} loading={isLoading}>
            刷新
          </Button>
        }
      >
        <Alert
          description="此页面显示 Prometheus 中监控但尚未导入资产系统的节点。选择节点后点击「批量导入」按钮可一次性导入多个资产。"
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />

        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={8}>
            <Card size="small">
              <Statistic
                title="Prometheus 总节点数"
                value={data?.total || 0}
                style={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
          <Col span={8}>
            <Card size="small">
              <Statistic
                title="已导入资产数"
                value={data?.existing || 0}
                style={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
          <Col span={8}>
            <Card size="small">
              <Statistic
                title="待导入节点数"
                value={data?.discovered || 0}
                style={{ color: data?.discovered ? '#faad14' : '#999' }}
              />
            </Card>
          </Col>
        </Row>

        <Space style={{ marginBottom: 16 }}>
          <Popconfirm
            title="批量导入"
            description={`确定要导入选中的 ${selectedInstances.length} 个节点吗？`}
            onConfirm={handleBatchImport}
            okText="确定"
            cancelText="取消"
            disabled={selectedInstances.length === 0}
          >
            <Button
              type="primary"
              icon={<CheckSquareOutlined />}
              loading={batchImportMutation.isPending}
              disabled={selectedInstances.length === 0}
            >
              批量导入 ({selectedInstances.length})
            </Button>
          </Popconfirm>
          {selectedInstances.length > 0 && (
            <Button onClick={() => setSelectedInstances([])}>
              清空选择
            </Button>
          )}
        </Space>

        <Table
          columns={columns}
          dataSource={data?.nodes || []}
          rowKey="instance"
          loading={isLoading}
          rowSelection={rowSelection}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 个待导入节点`,
          }}
          locale={{
            emptyText: '没有发现新的节点，所有 Prometheus 节点都已导入',
          }}
        />
      </Card>
    </div>
  );
};

export default AssetDiscovery;
