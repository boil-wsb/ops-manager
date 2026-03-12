import { Row, Col, Card, Statistic, Table, Tag, Progress, List, Avatar, Badge } from 'antd';
import { useQuery } from '@tanstack/react-query';
import {
  DatabaseOutlined,
  AlertOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  SafetyCertificateOutlined,
  DeploymentUnitOutlined,
  ClockCircleOutlined,
  RiseOutlined,
  FallOutlined,
} from '@ant-design/icons';
import { assetApi } from '../services/assets';
import type { Asset } from '../types';

const Dashboard = () => {
  const { data: assetsData } = useQuery({
    queryKey: ['assets', { limit: 1 }],
    queryFn: () => assetApi.getAssets({ limit: 1 }),
  });

  const recentAssets = assetsData?.items.slice(0, 5) || [];

  // Mock data for dashboard
  const stats = {
    totalAssets: assetsData?.total || 0,
    onlineAssets: 42,
    alerts: 3,
    pendingTasks: 5,
    certificatesExpiring: 2,
    deploymentsToday: 1,
  };

  const assetColumns = [
    {
      title: '资产编号',
      dataIndex: 'assetId',
      key: 'assetId',
      width: 120,
    },
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
    },
    {
      title: '类型',
      dataIndex: 'assetType',
      key: 'assetType',
      width: 100,
      render: (type: string) => (
        <Tag color="blue" style={{ borderRadius: '4px' }}>
          {type.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const colorMap: Record<string, string> = {
          active: 'success',
          offline: 'error',
          maintenance: 'warning',
          retired: 'default',
        };
        const labelMap: Record<string, string> = {
          active: '运行中',
          offline: '离线',
          maintenance: '维护中',
          retired: '已退役',
        };
        return (
          <Badge
            status={colorMap[status] as any}
            text={labelMap[status] || status}
          />
        );
      },
    },
    {
      title: 'IP地址',
      dataIndex: 'ipAddress',
      key: 'ipAddress',
      width: 140,
      render: (ip: string) => ip || '-',
    },
  ];

  const recentAlerts = [
    { id: 1, title: '服务器 CPU 使用率过高', severity: 'critical', time: '5分钟前' },
    { id: 2, title: '数据库连接数接近上限', severity: 'warning', time: '15分钟前' },
    { id: 3, title: 'SSL 证书即将过期', severity: 'warning', time: '1小时前' },
  ];

  const quickActions = [
    { title: '添加资产', icon: <DatabaseOutlined />, color: '#1890ff' },
    { title: '创建监控', icon: <AlertOutlined />, color: '#52c41a' },
    { title: '发布应用', icon: <DeploymentUnitOutlined />, color: '#722ed1' },
    { title: '查看证书', icon: <SafetyCertificateOutlined />, color: '#fa8c16' },
  ];

  return (
    <div className="animate-fade-in">
      <h1 style={{ marginBottom: 24, fontSize: 24, fontWeight: 600 }}>仪表盘</h1>

      {/* Stats Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card className="hover-lift" style={{ borderRadius: 'var(--radius-md)' }}>
            <Statistic
              title="总资产"
              value={stats.totalAssets}
              prefix={<DatabaseOutlined style={{ color: '#1890ff' }} />}
              valueStyle={{ color: '#1890ff', fontSize: 32, fontWeight: 600 }}
            />
            <div style={{ marginTop: 8, fontSize: 12, color: '#8c8c8c' }}>
              <RiseOutlined style={{ color: '#52c41a' }} /> 较上周增长 12%
            </div>
          </Card>
        </Col>
        <Col span={6}>
          <Card className="hover-lift" style={{ borderRadius: 'var(--radius-md)' }}>
            <Statistic
              title="在线资产"
              value={stats.onlineAssets}
              prefix={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
              valueStyle={{ color: '#52c41a', fontSize: 32, fontWeight: 600 }}
            />
            <div style={{ marginTop: 8, fontSize: 12, color: '#8c8c8c' }}>
              <Progress percent={85} size="small" showInfo={false} style={{ margin: 0 }} />
            </div>
          </Card>
        </Col>
        <Col span={6}>
          <Card className="hover-lift" style={{ borderRadius: 'var(--radius-md)' }}>
            <Statistic
              title="告警事件"
              value={stats.alerts}
              prefix={<AlertOutlined style={{ color: '#f5222d' }} />}
              valueStyle={{ color: '#f5222d', fontSize: 32, fontWeight: 600 }}
            />
            <div style={{ marginTop: 8, fontSize: 12, color: '#8c8c8c' }}>
              <FallOutlined style={{ color: '#52c41a' }} /> 较昨日减少 2 个
            </div>
          </Card>
        </Col>
        <Col span={6}>
          <Card className="hover-lift" style={{ borderRadius: 'var(--radius-md)' }}>
            <Statistic
              title="待处理"
              value={stats.pendingTasks}
              prefix={<ExclamationCircleOutlined style={{ color: '#faad14' }} />}
              valueStyle={{ color: '#faad14', fontSize: 32, fontWeight: 600 }}
            />
            <div style={{ marginTop: 8, fontSize: 12, color: '#8c8c8c' }}>
              <ClockCircleOutlined /> 包含证书续期等任务
            </div>
          </Card>
        </Col>
      </Row>

      {/* Middle Section */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={16}>
          <Card
            title="最近添加的资产"
            style={{ borderRadius: 'var(--radius-md)' }}
            bodyStyle={{ padding: 0 }}
          >
            <Table
              columns={assetColumns}
              dataSource={recentAssets}
              rowKey="id"
              pagination={false}
              size="small"
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card
            title="最近告警"
            style={{ borderRadius: 'var(--radius-md)', marginBottom: 16 }}
          >
            <List
              dataSource={recentAlerts}
              renderItem={(item) => (
                <List.Item style={{ padding: '12px 0' }}>
                  <List.Item.Meta
                    avatar={
                      <Avatar
                        size="small"
                        style={{
                          backgroundColor:
                            item.severity === 'critical' ? '#f5222d' : '#faad14',
                        }}
                      >
                        <AlertOutlined style={{ fontSize: 12 }} />
                      </Avatar>
                    }
                    title={<span style={{ fontSize: 14 }}>{item.title}</span>}
                    description={<span style={{ fontSize: 12 }}>{item.time}</span>}
                  />
                </List.Item>
              )}
            />
          </Card>
          <Card title="快捷操作" style={{ borderRadius: 'var(--radius-md)' }}>
            <Row gutter={[8, 8]}>
              {quickActions.map((action, index) => (
                <Col span={12} key={index}>
                  <Card
                    hoverable
                    style={{
                      textAlign: 'center',
                      borderRadius: 'var(--radius-sm)',
                      cursor: 'pointer',
                    }}
                    bodyStyle={{ padding: '16px 8px' }}
                  >
                    <div
                      style={{
                        fontSize: 24,
                        color: action.color,
                        marginBottom: 8,
                      }}
                    >
                      {action.icon}
                    </div>
                    <div style={{ fontSize: 13 }}>{action.title}</div>
                  </Card>
                </Col>
              ))}
            </Row>
          </Card>
        </Col>
      </Row>

      {/* Bottom Section */}
      <Row gutter={[16, 16]}>
        <Col span={12}>
          <Card title="系统健康度" style={{ borderRadius: 'var(--radius-md)' }}>
            <Row gutter={16}>
              <Col span={12}>
                <Progress
                  type="dashboard"
                  percent={92}
                  strokeColor={{ '0%': '#108ee9', '100%': '#87d068' }}
                  format={(percent) => (
                    <div style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: 24, fontWeight: 600 }}>{percent}%</div>
                      <div style={{ fontSize: 12, color: '#8c8c8c' }}>整体健康</div>
                    </div>
                  )}
                />
              </Col>
              <Col span={12}>
                <div style={{ padding: '20px 0' }}>
                  <div style={{ marginBottom: 16 }}>
                    <div style={{ fontSize: 12, color: '#8c8c8c', marginBottom: 4 }}>
                      证书有效期
                    </div>
                    <Progress percent={75} size="small" status="active" />
                  </div>
                  <div style={{ marginBottom: 16 }}>
                    <div style={{ fontSize: 12, color: '#8c8c8c', marginBottom: 4 }}>
                      监控覆盖率
                    </div>
                    <Progress percent={88} size="small" status="active" />
                  </div>
                  <div>
                    <div style={{ fontSize: 12, color: '#8c8c8c', marginBottom: 4 }}>
                      备份完成率
                    </div>
                    <Progress percent={100} size="small" />
                  </div>
                </div>
              </Col>
            </Row>
          </Card>
        </Col>
        <Col span={12}>
          <Card title="今日概览" style={{ borderRadius: 'var(--radius-md)' }}>
            <Row gutter={16}>
              <Col span={8}>
                <div style={{ textAlign: 'center', padding: '20px 0' }}>
                  <DeploymentUnitOutlined
                    style={{ fontSize: 32, color: '#722ed1', marginBottom: 8 }}
                  />
                  <div style={{ fontSize: 24, fontWeight: 600 }}>
                    {stats.deploymentsToday}
                  </div>
                  <div style={{ fontSize: 12, color: '#8c8c8c' }}>今日发布</div>
                </div>
              </Col>
              <Col span={8}>
                <div style={{ textAlign: 'center', padding: '20px 0' }}>
                  <SafetyCertificateOutlined
                    style={{ fontSize: 32, color: '#fa8c16', marginBottom: 8 }}
                  />
                  <div style={{ fontSize: 24, fontWeight: 600 }}>
                    {stats.certificatesExpiring}
                  </div>
                  <div style={{ fontSize: 12, color: '#8c8c8c' }}>即将过期证书</div>
                </div>
              </Col>
              <Col span={8}>
                <div style={{ textAlign: 'center', padding: '20px 0' }}>
                  <ClockCircleOutlined
                    style={{ fontSize: 32, color: '#1890ff', marginBottom: 8 }}
                  />
                  <div style={{ fontSize: 24, fontWeight: 600 }}>99.9%</div>
                  <div style={{ fontSize: 12, color: '#8c8c8c' }}>系统可用性</div>
                </div>
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;
