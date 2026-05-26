import { useState, useMemo, useCallback } from 'react';
import {
  Button, Space, App, Dropdown, DatePicker, Drawer, Tabs,
  Form, Slider, Tag, Table, Progress, Row, Col, Spin,
} from 'antd';
import {
  PlayCircleOutlined, ExportOutlined, SettingOutlined,
  CheckCircleOutlined, WarningOutlined, CloseCircleOutlined,
  DesktopOutlined, CloudServerOutlined, ReloadOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import type { Dayjs } from 'dayjs';
import { useThemeStore } from '../../stores/themeStore';
import { healthCheckApi } from '../../services/healthCheck';
import { PermissionGuard } from '../../components/PermissionGuard';
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

const getStatusColor = (status: string, dark: boolean) => {
  const c = dark ? darkColors : lightColors;
  if (status === 'critical') return c.accentRed;
  if (status === 'warning') return c.accentOrange;
  return c.accentGreen;
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

const SPARKLINE_VIEWBOX_WIDTH = 1000;
const SPARKLINE_PADDING = 4;

const Sparkline = ({ data, dark }: { data: number[]; dark: boolean }) => {
  if (data.length === 0) return null;
  const width = SPARKLINE_VIEWBOX_WIDTH;
  const height = 60;
  const padding = SPARKLINE_PADDING;
  const max = Math.max(...data, 1);
  const step = (width - padding * 2) / (data.length - 1 || 1);
  const points = data.map((v, i) => {
    const x = padding + i * step;
    const y = height - padding - (v / max) * (height - padding * 2);
    return `${x},${y}`;
  });
  const linePoints = points.join(' ');
  const areaPath = `M ${padding},${height - padding} ` +
    data.map((v, i) => `L ${padding + i * step},${height - padding - (v / max) * (height - padding * 2)}`).join(' ') +
    ` L ${padding + (data.length - 1) * step},${height - padding} Z`;
  const strokeColor = dark ? '#00d4ff' : '#1890ff';

  return (
    <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
      <defs>
        <linearGradient id="sparkGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={strokeColor} stopOpacity={0.3} />
          <stop offset="100%" stopColor={strokeColor} stopOpacity={0} />
        </linearGradient>
      </defs>
      <path d={areaPath} fill="url(#sparkGrad)" />
      <polyline points={linePoints} fill="none" stroke={strokeColor} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
      {data.map((v, i) => (
        <circle key={i} cx={padding + i * step} cy={height - padding - (v / max) * (height - padding * 2)} r={3} fill={strokeColor} />
      ))}
    </svg>
  );
};

const HostCard = ({ detail, thresholds, dark }: { detail: HealthCheckDetail; thresholds?: HealthCheckThresholds; dark: boolean }) => {
  const c = dark ? darkColors : lightColors;
  const statusColor = detail.hostStatus === 'critical' ? c.accentRed : detail.hostStatus === 'warning' ? c.accentOrange : c.accentGreen;
  const statusLabel = detail.hostStatus === 'critical' ? '严重' : detail.hostStatus === 'warning' ? '警告' : '正常';
  const isServer = detail.assetType?.toLowerCase().includes('server') || detail.assetType?.toLowerCase().includes('服务器');
  const isTerminal = detail.assetType?.toLowerCase().includes('terminal') || detail.assetType?.toLowerCase().includes('终端');

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

      {detail.osInfo && (
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

      {isServer && detail.load1 !== null && detail.cpuCount !== null && (
        <div style={{ marginTop: 8, fontSize: 11, color: c.textSecondary }}>
          Load: <span style={{ color: c.textPrimary, fontFamily: 'monospace' }}>{detail.load1.toFixed(2)}</span>
          <span style={{ color: c.textMuted }}> / {detail.cpuCount} cores</span>
        </div>
      )}

      {detail.memoryUsedMb !== null && detail.memoryTotalMb !== null && (
        <div style={{ marginTop: 2, fontSize: 11, color: c.textMuted }}>
          MEM: {detail.memoryUsedMb}MB / {detail.memoryTotalMb}MB
          {detail.diskTotalGb !== null && ` | DISK: ${detail.diskTotalGb}GB`}
        </div>
      )}
    </div>
  );
};

const HealthCheckList = () => {
  const { message, modal } = App.useApp();
  const queryClient = useQueryClient();
  const { mode } = useThemeStore();
  const dark = mode === 'dark';
  const c = dark ? darkColors : lightColors;

  const [selectedDate, setSelectedDate] = useState<Dayjs | null>(null);
  const [activeTab, setActiveTab] = useState('abnormal');
  const [thresholdDrawerOpen, setThresholdDrawerOpen] = useState(false);
  const [thresholdForm] = Form.useForm<HealthCheckThresholds>();

  const { data: latestReport, isLoading: latestLoading } = useQuery({
    queryKey: ['healthCheckLatest'],
    queryFn: async () => {
      const result = await healthCheckApi.getLatestReport();
      return result;
    },
  });

  const { data: historyData } = useQuery({
    queryKey: ['healthCheckHistory7d'],
    queryFn: async () => {
      const result = await healthCheckApi.getReportHistory({ days: 7, page: 1, pageSize: 7 });
      return result;
    },
  });

  const { data: selectedReport, isLoading: selectedLoading } = useQuery({
    queryKey: ['healthCheckByDate', selectedDate?.format('YYYY-MM-DD')],
    queryFn: async () => {
      if (!selectedDate) return null;
      const result = await healthCheckApi.getReportHistory({
        days: 1,
        page: 1,
        pageSize: 1,
      });
      if (result.items && result.items.length > 0) {
        const report = await healthCheckApi.getReportById(result.items[0].id);
        return report;
      }
      return null;
    },
    enabled: !!selectedDate,
  });

  const { data: thresholds, isLoading: thresholdsLoading } = useQuery({
    queryKey: ['healthCheckThresholds'],
    queryFn: healthCheckApi.getThresholds,
  });

  const currentReport = selectedReport || latestReport;
  const currentLoading = selectedDate ? selectedLoading : latestLoading;

  const trendData = useMemo(() => {
    if (!historyData?.items) return [];
    const dayMap = new Map<string, { date: string; abnormal: number; key: number | string }>();
    historyData.items.forEach((r, i) => {
      const dateKey = r.reportTime ? dayjs(r.reportTime).format('YYYY-MM-DD') : '';
      if (!dateKey) return;
      if (!dayMap.has(dateKey)) {
        dayMap.set(dateKey, {
          date: dayjs(r.reportTime).format('MM-DD'),
          abnormal: r.warningCount + r.criticalCount,
          key: r.id || i,
        });
      }
    });
    return Array.from(dayMap.values()).reverse();
  }, [historyData]);

  const filteredDetails = useMemo(() => {
    const details = currentReport?.details || [];
    switch (activeTab) {
      case 'abnormal':
        return details.filter((d) => d.hostStatus === 'warning' || d.hostStatus === 'critical');
      case 'server':
        return details.filter((d) => d.assetType?.toLowerCase().includes('server') || d.assetType?.toLowerCase().includes('服务器'));
      case 'terminal':
        return details.filter((d) => d.assetType?.toLowerCase().includes('terminal') || d.assetType?.toLowerCase().includes('终端'));
      default:
        return details;
    }
  }, [currentReport, activeTab]);

  const runMutation = useMutation({
    mutationFn: healthCheckApi.runHealthCheck,
    onSuccess: () => {
      message.success('巡检任务已触发');
      queryClient.invalidateQueries({ queryKey: ['healthCheckLatest'] });
      queryClient.invalidateQueries({ queryKey: ['healthCheckHistory7d'] });
    },
    onError: () => {
      message.error('巡检任务触发失败');
    },
  });

  const handleRunHealthCheck = () => {
    modal.confirm({
      title: '确认巡检',
      content: '确定要立即执行健康巡检吗？',
      onOk: () => {
        runMutation.mutate();
      },
    });
  };

  const handleExportHtml = useCallback(async () => {
    if (!currentReport) return;
    try {
      const html = await healthCheckApi.exportHtmlReport(currentReport.id);
      const blob = new Blob([html], { type: 'text/html' });
      const url = URL.createObjectURL(blob);
      window.open(url, '_blank');
    } catch {
      message.error('导出HTML失败');
    }
  }, [currentReport, message]);

  const handleExportExcel = useCallback(async () => {
    if (!currentReport) return;
    try {
      const blob = await healthCheckApi.exportExcelReport(currentReport.id);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `health-check-report-${currentReport.id}.xlsx`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch {
      message.error('导出Excel失败');
    }
  }, [currentReport, message]);

  const handleOpenThresholdDrawer = () => {
    if (thresholds) {
      thresholdForm.setFieldsValue(thresholds);
    }
    setThresholdDrawerOpen(true);
  };

  const handleSaveThresholds = async () => {
    try {
      const values = await thresholdForm.validateFields();
      await healthCheckApi.updateThresholds(values);
      message.success('阈值配置已更新');
      queryClient.invalidateQueries({ queryKey: ['healthCheckThresholds'] });
      setThresholdDrawerOpen(false);
    } catch {
      message.error('阈值配置更新失败');
    }
  };

  const overviewCards = currentReport ? [
    { label: '正常', value: currentReport.okCount, icon: <CheckCircleOutlined />, color: c.accentGreen },
    { label: '警告', value: currentReport.warningCount, icon: <WarningOutlined />, color: c.accentOrange },
    { label: '严重', value: currentReport.criticalCount, icon: <CloseCircleOutlined />, color: c.accentRed },
    { label: '总计', value: currentReport.totalHosts, icon: <DesktopOutlined />, color: c.accentCyan },
  ] : [];

  const tableColumns = [
    {
      title: 'IP/实例',
      dataIndex: 'instance',
      key: 'instance',
      render: (v: string) => <span style={{ fontFamily: 'monospace', fontWeight: 600, color: c.textPrimary }}>{v}</span>,
    },
    {
      title: '类型',
      dataIndex: 'assetType',
      key: 'assetType',
      render: (v: string) => <Tag>{v}</Tag>,
    },
    {
      title: '状态',
      dataIndex: 'hostStatus',
      key: 'hostStatus',
      render: (v: string) => {
        const color = getStatusColor(v, dark);
        return (
          <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: color, boxShadow: dark ? `0 0 6px ${color}` : 'none' }} />
            <span style={{ color }}>{v === 'critical' ? '严重' : v === 'warning' ? '警告' : '正常'}</span>
          </span>
        );
      },
    },
    {
      title: '系统',
      dataIndex: 'osInfo',
      key: 'osInfo',
      render: (v: string | null) => <span style={{ color: c.textSecondary, fontSize: 13 }}>{v || '-'}</span>,
    },
    {
      title: 'CPU',
      dataIndex: 'cpuUsage',
      key: 'cpuUsage',
      render: (v: number | null) => (
        <Progress
          percent={v ?? 0}
          size="small"
          strokeColor={getProgressColor(v, thresholds, 'cpu', dark)}
          trailColor={dark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)'}
        />
      ),
    },
    {
      title: '内存',
      dataIndex: 'memoryUsage',
      key: 'memoryUsage',
      render: (v: number | null) => (
        <Progress
          percent={v ?? 0}
          size="small"
          strokeColor={getProgressColor(v, thresholds, 'memory', dark)}
          trailColor={dark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)'}
        />
      ),
    },
    {
      title: '磁盘',
      dataIndex: 'diskUsage',
      key: 'diskUsage',
      render: (v: number | null) => (
        <Progress
          percent={v ?? 0}
          size="small"
          strokeColor={getProgressColor(v, thresholds, 'disk', dark)}
          trailColor={dark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)'}
        />
      ),
    },
    {
      title: '在线',
      dataIndex: 'isOnline',
      key: 'isOnline',
      render: (v: boolean) => <Tag color={v ? 'green' : 'red'}>{v ? '在线' : '离线'}</Tag>,
    },
  ];

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

  const sectionTitleStyle: React.CSSProperties = dark ? {
    fontSize: 15,
    fontWeight: 600,
    color: c.accentCyan,
    marginBottom: 16,
    letterSpacing: 0.5,
    textTransform: 'uppercase',
  } : {
    fontSize: 15,
    fontWeight: 600,
    color: c.textPrimary,
    marginBottom: 16,
  };

  const renderOverviewCard = (card: typeof overviewCards[0]) => {
    const total = currentReport?.totalHosts || 1;
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
        .ant-drawer-header { border-bottom-color: rgba(0,212,255,0.15) !important; }
        .ant-drawer-footer { border-top-color: rgba(0,212,255,0.15) !important; }
        ` : ''}
      `}</style>

      <div style={headerStyle}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <CloudServerOutlined style={{ fontSize: 24, color: dark ? c.accentCyan : undefined }} />
            <span style={titleStyle}>每日健康巡检</span>
            {currentReport?.reportTime && (
              <span style={{ fontSize: 12, color: c.textSecondary }}>
                {dayjs(currentReport.reportTime).format('YYYY-MM-DD HH:mm')}
              </span>
            )}
          </div>
          <Space size={8} wrap>
            <DatePicker
              value={selectedDate}
              onChange={(date) => setSelectedDate(date)}
              placeholder="选择日期查看历史"
              allowClear
              style={{ width: 180 }}
            />
            <Button
              icon={<ReloadOutlined />}
              onClick={() => {
                queryClient.invalidateQueries({ queryKey: ['healthCheckLatest'] });
                queryClient.invalidateQueries({ queryKey: ['healthCheckHistory7d'] });
              }}
            >
              刷新
            </Button>
            <PermissionGuard permissions="health-check:write">
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                onClick={handleRunHealthCheck}
                loading={runMutation.isPending}
                style={dark ? {
                  background: `linear-gradient(135deg, ${c.accentCyan}, #0099cc)`,
                  boxShadow: `0 0 12px ${c.accentCyan}44`,
                  border: 'none',
                } : undefined}
              >
                立即巡检
              </Button>
            </PermissionGuard>
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
            <Button
              icon={<SettingOutlined />}
              onClick={handleOpenThresholdDrawer}
              style={dark ? { borderColor: c.accentCyan + '44', color: c.accentCyan } : undefined}
            />
          </Space>
        </div>
      </div>

      {currentLoading ? (
        <div style={{ textAlign: 'center', padding: 60 }}>
          <Spin size="large" />
        </div>
      ) : (
        <>
          <Row gutter={16} style={{ marginBottom: 20 }}>
            {overviewCards.map((card) => (
              <Col xs={12} sm={12} md={6} key={card.label}>
                {renderOverviewCard(card)}
              </Col>
            ))}
          </Row>

          <div style={sectionStyle}>
            <div style={sectionTitleStyle}>
              {dark ? '// ABNORMAL TREND (7D)' : '异常趋势 (近7天)'}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 16, width: '100%' }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <Sparkline data={trendData.map((d) => d.abnormal)} dark={dark} />
                <div style={{ position: 'relative', marginTop: 4 }}>
                  {trendData.map((d, i) => {
                    const step = (SPARKLINE_VIEWBOX_WIDTH - SPARKLINE_PADDING * 2) / (trendData.length - 1 || 1);
                    const xPercent = ((SPARKLINE_PADDING + i * step) / SPARKLINE_VIEWBOX_WIDTH) * 100;
                    return (
                      <span key={d.key} style={{ position: 'absolute', left: `${xPercent}%`, transform: 'translateX(-50%)', fontSize: 10, color: c.textMuted, fontFamily: 'monospace', whiteSpace: 'nowrap' }}>
                        {d.date}
                      </span>
                    );
                  })}
                </div>
              </div>
              <div style={{ flexShrink: 0, textAlign: 'right' }}>
                <div style={{ fontSize: 28, fontWeight: 800, color: c.accentOrange, fontFamily: 'monospace' }}>
                  {trendData.reduce((s, d) => s + d.abnormal, 0)}
                </div>
                <div style={{ fontSize: 12, color: c.textSecondary }}>7天异常总计</div>
              </div>
            </div>
          </div>

          <div style={sectionStyle}>
            <Tabs
              activeKey={activeTab}
              onChange={setActiveTab}
              items={[
                { key: 'abnormal', label: '异常主机' },
                { key: 'all', label: '全部主机' },
                { key: 'server', label: '服务器' },
                { key: 'terminal', label: '终端' },
              ]}
              style={{ marginBottom: 16 }}
            />

            {activeTab === 'all' ? (
              <Table
                columns={tableColumns}
                dataSource={filteredDetails}
                rowKey="id"
                size="small"
                pagination={{ pageSize: 10, showSizeChanger: true, showTotal: (total) => `共 ${total} 条` }}
                style={dark ? { background: 'transparent' } : undefined}
              />
            ) : (
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
                    <Col xs={24} sm={12} md={8} lg={6} key={detail.id}>
                      <HostCard detail={detail} thresholds={thresholds} dark={dark} />
                    </Col>
                  ))
                )}
              </Row>
            )}
          </div>
        </>
      )}

      <Drawer
        title={dark ? '// THRESHOLD CONFIG' : '阈值配置'}
        open={thresholdDrawerOpen}
        onClose={() => setThresholdDrawerOpen(false)}
        width={420}
        extra={
          <Button type="primary" onClick={handleSaveThresholds} loading={thresholdsLoading}>
            保存
          </Button>
        }
      >
        <Form form={thresholdForm} layout="vertical">
          <div style={{ marginBottom: 24 }}>
            <div style={{
              fontSize: 14, fontWeight: 600, marginBottom: 16,
              color: dark ? c.accentCyan : c.textPrimary,
              paddingBottom: 8,
              borderBottom: dark ? `1px solid ${c.accentCyan}22` : '1px solid #f0f0f0',
            }}>
              CPU 负载 (每核)
            </div>
            <Form.Item label="警告阈值" name="cpuLoadPerCoreWarning">
              <Slider min={0} max={100} marks={{ 0: '0', 50: '50', 80: '80', 100: '100' }} />
            </Form.Item>
            <Form.Item label="严重阈值" name="cpuLoadPerCoreCritical">
              <Slider min={0} max={100} marks={{ 0: '0', 50: '50', 90: '90', 100: '100' }} />
            </Form.Item>
          </div>

          <div style={{ marginBottom: 24 }}>
            <div style={{
              fontSize: 14, fontWeight: 600, marginBottom: 16,
              color: dark ? c.accentCyan : c.textPrimary,
              paddingBottom: 8,
              borderBottom: dark ? `1px solid ${c.accentCyan}22` : '1px solid #f0f0f0',
            }}>
              内存使用率
            </div>
            <Form.Item label="警告阈值" name="memoryUsageWarning">
              <Slider min={0} max={100} marks={{ 0: '0', 50: '50', 80: '80', 100: '100' }} />
            </Form.Item>
            <Form.Item label="严重阈值" name="memoryUsageCritical">
              <Slider min={0} max={100} marks={{ 0: '0', 50: '50', 90: '90', 100: '100' }} />
            </Form.Item>
          </div>

          <div>
            <div style={{
              fontSize: 14, fontWeight: 600, marginBottom: 16,
              color: dark ? c.accentCyan : c.textPrimary,
              paddingBottom: 8,
              borderBottom: dark ? `1px solid ${c.accentCyan}22` : '1px solid #f0f0f0',
            }}>
              磁盘使用率
            </div>
            <Form.Item label="警告阈值" name="diskUsageWarning">
              <Slider min={0} max={100} marks={{ 0: '0', 50: '50', 80: '80', 100: '100' }} />
            </Form.Item>
            <Form.Item label="严重阈值" name="diskUsageCritical">
              <Slider min={0} max={100} marks={{ 0: '0', 50: '50', 90: '90', 100: '100' }} />
            </Form.Item>
          </div>
        </Form>
      </Drawer>
    </div>
  );
};

export default HealthCheckList;
