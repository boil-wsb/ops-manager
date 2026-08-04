import { useState } from 'react';
import { Table, Button, Space, Card, DatePicker, Select, Input, Tag, Modal, Segmented } from 'antd';
import { EyeOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import type { AlertHistory as AlertHistoryType, AlertHistoryStatus } from '../../types/alert';
import { fuzzyFilterOption } from '../../utils/selectFilter';
import alertApi from '../../services/alert';
import type { Dayjs } from 'dayjs';

const { RangePicker } = DatePicker;
const { Search } = Input;

type ViewMode = 'structured' | 'json';

const statusOptions = [
  { value: 'firing', label: '触发中' },
  { value: 'resolved', label: '已解决' },
  { value: 'suppressed', label: '已抑制' },
];

const severityColorMap: Record<string, string> = {
  critical: 'red',
  high: 'volcano',
  warning: 'orange',
  middle: 'gold',
  info: 'blue',
  low: 'default',
};

const AlertHistoryPage = () => {
  const [params, setParams] = useState({
    page: 1,
    pageSize: 20,
    status: undefined as AlertHistoryStatus | undefined,
    alertname: undefined as string | undefined,
    startTime: undefined as string | undefined,
    endTime: undefined as string | undefined,
  });
  const [selectedRecord, setSelectedRecord] = useState<AlertHistoryType | null>(null);
  const [detailVisible, setDetailVisible] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>('structured');

  const { data, isLoading } = useQuery({
    queryKey: ['alertHistory', params],
    queryFn: () => alertApi.getAlertHistory({
      page: params.page,
      pageSize: params.pageSize,
      status: params.status,
      alertname: params.alertname,
      startTime: params.startTime,
      endTime: params.endTime,
    }),
  });

  const handleSearch = (value: string) => {
    setParams({ ...params, alertname: value || undefined, page: 1 });
  };

  const handleStatusChange = (value: AlertHistoryStatus | undefined) => {
    setParams({ ...params, status: value, page: 1 });
  };

  const handleTimeChange = (dates: [Dayjs | null, Dayjs | null] | null) => {
    if (dates && dates[0] && dates[1]) {
      setParams({
        ...params,
        startTime: dates[0].toISOString(),
        endTime: dates[1].toISOString(),
        page: 1,
      });
    } else {
      setParams({
        ...params,
        startTime: undefined,
        endTime: undefined,
        page: 1,
      });
    }
  };

  const handleShowDetail = (record: AlertHistoryType) => {
    setSelectedRecord(record);
    setViewMode('structured');
    setDetailVisible(true);
  };

  const renderLabelTag = (key: string, value: string) => {
    if (key === 'severity') {
      return <Tag key={key} color={severityColorMap[value] || 'default'}>{key}={value}</Tag>;
    }
    return <Tag key={key}>{key}={value}</Tag>;
  };

  const sectionStyle: React.CSSProperties = {
    background: 'var(--bg-tertiary)',
    borderRadius: 8,
    padding: '12px 16px',
    marginBottom: 12,
  };

  const sectionTitleStyle: React.CSSProperties = {
    fontSize: 12,
    fontWeight: 600,
    color: 'var(--text-secondary)',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    marginBottom: 10,
    paddingBottom: 6,
    borderBottom: '1px solid var(--border-color)',
  };

  const fieldStyle: React.CSSProperties = {
    display: 'flex',
    alignItems: 'flex-start',
    gap: 8,
    marginBottom: 8,
    fontSize: 13,
  };

  const fieldLabelStyle: React.CSSProperties = {
    color: 'var(--text-secondary)',
    minWidth: 72,
    flexShrink: 0,
    paddingTop: 2,
  };

  const fieldValueStyle: React.CSSProperties = {
    color: 'var(--text-primary)',
    flex: 1,
    wordBreak: 'break-word',
  };

  const preStyle: React.CSSProperties = {
    background: 'var(--bg-elevated)',
    color: 'var(--text-primary)',
    border: '1px solid var(--border-color)',
    padding: 10,
    borderRadius: 6,
    fontSize: 12,
    margin: 0,
    flex: 1,
    wordBreak: 'break-all',
    whiteSpace: 'pre-wrap' as const,
    maxHeight: 100,
    overflow: 'auto' as const,
  };

  const renderStructuredView = (record: AlertHistoryType) => (
    <div style={{ color: 'var(--text-primary)' }}>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        <div>
          <div style={sectionStyle}>
            <div style={sectionTitleStyle}>基本信息</div>
            <div style={fieldStyle}>
              <span style={fieldLabelStyle}>告警名称</span>
              <span style={{ ...fieldValueStyle, fontWeight: 600 }}>{record.alertname}</span>
            </div>
            <div style={fieldStyle}>
              <span style={fieldLabelStyle}>状态</span>
              <Tag color={record.status === 'firing' ? 'red' : record.status === 'resolved' ? 'green' : 'default'}>
                {record.status === 'firing' ? '触发中' : record.status === 'resolved' ? '已解决' : '已抑制'}
              </Tag>
            </div>
            <div style={fieldStyle}>
              <span style={fieldLabelStyle}>级别</span>
              <Tag color={severityColorMap[record.severity] || 'default'}>{record.severity}</Tag>
            </div>
            <div style={fieldStyle}>
              <span style={fieldLabelStyle}>实例</span>
              <span style={fieldValueStyle}>{record.labels?.instance || '-'}</span>
            </div>
            <div style={{ ...fieldStyle, marginBottom: 0 }}>
              <span style={fieldLabelStyle}>开始时间</span>
              <span style={fieldValueStyle}>{record.startsAt ? new Date(record.startsAt).toLocaleString() : '-'}</span>
            </div>
          </div>
        </div>
        <div>
          <div style={sectionStyle}>
            <div style={sectionTitleStyle}>处理信息</div>
            <div style={fieldStyle}>
              <span style={fieldLabelStyle}>结束时间</span>
              <span style={fieldValueStyle}>{record.endsAt ? new Date(record.endsAt).toLocaleString() : '-'}</span>
            </div>
            <div style={fieldStyle}>
              <span style={fieldLabelStyle}>是否被抑制</span>
              <span style={fieldValueStyle}>{record.isSuppressed ? '是' : '否'}</span>
            </div>
            <div style={{ ...fieldStyle, marginBottom: 0 }}>
              <span style={fieldLabelStyle}>通知已发送</span>
              <span style={fieldValueStyle}>{record.notificationSent ? '是' : '否'}</span>
            </div>
          </div>
          <div style={sectionStyle}>
            <div style={sectionTitleStyle}>标签</div>
            <Space wrap size={[4, 4]}>
              {record.labels && Object.entries(record.labels).map(([k, v]) => renderLabelTag(k, v))}
            </Space>
          </div>
        </div>
      </div>
      <div style={{ ...sectionStyle, marginTop: 0 }}>
        <div style={sectionTitleStyle}>注解</div>
        <pre style={preStyle}>
          {JSON.stringify(record.annotations, null, 2)}
        </pre>
      </div>
    </div>
  );

  const renderJsonView = (record: AlertHistoryType) => (
    <div style={{ color: 'var(--text-primary)' }}>
      <div style={{ ...sectionStyle, marginBottom: 8 }}>
        <div style={sectionTitleStyle}>labels</div>
        <pre style={preStyle}>
          {JSON.stringify(record.labels, null, 2)}
        </pre>
      </div>
      <div style={{ ...sectionStyle, marginTop: 0 }}>
        <div style={sectionTitleStyle}>annotations</div>
        <pre style={preStyle}>
          {JSON.stringify(record.annotations, null, 2)}
        </pre>
      </div>
    </div>
  );

  const columns = [
    {
      title: '告警名称',
      dataIndex: 'alertname',
      key: 'alertname',
      width: 150,
      sorter: (a: AlertHistoryType, b: AlertHistoryType) => a.alertname.localeCompare(b.alertname),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      sorter: (a: AlertHistoryType, b: AlertHistoryType) => a.status.localeCompare(b.status),
      render: (status: string) => {
        const colorMap: Record<string, string> = {
          firing: 'red',
          resolved: 'green',
          suppressed: 'default',
        };
        const labelMap: Record<string, string> = {
          firing: '触发中',
          resolved: '已解决',
          suppressed: '已抑制',
        };
        return <Tag color={colorMap[status]}>{labelMap[status] || status}</Tag>;
      },
    },
    {
      title: '级别',
      dataIndex: 'severity',
      key: 'severity',
      width: 80,
      sorter: (a: AlertHistoryType, b: AlertHistoryType) => {
        const order: Record<string, number> = { critical: 0, high: 1, warning: 2, middle: 3, info: 4, low: 5 };
        return (order[a.severity] ?? 6) - (order[b.severity] ?? 6);
      },
      render: (severity: string) => {
        const colorMap: Record<string, string> = {
          info: 'blue',
          warning: 'orange',
          critical: 'red',
          high: 'volcano',
          middle: 'gold',
          low: 'default',
        };
        return <Tag color={colorMap[severity]}>{severity}</Tag>;
      },
    },
    {
      title: '实例',
      dataIndex: 'labels',
      key: 'instance',
      width: 150,
      sorter: (a: AlertHistoryType, b: AlertHistoryType) =>
        (a.labels?.instance || '').localeCompare(b.labels?.instance || ''),
      render: (labels: Record<string, string>) => labels?.instance || '-',
    },
    {
      title: '开始时间',
      dataIndex: 'startsAt',
      key: 'startsAt',
      width: 180,
      sorter: (a: AlertHistoryType, b: AlertHistoryType) =>
        new Date(a.startsAt || 0).getTime() - new Date(b.startsAt || 0).getTime(),
      render: (time: string) => time ? new Date(time).toLocaleString() : '-',
    },
    {
      title: '通知已发送',
      dataIndex: 'notificationSent',
      key: 'notificationSent',
      width: 100,
      sorter: (a: AlertHistoryType, b: AlertHistoryType) =>
        Number(a.notificationSent) - Number(b.notificationSent),
      render: (sent: boolean) => (
        <Tag color={sent ? 'green' : 'default'}>{sent ? '是' : '否'}</Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 80,
      render: (_: unknown, record: AlertHistoryType) => (
        <Button
          type="text"
          icon={<EyeOutlined />}
          onClick={() => handleShowDetail(record)}
        />
      ),
    },
  ];

  return (
    <div>
      <Card style={{ marginBottom: 16 }}>
        <Space wrap>
          <RangePicker onChange={handleTimeChange} />
          <Select
            placeholder="状态"
            value={params.status}
            onChange={handleStatusChange}
            style={{ width: 120 }}
            allowClear
            showSearch
            filterOption={fuzzyFilterOption}
            options={statusOptions}
          />
          <Search
            placeholder="搜索告警名称"
            onSearch={handleSearch}
            style={{ width: 200 }}
            allowClear
          />
        </Space>
      </Card>

      <Table
        columns={columns}
        dataSource={data?.items || []}
        rowKey="id"
        loading={isLoading}
        pagination={{
          current: params.page,
          pageSize: params.pageSize,
          total: data?.total || 0,
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total) => `共 ${total} 条`,
          onChange: (page, pageSize) => {
            setParams({ ...params, page, pageSize });
          },
        }}
      />

      <Modal
        title="告警详情"
        open={detailVisible}
        onCancel={() => setDetailVisible(false)}
        footer={[
          <Segmented
            key="viewToggle"
            options={[
              { label: '结构化', value: 'structured' },
              { label: 'JSON', value: 'json' },
            ]}
            value={viewMode}
            onChange={(val) => setViewMode(val as ViewMode)}
          />,
          <Button key="close" onClick={() => setDetailVisible(false)}>
            关闭
          </Button>,
        ]}
        width={700}
      >
        {selectedRecord && (
          viewMode === 'structured'
            ? renderStructuredView(selectedRecord)
            : renderJsonView(selectedRecord)
        )}
      </Modal>
    </div>
  );
};

export default AlertHistoryPage;
