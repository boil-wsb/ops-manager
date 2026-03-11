import { Row, Col, Card, Statistic, Table, Tag } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { ServerOutlined, AlertOutlined, CheckCircleOutlined, ExclamationCircleOutlined } from '@ant-design/icons';
import { assetApi } from '../services/assets';
import type { Asset, Alert } from '../types';

const Dashboard = () => {
  const { data: assetsData } = useQuery({
    queryKey: ['assets', { limit: 1 }],
    queryFn: () => assetApi.getAssets({ limit: 1 }),
  });

  const recentAssets = assetsData?.items.slice(0, 5) || [];

  const assetColumns = [
    {
      title: '资产编号',
      dataIndex: 'assetId',
      key: 'assetId',
    },
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
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
        return <Tag color={colorMap[status] || 'default'}>{status}</Tag>;
      },
    },
    {
      title: 'IP地址',
      dataIndex: 'ipAddress',
      key: 'ipAddress',
    },
  ];

  return (
    <div>
      <h1>仪表盘</h1>
      
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="总资产"
              value={assetsData?.total || 0}
              prefix={<ServerOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="在线资产"
              value={0}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="告警事件"
              value={0}
              prefix={<AlertOutlined />}
              valueStyle={{ color: '#cf1322' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="待处理"
              value={0}
              prefix={<ExclamationCircleOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
      </Row>

      <Card title="最近添加的资产">
        <Table
          columns={assetColumns}
          dataSource={recentAssets}
          rowKey="id"
          pagination={false}
        />
      </Card>
    </div>
  );
};

export default Dashboard;
