import { useState, useEffect, useCallback, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Card, Table, Tag, Button, Space, Input, Select, Modal, Form, App, Popconfirm } from 'antd';
import { itFeedbackApi, type ITFeedback } from '../../services/itFeedback';

const { TextArea } = Input;

const lagLevelColors: Record<string, string> = {
  '1': 'green',
  '2': 'orange',
  '3': 'red',
  '4': 'magenta',
};

const statusColors: Record<string, string> = {
  pending: 'blue',
  resolved: 'green',
};

const computerTypeLabels: Record<string, string> = {
  desktop: '台式机',
  laptop: '笔记本',
  workstation: '工作站',
};

const usageYearsLabels: Record<string, string> = {
  less1: '1年以内',
  '1-3': '1-3年',
  '3-5': '3-5年',
  more5: '5年以上',
};

const lagLevelLabels: Record<string, string> = {
  '1': '轻微卡顿',
  '2': '一般卡顿',
  '3': '严重卡顿',
  '4': '无法使用',
};

const ITManagement = () => {
  const { message } = App.useApp();
  const [searchParams] = useSearchParams();
  const [loading, setLoading] = useState(false);
  const [feedbackList, setFeedbackList] = useState<ITFeedback[]>([]);
  const [total, setTotal] = useState(0);
  const [filters, setFilters] = useState<{ status?: string; lagLevel?: string }>({});
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [resolveModal, setResolveModal] = useState<{
    visible: boolean;
    feedback: ITFeedback | null;
    saving: boolean;
  }>({ visible: false, feedback: null, saving: false });
  const [form] = Form.useForm();
  const hasCheckedUrlRef = useRef(false);
  const [highlightedId, setHighlightedId] = useState<number | null>(null);

  useEffect(() => {
    if (!hasCheckedUrlRef.current && feedbackList.length > 0) {
      const feedbackId = searchParams.get('feedback_id');
      const action = searchParams.get('action');

      if (feedbackId && action === 'handle') {
        const feedback = feedbackList.find((f) => f.id === parseInt(feedbackId, 10));
        if (feedback && feedback.status === 'pending') {
          hasCheckedUrlRef.current = true;
          setHighlightedId(feedback.id);
          setResolveModal({ visible: true, feedback, saving: false });
        }
      }
    }
  }, [searchParams, feedbackList]);

  const fetchFeedbackList = useCallback(async () => {
    setLoading(true);
    try {
      const response = await itFeedbackApi.getITFeedbackList({
        ...filters,
        page: currentPage,
        page_size: pageSize,
      });
      setFeedbackList(response.data.items);
      setTotal(response.data.total);
    } catch {
      message.error('获取反馈列表失败');
    } finally {
      setLoading(false);
    }
  }, [currentPage, pageSize, filters, message]);

  useEffect(() => {
    fetchFeedbackList();
  }, [fetchFeedbackList]);

  const handleResolve = async (values: { resolvedBy: string; notes?: string }) => {
    if (!resolveModal.feedback) return;
    
    setResolveModal({ ...resolveModal, saving: true });
    try {
      await itFeedbackApi.resolveITFeedback(
        resolveModal.feedback.id,
        values.resolvedBy,
        values.notes
      );
      message.success('处理成功');
      setResolveModal({ visible: false, feedback: null, saving: false });
      form.resetFields();
      fetchFeedbackList();
    } catch {
      message.error('处理失败');
    } finally {
      setResolveModal((prev) => ({ ...prev, saving: false }));
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await itFeedbackApi.deleteITFeedback(id);
      message.success('删除成功');
      fetchFeedbackList();
    } catch {
      message.error('删除失败');
    }
  };

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 60,
      sorter: (a: ITFeedback, b: ITFeedback) => a.id - b.id,
    },
    {
      title: '电脑类型',
      dataIndex: 'computerType',
      key: 'computerType',
      width: 100,
      sorter: (a: ITFeedback, b: ITFeedback) => (a.computerType || '').localeCompare(b.computerType || ''),
      render: (text: string) => computerTypeLabels[text] || '-',
    },
    {
      title: '使用年限',
      dataIndex: 'usageYears',
      key: 'usageYears',
      width: 100,
      sorter: (a: ITFeedback, b: ITFeedback) => (a.usageYears || '').localeCompare(b.usageYears || ''),
      render: (text: string) => usageYearsLabels[text] || '-',
    },
    {
      title: '卡顿程度',
      dataIndex: 'lagLevel',
      key: 'lagLevel',
      width: 100,
      sorter: (a: ITFeedback, b: ITFeedback) => (a.lagLevel || '').localeCompare(b.lagLevel || ''),
      render: (lagLevel: string) => (
        <Tag color={lagLevelColors[lagLevel] || 'blue'}>
          {lagLevelLabels[lagLevel]}
        </Tag>
      ),
    },
    {
      title: '卡顿场景',
      dataIndex: 'lagScenarios',
      key: 'lagScenarios',
      width: 150,
      sorter: (a: ITFeedback, b: ITFeedback) => (a.lagScenarios || '').localeCompare(b.lagScenarios || ''),
      render: (text: string) => {
        if (!text) return '-';
        const scenarios = text.split(',');
        return scenarios.map((s: string) => (
          <Tag key={s} style={{ marginBottom: 4 }}>
            {s}
          </Tag>
        ));
      },
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      width: 200,
      sorter: (a: ITFeedback, b: ITFeedback) => (a.description || '').localeCompare(b.description || ''),
      render: (text: string) => text || '-',
    },
    {
      title: '联系方式',
      dataIndex: 'contact',
      key: 'contact',
      width: 120,
      sorter: (a: ITFeedback, b: ITFeedback) => (a.contact || '').localeCompare(b.contact || ''),
      render: (text: string) => text || '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 80,
      sorter: (a: ITFeedback, b: ITFeedback) => (a.status || '').localeCompare(b.status || ''),
      render: (status: string) => (
        <Tag color={statusColors[status]}>
          {status === 'pending' ? '待处理' : '已解决'}
        </Tag>
      ),
    },
    {
      title: '提交时间',
      dataIndex: 'createdAt',
      key: 'createdAt',
      width: 150,
      sorter: (a: ITFeedback, b: ITFeedback) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime(),
      render: (text: string) => new Date(text).toLocaleString('zh-CN'),
    },
    {
      title: '客户端IP',
      dataIndex: 'clientIp',
      key: 'clientIp',
      width: 130,
      sorter: (a: ITFeedback, b: ITFeedback) => (a.clientIp || '').localeCompare(b.clientIp || ''),
      render: (text: string) => text || '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_: unknown, record: ITFeedback) => (
        <Space>
          <Button
            type="link"
            size="small"
            onClick={() => setResolveModal({ visible: true, feedback: record, saving: false })}
            disabled={record.status === 'resolved'}
          >
            处理
          </Button>
          <Popconfirm
            title="确认删除"
            description="确定要删除这条反馈记录吗？"
            onConfirm={() => handleDelete(record.id)}
            okText="删除"
            cancelText="取消"
          >
            <Button type="link" danger size="small">
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Card>
        <Space style={{ marginBottom: 16 }}>
          <Select
            placeholder="状态筛选"
            style={{ width: 120 }}
            value={filters.status}
            onChange={(status) => setFilters({ ...filters, status })}
            allowClear
          >
            <Select.Option value="pending">待处理</Select.Option>
            <Select.Option value="resolved">已解决</Select.Option>
          </Select>
          <Select
            placeholder="卡顿程度"
            style={{ width: 120 }}
            value={filters.lagLevel}
            onChange={(lagLevel) => setFilters({ ...filters, lagLevel })}
            allowClear
          >
            <Select.Option value="1">轻微</Select.Option>
            <Select.Option value="2">一般</Select.Option>
            <Select.Option value="3">严重</Select.Option>
            <Select.Option value="4">无法使用</Select.Option>
          </Select>
          <Button
            onClick={() => {
              setFilters({});
              setCurrentPage(1);
            }}
          >
            重置
          </Button>
        </Space>
        
        <Table
          columns={columns}
          dataSource={feedbackList}
          rowKey="id"
          loading={loading}
          rowClassName={(record) => (highlightedId === record.id ? 'highlight-row' : '')}
          pagination={{
            current: currentPage,
            pageSize: pageSize,
            total: total,
            onChange: (page, size) => {
              setCurrentPage(page);
              setPageSize(size);
            },
          }}
          style={{ marginTop: 16 }}
        />
      </Card>

      <Modal
        title="处理反馈"
        open={resolveModal.visible}
        onCancel={() => {
          setResolveModal({ visible: false, feedback: null, saving: false });
          form.resetFields();
        }}
        onOk={() => form.submit()}
        confirmLoading={resolveModal.saving}
      >
        <Form form={form} layout="vertical" onFinish={handleResolve}>
          <Form.Item
            name="resolvedBy"
            label="处理人"
            rules={[{ required: true, message: '请输入处理人' }]}
          >
            <Input placeholder="请输入处理人姓名" />
          </Form.Item>
          <Form.Item name="notes" label="备注">
            <TextArea rows={4} placeholder="请输入处理备注" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ITManagement;
