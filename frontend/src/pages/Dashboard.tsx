import { Row, Col, Card, Statistic, Table, Tag, Space, Button, Tooltip, Tabs, Progress } from 'antd';
import { LinkOutlined, MonitorOutlined, CloudUploadOutlined, DatabaseOutlined, CloudOutlined, SettingOutlined, DashboardOutlined, SafetyOutlined, ApiOutlined, DesktopOutlined, CustomerServiceOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { navigationApi } from '../services/navigation';
import { dashboardApi } from '../services/dashboard';
import type { RecentAlert, RecentDeployment } from '../services/dashboard';
import { useAuthStore } from '../stores/authStore';

const iconMap: Record<string, React.ReactNode> = {
  MonitorOutlined: <MonitorOutlined />,
  CloudUploadOutlined: <CloudUploadOutlined />,
  LinkOutlined: <LinkOutlined />,
  DatabaseOutlined: <DatabaseOutlined />,
  DesktopOutlined: <DesktopOutlined />,
  CloudOutlined: <CloudOutlined />,
  SettingOutlined: <SettingOutlined />,
  DashboardOutlined: <DashboardOutlined />,
  SafetyOutlined: <SafetyOutlined />,
  ApiOutlined: <ApiOutlined />,
};

const REFRESH_INTERVAL = 60 * 1000;

const formatTime = (isoStr: string | null): string => {
  if (!isoStr) return '-';
  const d = new Date(isoStr);
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`;
};

const Dashboard = () => {
  const user = useAuthStore((state) => state.user);
  const isViewer = user?.roles?.some(role => role.name === 'viewer') ?? false;

  const { data: terminalMetrics, isLoading: terminalLoading } = useQuery({
    queryKey: ['my-terminal-metrics'],
    queryFn: () => dashboardApi.getMyTerminalMetrics(),
    enabled: isViewer,
  });

  const { data: navigationGroups } = useQuery({
    queryKey: ['navigation-links'],
    queryFn: () => navigationApi.getPublicLinks(),
    staleTime: 5 * 60 * 1000,
  });

  const { data: overview, isLoading: overviewLoading } = useQuery({
    queryKey: ['dashboard-overview'],
    queryFn: () => dashboardApi.getOverview(),
    enabled: !isViewer,
    refetchInterval: REFRESH_INTERVAL,
  });

  const alertStats = overview?.alert_stats;
  const itFeedbackStats = overview?.it_feedback_stats;
  const assetStats = overview?.asset_stats;
  const certStats = overview?.cert_stats;
  const recentAlerts = alertStats?.recent_alerts || [];
  const recentDeployments = overview?.recent_deployments || [];

  return (
    <div>
      {navigationGroups && navigationGroups.groups.length > 0 && (
        <Card
          size="small"
          style={{ marginBottom: 16, background: 'var(--bg-elevated)' }}
          styles={{ body: { padding: '0 16px 12px' } }}
        >
          <Tabs
            defaultActiveKey={navigationGroups.groups[0]?.category}
            items={navigationGroups.groups.map((group) => ({
              key: group.category,
              label: group.category,
              children: (
                <Space size={8} wrap>
                  {group.links.map((link) => (
                    <Tooltip key={link.id} title={link.description || link.url} placement="top">
                      <Button
                        type="primary"
                        size="small"
                        icon={link.icon ? iconMap[link.icon] : <LinkOutlined />}
                        onClick={() => window.open(link.url, '_blank')}
                      >
                        {link.name}
                        <LinkOutlined style={{ marginLeft: 4, fontSize: 12 }} />
                      </Button>
                    </Tooltip>
                  ))}
                </Space>
              ),
            }))}
            size="small"
            tabBarStyle={{ marginBottom: 12 }}
          />
        </Card>
      )}

      <Row gutter={[16, 16]}>
        {!isViewer && (
          <>
            <Col xs={24} sm={12} lg={6}>
              <Card loading={overviewLoading}>
                <Statistic
                  title="活跃告警"
                  value={alertStats?.firing_count || 0}
                  suffix="个"
                  style={{ color: (alertStats?.firing_count ?? 0) > 0 ? '#ff4d4f' : '#52c41a' }}
                />
                <div style={{ marginTop: 8 }}>
                  <Tag color="orange">待处理: {alertStats?.firing_count || 0}</Tag>
                  <Tag color="green">已解决: {alertStats?.resolved_count || 0}</Tag>
                </div>
              </Card>
            </Col>

            <Col xs={24} sm={12} lg={6}>
              <Card loading={overviewLoading}>
                <Statistic
                  title="IT反馈"
                  value={itFeedbackStats?.pending_count || 0}
                  suffix="个待处理"
                  valueStyle={{ color: (itFeedbackStats?.pending_count ?? 0) > 0 ? '#faad14' : '#52c41a' }}
                  prefix={<CustomerServiceOutlined />}
                />
                <div style={{ marginTop: 8 }}>
                  <Tag color="orange">待处理: {itFeedbackStats?.pending_count || 0}</Tag>
                  <Tag color="blue">处理中: {itFeedbackStats?.handling_count || 0}</Tag>
                  <Tag color="green">已解决: {itFeedbackStats?.resolved_count || 0}</Tag>
                </div>
              </Card>
            </Col>

            <Col xs={24} sm={12} lg={6}>
              <Card loading={overviewLoading}>
                <Statistic
                  title="证书总数"
                  value={certStats?.total_count || 0}
                  suffix="个"
                  style={{ color: '#722ed1' }}
                />
                <div style={{ marginTop: 8 }}>
                  <Tag color="green">有效: {certStats?.valid_count || 0}</Tag>
                  <Tag color="orange">即将过期: {certStats?.expiring_count || 0}</Tag>
                  <Tag color="red">已过期: {certStats?.expired_count || 0}</Tag>
                </div>
              </Card>
            </Col>

            <Col xs={24} sm={12} lg={6}>
              <Card loading={overviewLoading}>
                <Statistic
                  title="资产总数"
                  value={assetStats?.total_count || 0}
                  suffix="个"
                  style={{ color: '#13c2c2' }}
                />
                <div style={{ marginTop: 8 }}>
                  <Tag color="blue">服务器: {assetStats?.server_count || 0}</Tag>
                  <Tag color="purple">域名: {assetStats?.domain_count || 0}</Tag>
                  <Tag color="cyan">终端: {assetStats?.terminal_count || 0}</Tag>
                </div>
              </Card>
            </Col>
          </>
        )}
      </Row>

      {isViewer && terminalMetrics && (
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={12}>
            <Card loading={overviewLoading}>
              <Statistic
                title="我的资产"
                value={assetStats?.total_count || 0}
                suffix="个"
                style={{ color: '#13c2c2' }}
              />
              <div style={{ marginTop: 8 }}>
                <Tag color="blue">服务器: {assetStats?.server_count || 0}</Tag>
                <Tag color="purple">域名: {assetStats?.domain_count || 0}</Tag>
              </div>
            </Card>
          </Col>

          <Col xs={12}>
            <Card loading={terminalLoading}>
              <Statistic
                title="终端总数"
                value={terminalMetrics.summary.totalCount}
                suffix="个"
                style={{ color: '#1890ff' }}
              />
              <div style={{ marginTop: 8 }}>
                <Tag color="green">在线: {terminalMetrics.summary.onlineCount}</Tag>
                <Tag color="red">离线: {terminalMetrics.summary.offlineCount}</Tag>
              </div>
            </Card>
          </Col>
        </Row>
      )}

      {isViewer && terminalMetrics && (
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24}>
            <Card
              title="终端详情"
              loading={terminalLoading}
              styles={{ body: { padding: terminalLoading ? 24 : 12 } }}
            >
                <Row gutter={[12, 12]}>
                  {(terminalMetrics.terminals || []).map((terminal) => {
                    const statusColor: Record<string, string> = {
                      online: '#52c41a',
                      offline: '#ff4d4f',
                      unknown: '#d9d9d9',
                    };
                    const statusLabel: Record<string, string> = {
                      online: '在线',
                      offline: '离线',
                      unknown: '未知',
                    };
                    return (
                      <Col xs={24} sm={12} lg={8} key={terminal.id}>
                        <Card
                          size="small"
                          style={{
                            borderTop: `3px solid ${statusColor[terminal.currentStatus] || '#d9d9d9'}`,
                            background: 'var(--bg-tertiary)',
                          }}
                          styles={{ body: { padding: '12px 16px' } }}
                        >
                          <div style={{ marginBottom: 10 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                              <DesktopOutlined style={{ color: 'var(--text-secondary)' }} />
                              <Tooltip title={terminal.hostname}>
                                <div style={{ fontWeight: 600, fontSize: 14, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 180 }}>
                                  {terminal.hostname}
                                </div>
                              </Tooltip>
                              <span style={{ fontSize: 12, color: 'var(--text-secondary)', marginLeft: 4 }}>
                                {terminal.ipAddress || '-'}
                              </span>
                              <Tag
                                color={statusColor[terminal.currentStatus]}
                                style={{ marginLeft: 'auto', fontSize: 11, padding: '0 6px' }}
                              >
                                {statusLabel[terminal.currentStatus]}
                              </Tag>
                            </div>
                          </div>

                          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                            <div>
                              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
                                <span style={{ color: 'var(--text-secondary)' }}>CPU</span>
                                <span style={{ fontWeight: 500 }}>{terminal.cpuUsage !== null ? `${terminal.cpuUsage}%` : '-'}</span>
                              </div>
                              <Progress
                                percent={terminal.cpuUsage ?? 0}
                                showInfo={false}
                                strokeColor={terminal.cpuUsage !== null ? (terminal.cpuUsage > 80 ? '#ff4d4f' : terminal.cpuUsage > 60 ? '#faad14' : '#1890ff') : '#d9d9d9'}
                                trailColor="var(--border-color)"
                                size={['100%', 6]}
                              />
                            </div>
                            <div>
                              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
                                <span style={{ color: 'var(--text-secondary)' }}>内存</span>
                                <span style={{ fontWeight: 500 }}>
                                  {terminal.memoryUsage !== null && terminal.memoryTotalGb !== null
                                    ? `${((terminal.memoryUsage / 100) * terminal.memoryTotalGb).toFixed(1)} / ${terminal.memoryTotalGb} GB`
                                    : terminal.memoryUsage !== null ? `${terminal.memoryUsage}%` : '-'}
                                </span>
                              </div>
                              <Progress
                                percent={terminal.memoryUsage ?? 0}
                                showInfo={false}
                                strokeColor={terminal.memoryUsage !== null ? (terminal.memoryUsage > 80 ? '#ff4d4f' : terminal.memoryUsage > 60 ? '#faad14' : '#722ed1') : '#d9d9d9'}
                                trailColor="var(--border-color)"
                                size={['100%', 6]}
                              />
                            </div>
                            <div>
                              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
                                <span style={{ color: 'var(--text-secondary)' }}>磁盘</span>
                                <span style={{ fontWeight: 500 }}>
                                  {terminal.diskUsage !== null && terminal.diskTotalGb !== null
                                    ? `${((terminal.diskUsage / 100) * terminal.diskTotalGb).toFixed(1)} / ${terminal.diskTotalGb} GB`
                                    : terminal.diskUsage !== null ? `${terminal.diskUsage}%` : '-'}
                                </span>
                              </div>
                              <Progress
                                percent={terminal.diskUsage ?? 0}
                                showInfo={false}
                                strokeColor={terminal.diskUsage !== null ? (terminal.diskUsage > 80 ? '#ff4d4f' : terminal.diskUsage > 60 ? '#faad14' : '#fa8c16') : '#d9d9d9'}
                                trailColor="var(--border-color)"
                                size={['100%', 6]}
                              />
                            </div>
                          </div>

                          {terminal.alertCount > 0 && (
                            <div style={{ marginTop: 10, paddingTop: 8, borderTop: '1px solid var(--border-color)' }}>
                              <Tag color="red" style={{ fontSize: 11 }}>
                                告警 {terminal.alertCount} 个{terminal.alertSeverity ? ` · ${terminal.alertSeverity}` : ''}
                              </Tag>
                            </div>
                          )}
                        </Card>
                      </Col>
                    );
                  })}
                </Row>
              </Card>
            </Col>
          </Row>
      )}

      {!isViewer && (
        <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
          <Col xs={24} lg={12}>
            <Card title="最近告警" extra={<a href="/alerts/alertmanager">查看全部</a>}>
              <Table
                dataSource={recentAlerts}
                rowKey={(r: RecentAlert) => `${r.alertname}-${r.starts_at}`}
                loading={overviewLoading}
                pagination={false}
                size="small"
                columns={[
                  {
                    title: '名称',
                    dataIndex: 'alertname',
                    key: 'alertname',
                    ellipsis: true,
                  },
                  {
                    title: '实例',
                    dataIndex: 'instance',
                    key: 'instance',
                    width: 140,
                    ellipsis: true,
                    render: (v: string | null) => v || '-',
                  },
                  {
                    title: '严重程度',
                    dataIndex: 'severity',
                    key: 'severity',
                    width: 80,
                    render: (severity: string) => {
                      const colorMap: Record<string, string> = {
                        critical: 'red',
                        warning: 'orange',
                        info: 'blue',
                      };
                      return <Tag color={colorMap[severity] || 'default'}>{severity?.toUpperCase()}</Tag>;
                    },
                  },
                  {
                    title: '状态',
                    dataIndex: 'status',
                    key: 'status',
                    width: 80,
                    render: (status: string) => {
                      const colorMap: Record<string, string> = {
                        firing: 'red',
                        resolved: 'green',
                        acknowledged: 'blue',
                      };
                      return <Tag color={colorMap[status] || 'default'}>{status?.toUpperCase()}</Tag>;
                    },
                  },
                  {
                    title: '时间',
                    dataIndex: 'starts_at',
                    key: 'starts_at',
                    width: 100,
                    render: (v: string | null) => formatTime(v),
                  },
                ]}
              />
            </Card>
          </Col>

          <Col xs={24} lg={12}>
            <Card title="最近发布" extra={<a href="/ops/deployments">查看全部</a>}>
              <Table
                dataSource={recentDeployments}
                rowKey={(r: RecentDeployment) => `${r.project_name}-${r.created_at}`}
                loading={overviewLoading}
                pagination={false}
                size="small"
                columns={[
                  {
                    title: '项目',
                    dataIndex: 'project_name',
                    key: 'project_name',
                    ellipsis: true,
                  },
                  {
                    title: '环境',
                    dataIndex: 'environment',
                    key: 'environment',
                    width: 80,
                    render: (env: string) => {
                      const colorMap: Record<string, string> = {
                        dev: 'blue',
                        test: 'cyan',
                        staging: 'orange',
                        prod: 'red',
                      };
                      return <Tag color={colorMap[env] || 'default'}>{env?.toUpperCase()}</Tag>;
                    },
                  },
                  {
                    title: '状态',
                    dataIndex: 'status',
                    key: 'status',
                    width: 80,
                    render: (status: string) => {
                      const colorMap: Record<string, string> = {
                        pending: 'default',
                        running: 'processing',
                        success: 'success',
                        failed: 'error',
                      };
                      return <Tag color={colorMap[status] || 'default'}>{status?.toUpperCase()}</Tag>;
                    },
                  },
                  {
                    title: '时间',
                    dataIndex: 'created_at',
                    key: 'created_at',
                    width: 100,
                    render: (v: string | null) => formatTime(v),
                  },
                ]}
              />
            </Card>
          </Col>
        </Row>
      )}
    </div>
  );
};

export default Dashboard;
