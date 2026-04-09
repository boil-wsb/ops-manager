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
} from 'antd';
import { DeleteOutlined, SearchOutlined, EyeOutlined } from '@ant-design/icons';
import { notificationRecordApi, type NotificationRecord } from '../../services/notification_record';

const { Search } = Input;

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
        footer={
          <Button type="primary" onClick={() => setDetailModalVisible(false)}>
            关闭
          </Button>
        }
        width={700}
      >
        {selectedRecord && (
          <pre style={{ background: 'var(--bg-tertiary)', padding: 16, borderRadius: 4, overflow: 'auto', maxHeight: 500, color: 'var(--text-color)' }}>
            {JSON.stringify(selectedRecord, null, 2)}
          </pre>
        )}
      </Modal>
    </div>
  );
};

export default NotificationRecordList;