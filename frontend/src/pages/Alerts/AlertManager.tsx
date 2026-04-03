import { Row, Col, Card, Statistic, App } from 'antd';
import { Link } from 'react-router-dom';
import {
  BellOutlined,
  LockOutlined,
  FileTextOutlined,
  HistoryOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import alertApi from '../../services/alert';

interface AlertStats {
  totalReceivers: number;
  activeReceivers: number;
  totalSilences: number;
  activeSilences: number;
  totalTemplates: number;
  activeTemplates: number;
  firingAlerts: number;
  resolvedAlerts: number;
}

const AlertManager = () => {
  const { message } = App.useApp();

  const { data: stats, isLoading } = useQuery<AlertStats>({
    queryKey: ['alert-stats'],
    queryFn: async () => {
      try {
        return await alertApi.getAlertStats();
      } catch {
        message.error('获取统计信息失败');
        return {
          totalReceivers: 0,
          activeReceivers: 0,
          totalSilences: 0,
          activeSilences: 0,
          totalTemplates: 0,
          activeTemplates: 0,
          firingAlerts: 0,
          resolvedAlerts: 0,
        };
      }
    },
  });

  const menuItems = [
    {
      key: 'silences',
      title: '抑制规则',
      description: '创建和管理告警抑制规则',
      icon: <LockOutlined />,
      link: '/alerts/alertmanager/silences',
      color: '#52c41a',
    },
    {
      key: 'templates',
      title: '模板配置',
      description: '配置告警通知模板',
      icon: <FileTextOutlined />,
      link: '/alerts/alertmanager/templates',
      color: '#faad14',
    },
    {
      key: 'history',
      title: '告警历史',
      description: '查看历史告警记录',
      icon: <HistoryOutlined />,
      link: '/alerts/alertmanager/history',
      color: '#f5222d',
    },
  ];

  return (
    <div>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={8}>
          <Card loading={isLoading}>
            <Statistic
              title="活跃抑制规则"
              value={stats?.activeSilences ?? 0}
              suffix={`/ ${stats?.totalSilences ?? 0}`}
              prefix={<LockOutlined style={{ color: '#52c41a' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8}>
          <Card loading={isLoading}>
            <Statistic
              title="活跃模板"
              value={stats?.activeTemplates ?? 0}
              suffix={`/ ${stats?.totalTemplates ?? 0}`}
              prefix={<FileTextOutlined style={{ color: '#faad14' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8}>
          <Card loading={isLoading}>
            <Statistic
              title="触发中告警"
              value={stats?.firingAlerts ?? 0}
              prefix={<BellOutlined style={{ color: '#f5222d' }} />}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        {menuItems.map((item) => (
          <Col xs={24} sm={12} md={8} key={item.key}>
            <Link to={item.link}>
              <Card
                hoverable
                style={{
                  height: '100%',
                  borderTop: `3px solid ${item.color}`,
                }}
              >
                <Card.Meta
                  avatar={
                    <div
                      style={{
                        width: 48,
                        height: 48,
                        borderRadius: 8,
                        backgroundColor: `${item.color}15`,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: 24,
                        color: item.color,
                      }}
                    >
                      {item.icon}
                    </div>
                  }
                  title={
                    <span style={{ fontSize: 16, fontWeight: 600 }}>
                      {item.title}
                    </span>
                  }
                  description={
                    <span style={{ fontSize: 12, color: 'var(--text-color-secondary)' }}>
                      {item.description}
                    </span>
                  }
                />
              </Card>
            </Link>
          </Col>
        ))}
      </Row>

      <Card style={{ marginTop: 24 }}>
        <Card.Meta
          title="Webhook 配置信息"
          description={
            <div>
              <p style={{ marginBottom: 8 }}>
                <SettingOutlined style={{ marginRight: 8 }} />
                <strong>Webhook 接收地址：</strong>
              </p>
              <code
                style={{
                  display: 'block',
                  padding: '12px 16px',
                  backgroundColor: 'var(--bg-color)',
                  borderRadius: 'var(--radius-md)',
                  fontFamily: 'monospace',
                  fontSize: 14,
                }}
              >
                POST /api/v1/alert/webhook/alertmanager
              </code>
              <p
                style={{
                  marginTop: 12,
                  fontSize: 12,
                  color: 'var(--text-color-secondary)',
                }}
              >
                将此地址配置到 Alertmanager 的 webhook_configs 中，即可接收 Alertmanager
                发送的告警通知。
              </p>
            </div>
          }
        />
      </Card>
    </div>
  );
};

export default AlertManager;
