import { useParams } from 'react-router-dom';
import { Card, Descriptions, Tag, Button, Space, App, Row, Col, Statistic } from 'antd';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowLeftOutlined, CloudOutlined, ReloadOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { assetApi } from '../../services/assets';
import { usePermission } from '../../hooks/usePermission';

const formatBytes = (bytes: number | undefined | null): string => {
  if (!bytes) return '-';
  const gb = bytes / (1024 * 1024 * 1024);
  if (gb >= 1) {
    return `${gb.toFixed(2)} GB`;
  }
  const mb = bytes / (1024 * 1024);
  if (mb >= 1) {
    return `${mb.toFixed(2)} MB`;
  }
  return `${bytes} Bytes`;
};

const AssetDetail = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { hasPermission } = usePermission();
  const { message } = App.useApp();

  const { data: asset, isLoading } = useQuery({
    queryKey: ['asset', id],
    queryFn: () => assetApi.getAsset(Number(id)),
    enabled: !!id,
  });

  const { data: metrics, isLoading: metricsLoading, refetch: refetchMetrics } = useQuery({
    queryKey: ['asset-metrics', id],
    queryFn: () => assetApi.getAssetMetrics(Number(id)),
    enabled: !!id && asset?.source === 'prometheus',
    refetchInterval: 60000,
  });

  const syncMutation = useMutation({
    mutationFn: () => {
      if (asset?.prometheusInstance) {
        return assetApi.importPrometheusAsset(asset.prometheusInstance);
      }
      throw new Error('No prometheus instance found');
    },
    onSuccess: () => {
      message.success('重新同步成功');
      queryClient.invalidateQueries({ queryKey: ['asset', id] });
    },
    onError: () => {
      message.error('同步失败');
    },
  });

  const statusColorMap: Record<string, string> = {
    active: 'green',
    offline: 'red',
    maintenance: 'orange',
    retired: 'gray',
  };

  const statusLabelMap: Record<string, string> = {
    active: '运行中',
    offline: '离线',
    maintenance: '维护中',
    retired: '已退役',
  };

  const labelsData = asset?.labelsData || {};
  const pcInfoIpAddress = labelsData.ipAddress || asset?.ipAddress || '-';
  const pcInfoOsCaption = labelsData.osCaption || asset?.osType || '-';
  const pcMemoryTotalBytes = labelsData.pc_memory_total_bytes;

  return (
    <div>
      <Space style={{ marginBottom: 24 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/assets')}>
          返回列表
        </Button>
      </Space>

      <Card
        title={
          <Space>
            资产详情
            {asset?.source === 'prometheus' && (
              <Tag icon={<CloudOutlined />} color="blue">
                从 Prometheus 同步
              </Tag>
            )}
          </Space>
        }
        loading={isLoading}
        extra={
          asset?.source === 'prometheus' && hasPermission('asset:admin') ? (
            <Button
              icon={<ReloadOutlined spin={syncMutation.isPending} />}
              onClick={() => syncMutation.mutate()}
              loading={syncMutation.isPending}
            >
              重新同步
            </Button>
          ) : null
        }
      >
        {asset && (
          <>
            <Descriptions title="基本信息" bordered column={2}>
              <Descriptions.Item label="资产编号">{asset.assetId}</Descriptions.Item>
              <Descriptions.Item label="名称">{asset.name}</Descriptions.Item>
              <Descriptions.Item label="类型">{asset.assetType}</Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={statusColorMap[asset.status]}>
                  {statusLabelMap[asset.status]}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="负责人">
                {asset.owner ? (
                  <Space>
                    <span>{asset.owner.name || asset.owner.username}</span>
                  </Space>
                ) : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="标签">
                {asset.labels && asset.labels.length > 0 ? (
                  asset.labels.map((label) => (
                    <Tag key={label.id} color={label.color}>
                      {label.name}
                    </Tag>
                  ))
                ) : '-'}
              </Descriptions.Item>
              {asset.source === 'prometheus' && (
                <>
                  <Descriptions.Item label="同步状态">
                    <Tag color={asset.syncStatus === 'synced' ? 'green' : asset.syncStatus === 'error' ? 'red' : 'orange'}>
                      {asset.syncStatus === 'synced' ? '已同步' : asset.syncStatus === 'error' ? '同步失败' : '待同步'}
                    </Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="上次同步">
                    {asset.lastSyncTime ? new Date(asset.lastSyncTime).toLocaleString('zh-CN') : '-'}
                  </Descriptions.Item>
                </>
              )}
              <Descriptions.Item label="创建时间">{asset.createdAt}</Descriptions.Item>
              <Descriptions.Item label="更新时间">{asset.updatedAt}</Descriptions.Item>
            </Descriptions>

            <Descriptions title="网络信息" bordered column={2} style={{ marginTop: 24 }}>
              <Descriptions.Item label="IP地址">{pcInfoIpAddress}</Descriptions.Item>
              <Descriptions.Item label="内网IP">{asset.privateIp || '-'}</Descriptions.Item>
              <Descriptions.Item label="MAC地址">{asset.macAddress || '-'}</Descriptions.Item>
            </Descriptions>

            <Descriptions title="硬件信息" bordered column={2} style={{ marginTop: 24 }}>
              <Descriptions.Item label="CPU核数">{asset.cpuCores || '-'}</Descriptions.Item>
              <Descriptions.Item label="内存">
                {pcMemoryTotalBytes ? formatBytes(Number(pcMemoryTotalBytes)) : (asset.memoryGb ? `${asset.memoryGb} GB` : '-')}
              </Descriptions.Item>
              <Descriptions.Item label="磁盘(GB)">{asset.diskGb || '-'}</Descriptions.Item>
              <Descriptions.Item label="操作系统">{pcInfoOsCaption}</Descriptions.Item>
              <Descriptions.Item label="系统版本">{asset.osVersion || '-'}</Descriptions.Item>
            </Descriptions>

            <Descriptions title="位置信息" bordered column={2} style={{ marginTop: 24 }}>
              <Descriptions.Item label="IDC">{asset.idc || '-'}</Descriptions.Item>
              <Descriptions.Item label="区域">{asset.region || '-'}</Descriptions.Item>
              <Descriptions.Item label="机架">{asset.rack || '-'}</Descriptions.Item>
            </Descriptions>

            {asset.description && (
              <Descriptions title="描述" bordered column={1} style={{ marginTop: 24 }}>
                <Descriptions.Item label="描述">{asset.description}</Descriptions.Item>
              </Descriptions>
            )}

            {asset.source === 'prometheus' && (
              <Card title="实时指标" style={{ marginTop: 24 }} loading={metricsLoading}>
                {metrics?.metrics ? (
                  <Row gutter={16}>
                    {metrics.metrics.cpu && (
                      <Col span={6}>
                        <Card size="small">
                          <Statistic
                            title="CPU 使用率"
                            value={metrics.metrics.cpu.usagePercent}
                            suffix="%"
                            precision={1}
                            styles={{
                              content: {
                                color: metrics.metrics.cpu.usagePercent > 80 ? '#cf1322' :
                                       metrics.metrics.cpu.usagePercent > 60 ? '#faad14' : '#3f8600'
                              }
                            }}
                          />
                          <div style={{ fontSize: 12, color: '#999', marginTop: 8 }}>
                            {metrics.metrics.cpu.cores} 核
                          </div>
                        </Card>
                      </Col>
                    )}
                    {metrics.metrics.memory && (
                      <Col span={6}>
                        <Card size="small">
                          <Statistic
                            title="内存使用率"
                            value={metrics.metrics.memory.usagePercent}
                            suffix="%"
                            precision={1}
                            styles={{
                              content: {
                                color: metrics.metrics.memory.usagePercent > 80 ? '#cf1322' :
                                       metrics.metrics.memory.usagePercent > 60 ? '#faad14' : '#3f8600'
                              }
                            }}
                          />
                          <div style={{ fontSize: 12, color: '#999', marginTop: 8 }}>
                            已用 {metrics.metrics.memory.usedGB.toFixed(1)} / 总共 {metrics.metrics.memory.totalGB.toFixed(1)} GB
                          </div>
                        </Card>
                      </Col>
                    )}
                    {metrics.metrics.disk && (
                      <Col span={6}>
                        <Card size="small">
                          <Statistic
                            title="磁盘使用率"
                            value={metrics.metrics.disk.usagePercent}
                            suffix="%"
                            precision={1}
                            styles={{
                              content: {
                                color: metrics.metrics.disk.usagePercent > 80 ? '#cf1322' :
                                       metrics.metrics.disk.usagePercent > 60 ? '#faad14' : '#3f8600'
                              }
                            }}
                          />
                          <div style={{ fontSize: 12, color: '#999', marginTop: 8 }}>
                            已用 {metrics.metrics.disk.usedGB.toFixed(1)} / 总共 {metrics.metrics.disk.totalGB.toFixed(1)} GB
                          </div>
                        </Card>
                      </Col>
                    )}
                    {metrics.metrics.network && (
                      <Col span={6}>
                        <Card size="small">
                          <Statistic
                            title="网络接收"
                            value={metrics.metrics.network.receiveRate}
                            suffix="KB/s"
                            precision={1}
                          />
                          <div style={{ fontSize: 12, color: '#999', marginTop: 8 }}>
                            发送: {metrics.metrics.network.transmitRate.toFixed(1)} KB/s
                          </div>
                        </Card>
                      </Col>
                    )}
                  </Row>
                ) : (
                  <div style={{ textAlign: 'center', padding: '20px', color: '#999' }}>
                    暂无实时指标数据
                  </div>
                )}
                <div style={{ textAlign: 'right', marginTop: 16 }}>
                  <Button
                    size="small"
                    icon={<ReloadOutlined />}
                    onClick={() => refetchMetrics()}
                  >
                    刷新指标
                  </Button>
                </div>
              </Card>
            )}
          </>
        )}
      </Card>
    </div>
  );
};

export default AssetDetail;
