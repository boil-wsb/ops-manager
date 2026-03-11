import { useParams } from 'react-router-dom';
import { Card, Descriptions, Tag, Button, Space } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeftOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { assetApi } from '../../services/assets';

const AssetDetail = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: asset, isLoading } = useQuery({
    queryKey: ['asset', id],
    queryFn: () => assetApi.getAsset(Number(id)),
    enabled: !!id,
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

  return (
    <div>
      <Space style={{ marginBottom: 24 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/assets')}>
          返回列表
        </Button>
      </Space>

      <Card title="资产详情" loading={isLoading}>
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
              <Descriptions.Item label="创建时间">{asset.createdAt}</Descriptions.Item>
              <Descriptions.Item label="更新时间">{asset.updatedAt}</Descriptions.Item>
            </Descriptions>

            <Descriptions title="网络信息" bordered column={2} style={{ marginTop: 24 }}>
              <Descriptions.Item label="公网IP">{asset.ipAddress || '-'}</Descriptions.Item>
              <Descriptions.Item label="内网IP">{asset.privateIp || '-'}</Descriptions.Item>
              <Descriptions.Item label="MAC地址">{asset.macAddress || '-'}</Descriptions.Item>
            </Descriptions>

            <Descriptions title="硬件信息" bordered column={2} style={{ marginTop: 24 }}>
              <Descriptions.Item label="CPU核数">{asset.cpuCores || '-'}</Descriptions.Item>
              <Descriptions.Item label="内存(GB)">{asset.memoryGb || '-'}</Descriptions.Item>
              <Descriptions.Item label="磁盘(GB)">{asset.diskGb || '-'}</Descriptions.Item>
              <Descriptions.Item label="操作系统">{asset.osType || '-'}</Descriptions.Item>
              <Descriptions.Item label="系统版本">{asset.osVersion || '-'}</Descriptions.Item>
            </Descriptions>

            <Descriptions title="位置信息" bordered column={2} style={{ marginTop: 24 }}>
              <Descriptions.Item label="IDC">{asset.idc || '-'}</Descriptions.Item>
              <Descriptions.Item label="区域">{asset.region || '-'}</Descriptions.Item>
              <Descriptions.Item label="机架">{asset.rack || '-'}</Descriptions.Item>
            </Descriptions>

            {asset.labels.length > 0 && (
              <Descriptions title="标签" bordered column={1} style={{ marginTop: 24 }}>
                <Descriptions.Item label="标签">
                  {asset.labels.map((label) => (
                    <Tag key={label.id} color={label.color}>
                      {label.name}
                    </Tag>
                  ))}
                </Descriptions.Item>
              </Descriptions>
            )}

            {asset.description && (
              <Descriptions title="描述" bordered column={1} style={{ marginTop: 24 }}>
                <Descriptions.Item label="描述">{asset.description}</Descriptions.Item>
              </Descriptions>
            )}
          </>
        )}
      </Card>
    </div>
  );
};

export default AssetDetail;
