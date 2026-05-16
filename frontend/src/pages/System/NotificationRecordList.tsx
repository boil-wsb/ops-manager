import { useState, useEffect, useCallback } from 'react';
import {
  Table,
  Button,
  Space,
  Tag,
  Card,
  Input,
  message,
  Popconfirm,
  Tooltip,
  Modal,
  Segmented,
  Descriptions,
} from 'antd';
import { DeleteOutlined, SearchOutlined, EyeOutlined } from '@ant-design/icons';
import { notificationRecordApi, type NotificationRecord } from '../../services/notification_record';

const { Search } = Input;

type ViewMode = 'structured' | 'json';

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
  textTransform: 'uppercase' as const,
  letterSpacing: '0.5px',
  marginBottom: 10,
  paddingBottom: 6,
  borderBottom: '1px solid var(--border-color)',
};

const preStyle: React.CSSProperties = {
  background: 'var(--bg-elevated)',
  color: 'var(--text-primary)',
  border: '1px solid var(--border-color)',
  padding: 10,
  borderRadius: 6,
  fontSize: 12,
  margin: 0,
  wordBreak: 'break-all',
  whiteSpace: 'pre-wrap' as const,
  maxHeight: 300,
  overflow: 'auto' as const,
};

const cardPreviewStyle: React.CSSProperties = {
  border: '1px solid var(--border-color)',
  borderRadius: 8,
  overflow: 'hidden',
  background: 'var(--bg-elevated)',
};

const cardHeaderStyle = (template: string = 'blue'): React.CSSProperties => {
  const colorMap: Record<string, string> = {
    blue: '#3370ff',
    green: '#2ea44f',
    orange: '#ff8800',
    red: '#d9363e',
    violet: '#652ecb',
    indigo: '#4f46e5',
    wathet: '#14c9ba',
    turquoise: '#0fc6c2',
    yellow: '#f5a623',
    default: '#3370ff',
  };
  return {
    background: colorMap[template] || colorMap.default,
    padding: '12px 16px',
    color: '#fff',
  };
};

const cardElementStyle: React.CSSProperties = {
  padding: '12px 16px',
  borderBottom: '1px solid var(--border-color)',
  fontSize: 13,
};

const NotificationRecordList = () => {
  const [records, setRecords] = useState<NotificationRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [searchText, setSearchText] = useState('');
  const [successFilter, setSuccessFilter] = useState<boolean | null>(null);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [selectedRecord, setSelectedRecord] = useState<NotificationRecord | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('structured');

  const fetchRecords = useCallback(async () => {
    setLoading(true);
    try {
      const response = await notificationRecordApi.getNotificationRecords({
        user: searchText || undefined,
        success: successFilter ?? undefined,
        page: currentPage,
        page_size: pageSize,
      });
      setRecords(response.data.items);
      setTotal(response.data.total);
    } catch {
      message.error('获取通知记录列表失败');
    } finally {
      setLoading(false);
    }
  }, [currentPage, pageSize, searchText, successFilter]);

  useEffect(() => {
    fetchRecords();
  }, [fetchRecords]);

  const handleDelete = async (id: number) => {
    try {
      await notificationRecordApi.deleteNotificationRecord(id);
      message.success('删除成功');
      fetchRecords();
    } catch {
      message.error('删除失败');
    }
  };

  const renderFeishuCardPreview = (cardContent: Record<string, unknown>) => {
    const header = cardContent.header as Record<string, unknown> | undefined;
    const elements = cardContent.elements as Record<string, unknown>[] | undefined;

    return (
      <div style={cardPreviewStyle}>
        {header && (
          <div style={cardHeaderStyle(header.template as string)}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              {header.ud_icon && (
                <span style={{ fontSize: 16 }}>
                  {String((header.ud_icon as Record<string, unknown>)?.tag || '')}
                </span>
              )}
              <div>
                <div style={{ fontWeight: 600, fontSize: 14 }}>
                  {String(header.title?.valueOf() ? (header.title as Record<string, unknown>)?.content || header.title : header.title || '无标题')}
                </div>
                {header.subtitle && (
                  <div style={{ fontSize: 12, opacity: 0.85 }}>
                    {String(
                      (header.subtitle as Record<string, unknown>)?.content || header.subtitle
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
        {elements && elements.length > 0 && (
          <div>
            {elements.map((element, index) => (
              <div key={index} style={cardElementStyle}>
                {renderCardElement(element)}
              </div>
            ))}
          </div>
        )}
        {!header && (!elements || elements.length === 0) && (
          <div style={{ padding: 16, color: 'var(--text-secondary)', textAlign: 'center' }}>
            无卡片内容
          </div>
        )}
      </div>
    );
  };

  const renderCardElement = (element: Record<string, unknown>) => {
    const tag = element.tag as string;

    if (tag === 'div') {
      const fields = element.fields as Record<string, unknown>[] | undefined;
      const text = element.text as Record<string, unknown> | undefined;

      return (
        <div>
          {text && (
            <div style={{ marginBottom: fields ? 8 : 0 }}>
              {String(text.content || '')}
            </div>
          )}
          {fields && fields.length > 0 && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: 8 }}>
              {fields.map((field, i) => (
                <div key={i}>
                  <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                    {String((field.is_short ? '' : '') + ((field.label as Record<string, unknown>)?.content || field.label || ''))}
                  </div>
                  <div style={{ fontWeight: 500 }}>
                    {String((field.text as Record<string, unknown>)?.content || field.text || '')}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      );
    }

    if (tag === 'markdown') {
      return (
        <div style={{ whiteSpace: 'pre-wrap' }}>
          {String(element.content || '')}
        </div>
      );
    }

    if (tag === 'action') {
      const actions = element.actions as Record<string, unknown>[] | undefined;
      return (
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {actions?.map((action, i) => {
            const btnTag = action.tag as string;
            if (btnTag === 'button') {
              return (
                <Tag key={i} color="blue" style={{ cursor: 'default' }}>
                  {String(action.text?.valueOf() ? (action.text as Record<string, unknown>)?.content || action.text : action.text || '按钮')}
                </Tag>
              );
            }
            return <Tag key={i}>{btnTag}</Tag>;
          })}
        </div>
      );
    }

    if (tag === 'note') {
      const notes = element.elements as Record<string, unknown>[] | undefined;
      return (
        <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
          {notes?.map((note, i) => (
            <span key={i}>
              {i > 0 && ' · '}
              {String(note.content || note.text || '')}
            </span>
          ))}
        </div>
      );
    }

    if (tag === 'hr') {
      return <div style={{ borderBottom: '1px solid var(--border-color)' }} />;
    }

    return (
      <div style={{ color: 'var(--text-secondary)' }}>
        [{tag}] {JSON.stringify(element, null, 2).slice(0, 100)}...
      </div>
    );
  };

  const renderStructuredView = (record: NotificationRecord) => (
    <div style={{ color: 'var(--text-primary)' }}>
      <div style={sectionStyle}>
        <div style={sectionTitleStyle}>基本信息</div>
        <Descriptions
          size="small"
          column={2}
          bordered
          style={{ background: 'transparent' }}
        >
          <Descriptions.Item label="查询用户">
            <span style={{ fontWeight: 500 }}>{record.user}</span>
          </Descriptions.Item>
          <Descriptions.Item label="匹配用户">
            {record.matchedUser || '-'}
          </Descriptions.Item>
          <Descriptions.Item label="接收类型">
            <Tag color={record.receiveType === 'chat_id' ? 'blue' : 'green'}>
              {record.receiveType === 'chat_id' ? '群聊' : '个人'}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="群聊ID">
            {record.chatId || '-'}
          </Descriptions.Item>
          <Descriptions.Item label="回调ID">
            {record.callbackId || '-'}
          </Descriptions.Item>
          <Descriptions.Item label="消息ID">
            {record.messageId || '-'}
          </Descriptions.Item>
          <Descriptions.Item label="发送状态">
            <Tag color={record.success ? 'success' : 'error'}>
              {record.success ? '成功' : '失败'}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="创建时间">
            {record.createdAt ? new Date(record.createdAt).toLocaleString('zh-CN') : '-'}
          </Descriptions.Item>
          {record.error && (
            <Descriptions.Item label="错误信息" span={2}>
              <span style={{ color: '#ff4d4f' }}>{record.error}</span>
            </Descriptions.Item>
          )}
        </Descriptions>
      </div>

      {record.cardContent && (
        <div style={sectionStyle}>
          <div style={sectionTitleStyle}>飞书卡片内容</div>
          {renderFeishuCardPreview(record.cardContent)}
        </div>
      )}
    </div>
  );

  const renderJsonView = (record: NotificationRecord) => (
    <div style={{ color: 'var(--text-primary)' }}>
      <div style={{ ...sectionStyle, marginBottom: 8 }}>
        <div style={sectionTitleStyle}>基本信息</div>
        <pre style={preStyle}>
          {JSON.stringify(
            {
              id: record.id,
              user: record.user,
              matchedUser: record.matchedUser,
              receiveType: record.receiveType,
              chatId: record.chatId,
              callbackId: record.callbackId,
              messageId: record.messageId,
              success: record.success,
              error: record.error,
              createdAt: record.createdAt,
            },
            null,
            2
          )}
        </pre>
      </div>
      {record.cardContent && (
        <div style={{ ...sectionStyle, marginTop: 0 }}>
          <div style={sectionTitleStyle}>cardContent</div>
          <pre style={preStyle}>
            {JSON.stringify(record.cardContent, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: '查询用户',
      dataIndex: 'user',
      key: 'user',
      width: 150,
      render: (text: string) => <span style={{ fontWeight: 500 }}>{text}</span>,
    },
    {
      title: '匹配用户',
      dataIndex: 'matchedUser',
      key: 'matchedUser',
      width: 150,
      render: (text: string) => text || '-',
    },
    {
      title: '回调ID',
      dataIndex: 'callbackId',
      key: 'callbackId',
      width: 150,
      render: (text: string) => text || '-',
    },
    {
      title: '接收类型',
      dataIndex: 'receiveType',
      key: 'receiveType',
      width: 100,
      render: (type: string) => (
        <Tag color={type === 'chat_id' ? 'blue' : 'green'}>
          {type === 'chat_id' ? '群聊' : '个人'}
        </Tag>
      ),
    },
    {
      title: '群聊ID',
      dataIndex: 'chatId',
      key: 'chatId',
      width: 200,
      ellipsis: true,
      render: (text: string) => text || '-',
    },
    {
      title: '状态',
      dataIndex: 'success',
      key: 'success',
      width: 100,
      render: (success: boolean) => (
        <Tag color={success ? 'success' : 'error'}>
          {success ? '成功' : '失败'}
        </Tag>
      ),
    },
    {
      title: '错误信息',
      dataIndex: 'error',
      key: 'error',
      ellipsis: true,
      render: (text: string) => (
        <Tooltip title={text}>
          <span style={{ color: text ? '#ff4d4f' : undefined }}>{text || '-'}</span>
        </Tooltip>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      key: 'createdAt',
      width: 180,
      render: (text: string) => {
        const date = new Date(text);
        return date.toLocaleString('zh-CN');
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_: unknown, record: NotificationRecord) => (
        <Space>
          <Tooltip title="查看详情">
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => {
                setSelectedRecord(record);
                setViewMode('structured');
                setDetailModalVisible(true);
              }}
            />
          </Tooltip>
          <Popconfirm
            title="确认删除"
            description="确定要删除此通知记录吗？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Tooltip title="删除">
              <Button type="text" danger icon={<DeleteOutlined />} />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Card
        title={
          <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center' }}>
            <Space>
              <Search
                placeholder="搜索用户"
                allowClear
                onSearch={(value) => {
                  setSearchText(value);
                  setCurrentPage(1);
                }}
                onChange={(e) => setSearchText(e.target.value)}
                style={{ width: 200 }}
                prefix={<SearchOutlined />}
              />
              <Button
                type={successFilter === true ? 'primary' : 'default'}
                onClick={() => {
                  setSuccessFilter(successFilter === true ? null : true);
                  setCurrentPage(1);
                }}
              >
                成功
              </Button>
              <Button
                type={successFilter === false ? 'primary' : 'default'}
                onClick={() => {
                  setSuccessFilter(successFilter === false ? null : false);
                  setCurrentPage(1);
                }}
              >
                失败
              </Button>
            </Space>
          </div>
        }
        style={{ background: 'var(--bg-card)' }}
      >
        <Table
          columns={columns}
          dataSource={records}
          rowKey="id"
          loading={loading}
          scroll={{ x: 'max-content' }}
          pagination={{
            current: currentPage,
            pageSize: pageSize,
            total: total,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 条`,
            onChange: (page, size) => {
              setCurrentPage(page);
              setPageSize(size || 10);
            },
          }}
        />
      </Card>
      <Modal
        title="通知详情"
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
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
          <Button key="close" onClick={() => setDetailModalVisible(false)}>
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

export default NotificationRecordList;
