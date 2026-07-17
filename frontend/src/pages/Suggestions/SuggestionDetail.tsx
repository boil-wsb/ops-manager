import { useState } from 'react';
import { Card, Descriptions, Tag, Table, Button, Modal, Input, App, Space, Spin } from 'antd';
import { ArrowLeftOutlined, SaveOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useParams, useNavigate } from 'react-router-dom';
import { suggestionApi } from '../../services/suggestion';
import type { AssignmentInfo } from '../../services/suggestion';
import { PermissionGuard } from '../../components/PermissionGuard';

const { TextArea } = Input;

const statusConfig: Record<string, { color: string; text: string }> = {
  pending: { color: 'orange', text: '待审批' },
  approved: { color: 'blue', text: '已审批' },
  archived: { color: 'green', text: '已存档' },
  rejected: { color: 'default', text: '已驳回' },
};

const assignmentStatusConfig: Record<string, { color: string; text: string }> = {
  pending: { color: 'orange', text: '待审批' },
  approved: { color: 'green', text: '已通过' },
  rejected: { color: 'red', text: '已驳回' },
};

const SuggestionDetail = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { message } = App.useApp();
  const [archiveModalOpen, setArchiveModalOpen] = useState(false);
  const [marketResult, setMarketResult] = useState('');

  const { data: suggestion, isLoading } = useQuery({
    queryKey: ['suggestions', 'detail', id],
    queryFn: () => suggestionApi.getDetail(Number(id)),
    enabled: !!id,
  });

  const archiveMutation = useMutation({
    mutationFn: () => suggestionApi.archive(Number(id), marketResult),
    onSuccess: () => {
      message.success('存档成功');
      setArchiveModalOpen(false);
      setMarketResult('');
      queryClient.invalidateQueries({ queryKey: ['suggestions', 'detail', id] });
      queryClient.invalidateQueries({ queryKey: ['suggestions', 'list'] });
    },
    onError: (error: unknown) => {
      const errorMsg = error instanceof Error ? error.message : '存档失败';
      message.error(errorMsg);
    },
  });

  if (isLoading) {
    return <div style={{ textAlign: 'center', padding: 60 }}><Spin size="large" /></div>;
  }

  if (!suggestion) {
    return <div>建议不存在</div>;
  }

  const statusCfg = statusConfig[suggestion.status] || { color: 'default', text: suggestion.status };

  const assignmentColumns = [
    {
      title: '指派类型',
      key: 'type',
      width: 100,
      render: (_: unknown, record: AssignmentInfo) => {
        if (record.departmentName) return <Tag color="blue">部门</Tag>;
        if (record.assigneeName) return <Tag color="purple">个人</Tag>;
        return <Tag>未知</Tag>;
      },
    },
    {
      title: '指派对象',
      key: 'target',
      render: (_: unknown, record: AssignmentInfo) => {
        if (record.departmentName) return record.departmentName;
        if (record.assigneeName) return record.assigneeName;
        return '-';
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const cfg = assignmentStatusConfig[status] || { color: 'default', text: status };
        return <Tag color={cfg.color}>{cfg.text}</Tag>;
      },
    },
    {
      title: '审批时间',
      dataIndex: 'reviewedAt',
      key: 'reviewedAt',
      width: 180,
      render: (time: string | null) => time ? new Date(time).toLocaleString('zh-CN') : '-',
    },
    {
      title: '审批意见',
      dataIndex: 'reviewComment',
      key: 'reviewComment',
      ellipsis: true,
      render: (comment: string | null) => comment || '-',
    },
  ];

  return (
    <div>
      <Card style={{ marginBottom: 16 }}>
        <Space style={{ marginBottom: 16 }}>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/suggestions/manage')}>
            返回列表
          </Button>
          <Tag color={statusCfg.color} style={{ fontSize: 14, padding: '4px 12px' }}>
            {statusCfg.text}
          </Tag>
          {/* 市场部负责人可存档（仅 approved 状态） */}
          {suggestion.status === 'approved' && (
            <PermissionGuard permissions="suggestion:archive">
              <Button
                type="primary"
                icon={<SaveOutlined />}
                onClick={() => setArchiveModalOpen(true)}
              >
                填写执行结果并存档
              </Button>
            </PermissionGuard>
          )}
        </Space>

        <Descriptions column={2} bordered>
          <Descriptions.Item label="建议ID">{suggestion.id}</Descriptions.Item>
          <Descriptions.Item label="查询码">{suggestion.queryCode}</Descriptions.Item>
          <Descriptions.Item label="创建时间">
            {new Date(suggestion.createdAt).toLocaleString('zh-CN')}
          </Descriptions.Item>
          <Descriptions.Item label="存档时间">
            {suggestion.archivedAt ? new Date(suggestion.archivedAt).toLocaleString('zh-CN') : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="意见内容" span={2}>
            {suggestion.content}
          </Descriptions.Item>
          {suggestion.highlights && (
            <Descriptions.Item label="项目服务亮点" span={2}>
              {suggestion.highlights}
            </Descriptions.Item>
          )}
          {suggestion.innovationIdeas && (
            <Descriptions.Item label="创新/效能提高idea" span={2}>
              {suggestion.innovationIdeas}
            </Descriptions.Item>
          )}
          {suggestion.marketResult && (
            <Descriptions.Item label="市场部执行结果" span={2}>
              {suggestion.marketResult}
            </Descriptions.Item>
          )}
          {suggestion.rejectReason && (
            <Descriptions.Item label="驳回原因" span={2}>
              <span style={{ color: '#ff4d4f' }}>{suggestion.rejectReason}</span>
            </Descriptions.Item>
          )}
        </Descriptions>
      </Card>

      <Card title="指派与审批记录">
        <Table
          columns={assignmentColumns}
          dataSource={suggestion.assignments}
          rowKey="id"
          pagination={false}
          size="small"
        />
      </Card>

      <Modal
        title="填写执行结果并存档"
        open={archiveModalOpen}
        onCancel={() => { setArchiveModalOpen(false); setMarketResult(''); }}
        onOk={() => archiveMutation.mutate()}
        confirmLoading={archiveMutation.isPending}
        okText="存档"
        cancelText="取消"
        okButtonProps={{ disabled: !marketResult.trim() }}
      >
        <TextArea
          value={marketResult}
          onChange={(e) => setMarketResult(e.target.value)}
          placeholder="请输入市场部执行结果..."
          autoSize={{ minRows: 4, maxRows: 10 }}
          maxLength={2000}
          showCount
        />
      </Modal>
    </div>
  );
};

export default SuggestionDetail;
