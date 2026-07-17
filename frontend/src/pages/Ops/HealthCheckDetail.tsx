import { useState, useMemo, useCallback } from 'react';
import {
  Button, Space, App, Dropdown, Tabs, Tag, Progress, Row, Col, Spin, Segmented,
} from 'antd';
import {
  ArrowLeftOutlined, ExportOutlined,
  CheckCircleOutlined, WarningOutlined, CloseCircleOutlined,
  DesktopOutlined, CloudServerOutlined,
  ArrowUpOutlined, ArrowDownOutlined, MinusOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import dayjs from 'dayjs';
import { useParams, useNavigate } from 'react-router-dom';
import { useThemeStore } from '../../stores/themeStore';
import { healthCheckApi } from '../../services/healthCheck';
import type { HealthCheckDetail, HealthCheckThresholds } from '../../types/healthCheck';

const darkColors = {
  bgPrimary: '#0a0e1a',
  bgSecondary: '#111827',
  bgCard: 'rgba(17, 24, 39, 0.85)',
  bgCardHover: 'rgba(22, 33, 62, 0.95)',
  borderGlow: 'rgba(0, 212, 255, 0.25)',
  borderGlowHover: 'rgba(0, 212, 255, 0.5)',
  accentCyan: '#00d4ff',
  accentGreen: '#00ff88',
  accentOrange: '#ff9f1c',
  accentRed: '#ff3b5c',
  textPrimary: 'rgba(255, 255, 255, 0.92)',
  textSecondary: 'rgba(255, 255, 255, 0.6)',
  textMuted: 'rgba(255, 255, 255, 0.35)',
  shadowGlow: '0 0 15px rgba(0, 212, 255, 0.08)',
  shadowGlowHover: '0 0 25px rgba(0, 212, 255, 0.15)',
};

const lightColors = {
  bgPrimary: '#f0f2f5',
  bgSecondary: '#ffffff',
  bgCard: '#ffffff',
  bgCardHover: '#fafafa',
  borderGlow: 'rgba(0, 0, 0, 0.06)',
  borderGlowHover: 'rgba(24, 144, 255, 0.3)',
  accentCyan: '#1890ff',
  accentGreen: '#52c41a',
  accentOrange: '#fa8c16',
  accentRed: '#ff4d4f',
  textPrimary: 'rgba(0, 0, 0, 0.88)',
  textSecondary: 'rgba(0, 0, 0, 0.65)',
  textMuted: 'rgba(0, 0, 0, 0.25)',
  shadowGlow: '0 1px 4px rgba(0, 0, 0, 0.06)',
  shadowGlowHover: '0 4px 12px rgba(0, 0, 0, 0.1)',
};

const getProgressColor = (value: number | null, thresholds: HealthCheckThresholds | undefined, type: 'cpu' | 'memory' | 'disk', dark: boolean) => {
  if (value === null) return dark ? '#303030' : '#f0f0f0';
  const crit = type === 'cpu' ? thresholds?.cpuLoadPerCoreCritical ?? 95
    : type === 'memory' ? thresholds?.memoryUsageCritical ?? 95
    : thresholds?.diskUsageCritical ?? 95;
  const warn = type === 'cpu' ? thresholds?.cpuLoadPerCoreWarning ?? 80
    : type === 'memory' ? thresholds?.memoryUsageWarning ?? 80
    : thresholds?.diskUsageWarning ?? 80;
  if (value >= crit) return dark ? '#ff3b5c' : '#ff4d4f';
  if (value >= warn) return dark ? '#ff9f1c' : '#fa8c16';
  return dark ? '#00ff88' : '#52c41a';
};

const RingChart = ({ value, total, color, dark }: { value: number; total: number; color: string; dark: boolean }) => {
  const pct = total > 0 ? (value / total) * 100 : 0;
  const size = 48;
  const strokeWidth = 5;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (pct / 100) * circumference;
  const bgColor = dark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)';

  return (
    <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
      <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke={bgColor} strokeWidth={strokeWidth} />
      <circle
        cx={size / 2} cy={size / 2} r={radius} fill="none"
        stroke={color} strokeWidth={strokeWidth}
        strokeDasharray={circumference} strokeDashoffset={offset}
        strokeLinecap="round"
        style={{ transition: 'stroke-dashoffset 0.6s ease' }}
      />
    </svg>
  );
};

const HostCard = ({ detail, thresholds, dark }: { detail: HealthCheckDetail; thresholds?: HealthCheckThresholds; dark: boolean }) => {
  const c = dark ? darkColors : lightColors;
  const statusColor = detail.hostStatus === 'critical' ? c.accentRed : detail.hostStatus === 'warning' ? c.accentOrange : c.accentGreen;
  const statusLabel = detail.hostStatus === 'critical' ? '严重' : detail.hostStatus === 'warning' ? '警告' : '正常';
  const isServer = detail.assetType?.toLowerCase().includes('server') || detail.assetType?.toLowerCase().includes('服务器');
  const isTerminal = detail.assetType?.toLowerCase().includes('terminal') || detail.assetType?.toLowerCase().includes('终端');
  const isWindows = detail.osInfo?.toLowerCase().includes('windows') ?? false;

  const cardStyle: React.CSSProperties = dark ? {
    background: c.bgCard,
    border: `1px solid ${statusColor}33`,
    borderRadius: 10,
    padding: '16px 18px',
    boxShadow: `0 0 12px ${statusColor}15, ${c.shadowGlow}`,
    transition: 'all 0.3s ease',
    position: 'relative',
    overflow: 'hidden',
  } : {
    background: c.bgCard,
    border: `1px solid ${c.borderGlow}`,
    borderLeft: `3px solid ${statusColor}`,
    borderRadius: 8,
    padding: '16px 18px',
    boxShadow: c.shadowGlow,
    transition: 'all 0.3s ease',
  };

  const glowOverlay: React.CSSProperties = dark ? {
    position: 'absolute',
    top: 0, left: 0, right: 0,
    height: 2,
    background: `linear-gradient(90deg, transparent, ${statusColor}66, transparent)`,
  } : {};

  const failedChecks = useMemo(() => {
    if (!detail.checkDetails || typeof detail.checkDetails !== 'object') return [];
    const failed: { name: string; value: unknown }[] = [];
    for (const [key, val] of Object.entries(detail.checkDetails)) {
      if (val && typeof val === 'object') {
        const obj = val as Record<string, unknown>;
        if (obj.status === 'warning' || obj.status === 'critical') {
          failed.push({ name: key, value: obj.value ?? obj.message ?? obj });
        }
      }
    }
    return failed;
  }, [detail.checkDetails]);

  return (
    <div style={cardStyle} className="host-card-hover">
      {dark && <div style={glowOverlay} />}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 15, fontWeight: 600, color: c.textPrimary, fontFamily: 'monospace' }}>
            {detail.instance}
          </span>
          <Tag color={isServer ? 'blue' : isTerminal ? 'purple' : 'default'} style={{ margin: 0, fontSize: 11 }}>
            {detail.assetType}
          </Tag>
          {isWindows && (
            <Tag color="cyan" style={{ margin: 0, fontSize: 11, fontWeight: 600 }}>
              Windows
            </Tag>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
          <span style={{
            width: 8, height: 8, borderRadius: '50%',
            background: statusColor,
            boxShadow: dark ? `0 0 6px ${statusColor}` : 'none',
          }} />
          <span style={{ fontSize: 12, color: statusColor, fontWeight: 500 }}>{statusLabel}</span>
        </div>
      </div>

      {detail.env && (
        <div style={{ fontSize: 12, color: c.textSecondary, marginBottom: 10 }}>
          {detail.env}{detail.kernelVersion ? ` | ${detail.kernelVersion}` : ''}
        </div>
      )}
      {!detail.env && detail.osInfo && (
        <div style={{ fontSize: 12, color: c.textSecondary, marginBottom: 10 }}>
          {detail.osInfo}{detail.kernelVersion ? ` | ${detail.kernelVersion}` : ''}
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {[
          { label: 'CPU', value: detail.cpuUsage, type: 'cpu' as const },
          { label: 'MEM', value: detail.memoryUsage, type: 'memory' as const },
          { label: 'DISK', value: detail.diskUsage, type: 'disk' as const },
        ].map((item) => (
          <div key={item.label} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 11, color: c.textSecondary, width: 32, fontFamily: 'monospace' }}>{item.label}</span>
            <Progress
              percent={item.value ?? 0}
              size="small"
              strokeColor={getProgressColor(item.value, thresholds, item.type, dark)}
              trailColor={dark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)'}
              showInfo={false}
              style={{ flex: 1, margin: 0 }}
            />
            <span style={{
              fontSize: 12, fontFamily: 'monospace', fontWeight: 600,
              color: getProgressColor(item.value, thresholds, item.type, dark),
              width: 38, textAlign: 'right',
            }}>
              {item.value !== null ? `${item.value}%` : '-'}
            </span>
          </div>
        ))}
      </div>

      {isServer && (detail.load1 !== null || detail.cpuCount !== null) && (
        <div style={{ marginTop: 8, fontSize: 11, color: c.textSecondary, display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          {detail.load1 !== null ? (
            <>
              <span>
                负载{' '}
                <span style={{ color: c.textPrimary, fontFamily: 'monospace' }}>{detail.load1.toFixed(2)}</span>
                <span style={{ color: c.textMuted }}> / </span>
                <span style={{ color: c.textPrimary, fontFamily: 'monospace' }}>
                  {detail.load5 !== null ? detail.load5.toFixed(2) : '-'}
                </span>
                <span style={{ color: c.textMuted }}> / </span>
                <span style={{ color: c.textPrimary, fontFamily: 'monospace' }}>
                  {detail.load15 !== null ? detail.load15.toFixed(2) : '-'}
                </span>
              </span>
              {detail.cpuCount !== null && (
                <span>
                  CPU <span style={{ color: c.textPrimary, fontFamily: 'monospace' }}>{detail.cpuCount}</span>
                  <span style={{ color: c.textMuted }}> cores</span>
                </span>
              )}
            </>
          ) : (
            <span>
              CPU <span style={{ color: c.textPrimary, fontFamily: 'monospace' }}>{detail.cpuCount}</span>
              <span style={{ color: c.textMuted }}> cores</span>
              {detail.cpuUsage !== null && (
                <span style={{ color: c.textMuted }}> | {detail.cpuUsage}%</span>
              )}
            </span>
          )}
        </div>
      )}

      {isTerminal && detail.instance && (
        <div style={{ marginTop: 4, fontSize: 11, color: c.textMuted }}>
          {detail.osInfo && <span>终端: {detail.instance}</span>}
        </div>
      )}

      {detail.memoryUsedMb !== null && detail.memoryTotalMb !== null && (
        <div style={{ marginTop: 4, fontSize: 11, color: c.textMuted }}>
          MEM: {detail.memoryUsedMb}MB / {detail.memoryTotalMb}MB
          {detail.diskTotalGb !== null && ` | DISK: ${detail.diskTotalGb}GB`}
        </div>
      )}

      {!detail.isOnline && (
        <div style={{
          marginTop: 8, fontSize: 11, color: c.accentRed,
          display: 'flex', alignItems: 'center', gap: 4,
        }}>
          <CloseCircleOutlined style={{ fontSize: 12 }} />
          <span>离线</span>
        </div>
      )}

      {failedChecks.length > 0 && (
        <div style={{ marginTop: 8, borderTop: dark ? `1px solid rgba(255,255,255,0.06)` : '1px solid #f0f0f0', paddingTop: 8 }}>
          <div style={{ fontSize: 11, color: c.accentOrange, marginBottom: 4, fontWeight: 500 }}>
            检查异常项:
          </div>
          {failedChecks.map((check) => (
            <div key={check.name} style={{ fontSize: 11, color: c.textSecondary, display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ fontFamily: 'monospace' }}>{check.name}</span>
              <span style={{ color: c.accentOrange, fontFamily: 'monospace' }}>{String(check.value)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

const HealthCheckDetailPage = () => {
  const { message } = App.useApp();
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { mode } = useThemeStore();
  const dark = mode === 'dark';
  const c = dark ? darkColors : lightColors;
  const reportId = Number(id);

  const [activeTab, setActiveTab] = useState('server');
  const [serverFilter, setServerFilter] = useState<'all' | 'linux' | 'windows'>('all');

  const { data: report, isLoading } = useQuery({
    queryKey: ['healthCheckReport', reportId],
    queryFn: () => healthCheckApi.getReportById(reportId),
    enabled: !isNaN(reportId),
  });

  const { data: thresholds } = useQuery({
    queryKey: ['healthCheckThresholds'],
    queryFn: healthCheckApi.getThresholds,
  });

  const { data: prevHistoryData } = useQuery({
    queryKey: ['healthCheckPrevReport', reportId],
    queryFn: async () => {
      const result = await healthCheckApi.getReportHistory({ days: 1, page: 1, pageSize: 2 });
      if (!result.items || result.items.length < 2) return null;
      const sorted = [...result.items].sort((a, b) => {
        const ta = a.reportTime ? new Date(a.reportTime).getTime() : 0;
        const tb = b.reportTime ? new Date(b.reportTime).getTime() : 0;
        return tb - ta;
      });
      const prevReport = sorted.find((r) => r.id !== reportId);
      if (!prevReport) return null;
      return prevReport;
    },
    enabled: !isNaN(reportId),
  });

  const handleExportHtml = useCallback(async () => {
    try {
      const html = await healthCheckApi.exportHtmlReport(reportId);
      const blob = new Blob([html], { type: 'text/html' });
      const url = URL.createObjectURL(blob);
      window.open(url, '_blank');
    } catch {
      message.error('导出HTML失败');
    }
  }, [reportId, message]);

  const handleExportExcel = useCallback(async () => {
    try {
      const blob = await healthCheckApi.exportExcelReport(reportId);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `health-check-report-${reportId}.xlsx`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch {
      message.error('导出Excel失败');
    }
  }, [reportId, message]);

  const filteredDetails = useMemo(() => {
    const details = report?.details || [];
    switch (activeTab) {
      case 'abnormal':
        return details.filter((d) => d.hostStatus === 'warning' || d.hostStatus === 'critical');
      case 'server': {
        const servers = details.filter(
          (d) => d.assetType?.toLowerCase().includes('server') || d.assetType?.toLowerCase().includes('服务器')
        );
        if (serverFilter === 'windows') {
          return servers.filter((d) => (d.osInfo?.toLowerCase().includes('windows') ?? false));
        }
        if (serverFilter === 'linux') {
          return servers.filter((d) => !(d.osInfo?.toLowerCase().includes('windows') ?? false));
        }
        return servers;
      }
      case 'terminal':
        return details.filter((d) => d.assetType?.toLowerCase().includes('terminal') || d.assetType?.toLowerCase().includes('终端'));
      default:
        return details;
    }
  }, [report, activeTab, serverFilter]);

  const overviewCards = report ? [
    { label: '正常', value: report.okCount, icon: <CheckCircleOutlined />, color: c.accentGreen },
    { label: '警告', value: report.warningCount, icon: <WarningOutlined />, color: c.accentOrange },
    { label: '严重', value: report.criticalCount, icon: <CloseCircleOutlined />, color: c.accentRed },
    { label: '总计', value: report.totalHosts, icon: <DesktopOutlined />, color: c.accentCyan },
  ] : [];

  const comparisonData = useMemo(() => {
    if (!prevHistoryData || !report) return null;
    const warnDiff = report.warningCount - prevHistoryData.warningCount;
    const critDiff = report.criticalCount - prevHistoryData.criticalCount;
    return { warnDiff, critDiff };
  }, [prevHistoryData, report]);

  const pageStyle: React.CSSProperties = {
    padding: 20,
    minHeight: '100%',
    background: dark
      ? 'linear-gradient(180deg, #0a0e1a 0%, #111827 100%)'
      : '#f0f2f5',
  };

  const headerStyle: React.CSSProperties = dark ? {
    background: 'rgba(17, 24, 39, 0.7)',
    backdropFilter: 'blur(12px)',
    border: `1px solid ${c.borderGlow}`,
    borderRadius: 12,
    padding: '16px 24px',
    marginBottom: 20,
    boxShadow: c.shadowGlow,
  } : {
    background: c.bgCard,
    border: `1px solid ${c.borderGlow}`,
    borderRadius: 10,
    padding: '16px 24px',
    marginBottom: 20,
    boxShadow: c.shadowGlow,
  };

  const sectionStyle: React.CSSProperties = dark ? {
    background: 'rgba(17, 24, 39, 0.6)',
    backdropFilter: 'blur(8px)',
    border: `1px solid ${c.borderGlow}`,
    borderRadius: 12,
    padding: '20px 24px',
    marginBottom: 20,
    boxShadow: c.shadowGlow,
  } : {
    background: c.bgCard,
    border: `1px solid ${c.borderGlow}`,
    borderRadius: 10,
    padding: '20px 24px',
    marginBottom: 20,
    boxShadow: c.shadowGlow,
  };

  const titleStyle: React.CSSProperties = dark ? {
    fontSize: 22,
    fontWeight: 700,
    color: c.textPrimary,
    letterSpacing: 1,
    textShadow: '0 0 20px rgba(0, 212, 255, 0.3)',
  } : {
    fontSize: 22,
    fontWeight: 700,
    color: c.textPrimary,
  };

  const renderOverviewCard = (card: typeof overviewCards[0]) => {
    const total = report?.totalHosts || 1;
    const cardStyle: React.CSSProperties = dark ? {
      background: c.bgCard,
      border: `1px solid ${card.color}33`,
      borderRadius: 10,
      padding: '18px 20px',
      boxShadow: `0 0 12px ${card.color}10, ${c.shadowGlow}`,
      transition: 'all 0.3s ease',
      position: 'relative',
      overflow: 'hidden',
    } : {
      background: c.bgCard,
      borderLeft: `3px solid ${card.color}`,
      borderRadius: 8,
      padding: '18px 20px',
      boxShadow: c.shadowGlow,
      transition: 'all 0.3s ease',
    };

    const topGlow: React.CSSProperties = dark ? {
      position: 'absolute',
      top: 0, left: 0, right: 0,
      height: 2,
      background: `linear-gradient(90deg, transparent, ${card.color}88, transparent)`,
    } : {};

    return (
      <div key={card.label} style={cardStyle}>
        {dark && <div style={topGlow} />}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <div style={{ fontSize: 13, color: c.textSecondary, marginBottom: 6 }}>{card.label}</div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
              <span style={{
                fontSize: 32, fontWeight: 800, color: card.color,
                fontFamily: 'monospace',
                textShadow: dark ? `0 0 15px ${card.color}55` : 'none',
              }}>
                {card.value}
              </span>
              <span style={{ fontSize: 18, color: card.color, opacity: 0.8 }}>{card.icon}</span>
            </div>
          </div>
          <RingChart value={card.value} total={total} color={card.color} dark={dark} />
        </div>
      </div>
    );
  };

  const renderComparison = () => {
    if (!comparisonData) return null;
    const { warnDiff, critDiff } = comparisonData;

    const renderDiff = (diff: number, label: string) => {
      if (diff === 0) {
        return (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 13, color: c.textSecondary }}>
            <MinusOutlined style={{ fontSize: 10 }} />
            {label} +0
          </span>
        );
      }
      const isUp = diff > 0;
      const iconColor = isUp ? c.accentRed : c.accentGreen;
      return (
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 13, color: iconColor }}>
          {isUp ? <ArrowUpOutlined style={{ fontSize: 10 }} /> : <ArrowDownOutlined style={{ fontSize: 10 }} />}
          {label} {diff > 0 ? '+' : ''}{diff}
        </span>
      );
    };

    return (
      <div style={{
        display: 'flex', alignItems: 'center', gap: 16,
        padding: '10px 16px', borderRadius: 8,
        background: dark ? 'rgba(17, 24, 39, 0.5)' : '#fafafa',
        border: dark ? `1px solid ${c.borderGlow}` : '1px solid #f0f0f0',
        marginBottom: 20,
      }}>
        <span style={{ fontSize: 12, color: c.textSecondary, fontWeight: 500 }}>较上次:</span>
        {renderDiff(warnDiff, '警告')}
        {renderDiff(critDiff, '严重')}
      </div>
    );
  };

  if (isLoading) {
    return (
      <div style={{ ...pageStyle, display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div style={pageStyle}>
      <style>{`
        .host-card-hover:hover {
          border-color: ${dark ? darkColors.borderGlowHover : lightColors.borderGlowHover} !important;
          box-shadow: ${dark ? darkColors.shadowGlowHover : lightColors.shadowGlowHover} !important;
          transform: translateY(-1px);
        }
        .ant-tabs-tab { font-size: 13px !important; }
        ${dark ? `
        .ant-tabs-ink-bar { background: ${darkColors.accentCyan} !important; box-shadow: 0 0 8px ${darkColors.accentCyan}66; }
        .ant-tabs-tab-active .ant-tabs-tab-btn { color: ${darkColors.accentCyan} !important; text-shadow: 0 0 8px ${darkColors.accentCyan}44; }
        ` : ''}
      `}</style>

      <div style={headerStyle}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <Button
              type="text"
              icon={<ArrowLeftOutlined />}
              onClick={() => navigate('/ops/health-check')}
              style={dark ? { color: c.accentCyan } : undefined}
            />
            <CloudServerOutlined style={{ fontSize: 24, color: dark ? c.accentCyan : undefined }} />
            <span style={titleStyle}>巡检报告详情</span>
            {report?.reportTime && (
              <span style={{ fontSize: 12, color: c.textSecondary }}>
                {dayjs(report.reportTime).format('YYYY-MM-DD HH:mm')}
              </span>
            )}
          </div>
          <Space size={8} wrap>
            <Dropdown
              menu={{
                items: [
                  { key: 'html', label: '导出 HTML', icon: <ExportOutlined /> },
                  { key: 'excel', label: '导出 Excel', icon: <ExportOutlined /> },
                ],
                onClick: ({ key }) => {
                  if (key === 'html') handleExportHtml();
                  if (key === 'excel') handleExportExcel();
                },
              }}
            >
              <Button icon={<ExportOutlined />}>导出</Button>
            </Dropdown>
          </Space>
        </div>
      </div>

      <Row gutter={16} style={{ marginBottom: 20 }}>
        {overviewCards.map((card) => (
          <Col xs={12} sm={12} md={6} key={card.label}>
            {renderOverviewCard(card)}
          </Col>
        ))}
      </Row>

      {renderComparison()}

      <div style={sectionStyle}>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={[
            { key: 'abnormal', label: '异常主机' },
            { key: 'all', label: '全部' },
            { key: 'server', label: '服务器' },
            { key: 'terminal', label: '终端' },
          ]}
          style={{ marginBottom: 16 }}
        />

        {activeTab === 'server' && (
          <div style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ fontSize: 12, color: c.textSecondary }}>系统分组:</span>
            <Segmented
              value={serverFilter}
              onChange={(v) => setServerFilter(v as 'all' | 'linux' | 'windows')}
              options={[
                { label: '全部', value: 'all' },
                { label: 'Linux', value: 'linux' },
                { label: 'Windows', value: 'windows' },
              ]}
              size="small"
            />
            <span style={{ fontSize: 12, color: c.textMuted }}>
              共 {filteredDetails.length} 台
            </span>
          </div>
        )}

        <Row gutter={[16, 16]}>
          {filteredDetails.length === 0 ? (
            <Col span={24}>
              <div style={{ textAlign: 'center', padding: 40, color: c.textSecondary }}>
                <CheckCircleOutlined style={{ fontSize: 40, marginBottom: 12, color: c.accentGreen }} />
                <div>暂无异常主机</div>
              </div>
            </Col>
          ) : (
            filteredDetails.map((detail) => (
              <Col xs={24} sm={12} md={8} key={detail.id}>
                <HostCard detail={detail} thresholds={thresholds} dark={dark} />
              </Col>
            ))
          )}
        </Row>
      </div>
    </div>
  );
};

export default HealthCheckDetailPage;
