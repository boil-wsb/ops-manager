import { Row, Col, Card, Statistic, Table, Tag, Space, Button, Tooltip, Tabs, Progress } from 'antd';
import { LinkOutlined, MonitorOutlined, CloudUploadOutlined, DatabaseOutlined, CloudOutlined, SettingOutlined, DashboardOutlined, SafetyOutlined, ApiOutlined, DesktopOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { monitorApi } from '../services/monitor';
import { opsApi } from '../services/ops';
import { assetApi } from '../services/assets';
import { navigationApi } from '../services/navigation';
import { dashboardApi } from '../services/dashboard';
import alertApi from '../services/alert';
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
  const { data: alertStats, isLoading: alertLoading } = useQuery({
    queryKey: ['alert-stats'],
    queryFn: async () => {
      const firing = await alertApi.getAlertHistory({ page: 1, pageSize: 1, status: 'firing' });
      const resolved = await alertApi.getAlertHistory({ page: 1, pageSize: 1, status: 'resolved' });
      return {
        firing: firing.total || 0,
        resolved: resolved.total || 0,
      };
    },
  });

  const { data: monitorStats, isLoading: monitorLoading } = useQuery({
    queryKey: ['monitor-stats'],
    queryFn: async () => {
      const all = await monitorApi.getMonitors({ limit: 1 });
      const up = await monitorApi.getMonitors({ status: 'up', limit: 1 });
      const down = await monitorApi.getMonitors({ status: 'down', limit: 1 });
      return {
        total: all.total || 0,
        up: up.total || 0,
        down: down.total || 0,
      };
    },
  });

  const { data: certStats, isLoading: certLoading } = useQuery({
    queryKey: ['cert-stats'],
    queryFn: async () => {
      const all = await opsApi.getCertificates({ limit: 100 });
      const certArray = Array.isArray(all) ? all : [];
      const valid = certArray.filter((c) => c.status === 'active');
      const expiring = certArray.filter((c) => c.status === 'expiring');
      const expired = certArray.filter((c) => c.status === 'expired');
      return {
        total: certArray.length,
        valid: valid.length,
        expiring: expiring.length,
        expired: expired.length,
      };
    },
  });

  const { data: assetStats, isLoading: assetLoading } = useQuery({
    queryKey: ['asset-stats'],
    queryFn: async () => {
      const all = await assetApi.getAssets({ limit: 1 });
      const servers = await assetApi.getAssets({ assetType: 'SERVER', limit: 1 });
      const domains = await assetApi.getAssets({ assetType: 'DOMAIN', limit: 1 });
      return {
        total: all?.total || 0,
        servers: servers?.total || 0,
        domains: domains?.total || 0,
      };
    },
  });

  const { data: recentAlerts, isLoading: alertsLoading } = useQuery({
    queryKey: ['recent-alerts'],
    queryFn: () => alertApi.getAlertHistory({ page: 1, pageSize: 5 }),
  });

  const { data: recentDeployments, isLoading: deploymentsLoading } = useQuery({
    queryKey: ['recent-deployments'],
    queryFn: () => opsApi.getDeployments({ limit: 5 }),
  });

  return (
    <div>
      {navigationGroups && navigationGroups.groups.length > 0 && (
        <Card
          size="small"
          style={{ marginBottom: 16 }}
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
              <Card loading={monitorLoading}>
                <Statistic
                  title="监控总数"
                  value={monitorStats?.total || 0}
                  suffix="个"
                  style={{ color: '#1890ff' }}
                />
                <div style={{ marginTop: 8 }}>
                  <Tag color="green">正常: {monitorStats?.up || 0}</Tag>
                  <Tag color="red">故障: {monitorStats?.down || 0}</Tag>
                </div>
              </Card>
            </Col>

            <Col xs={24} sm={12} lg={6}>
              <Card loading={alertLoading}>
                <Statistic
                  title="活跃告警"
                  value={alertStats?.firing || 0}
                  suffix="个"
                  style={{ color: (alertStats?.firing ?? 0) > 0 ? '#ff4d4f' : '#52c41a' }}
                />
                <div style={{ marginTop: 8 }}>
                  <Tag color="orange">待处理: {alertStats?.firing || 0}</Tag>
                  <Tag color="green">已解决: {alertStats?.resolved || 0}</Tag>
                </div>
              </Card>
            </Col>

            <Col xs={24} sm={12} lg={6}>
              <Card loading={certLoading}>
                <Statistic
                  title="证书总数"
                  value={certStats?.total || 0}
                  suffix="个"
                  style={{ color: '#722ed1' }}
                />
                <div style={{ marginTop: 8 }}>
                  <Tag color="green">有效: {certStats?.valid || 0}</Tag>
                  <Tag color="orange">即将过期: {certStats?.expiring || 0}</Tag>
                  <Tag color="red">已过期: {certStats?.expired || 0}</Tag>
                </div>
              </Card>
            </Col>
          </>
        )}

        {!isViewer && (
          <Col xs={24} sm={12} lg={6}>
            <Card loading={assetLoading}>
              <Statistic
                title="资产总数"
                value={assetStats?.total || 0}
                suffix="个"
                style={{ color: '#13c2c2' }}
              />
              <div style={{ marginTop: 8 }}>
                <Tag color="blue">服务器: {assetStats?.servers || 0}</Tag>
                <Tag color="purple">域名: {assetStats?.domains || 0}</Tag>
              </div>
            </Card>
          </Col>
        )}
      </Row>

      {isViewer && terminalMetrics && (
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={12}>
            <Card loading={assetLoading}>
              <Statistic
                title="我的资产"
                value={assetStats?.total || 0}
                suffix="个"
                style={{ color: '#13c2c2' }}
              />
              <div style={{ marginTop: 8 }}>
                <Tag color="blue">服务器: {assetStats?.servers || 0}</Tag>
                <Tag color="purple">域名: {assetStats?.domains || 0}</Tag>
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
            <Card title="最近告警" extra={<a href="/monitor/alerts">查看全部</a>}>
              <Table
                dataSource={recentAlerts?.items || []}
                rowKey="id"
                loading={alertsLoading}
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
                ]}
              />
            </Card>
          </Col>

          <Col xs={24} lg={12}>
            <Card title="最近发布" extra={<a href="/ops/deployments">查看全部</a>}>
              <Table
                dataSource={recentDeployments?.items || []}
                rowKey="id"
                loading={deploymentsLoading}
                pagination={false}
                size="small"
                columns={[
                  {
                    title: '项目',
                    dataIndex: 'projectName',
                    key: 'projectName',
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
