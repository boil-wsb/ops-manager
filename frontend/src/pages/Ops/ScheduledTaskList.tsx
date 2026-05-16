import { useState } from 'react';
import { Table, Button, Select, Tag, Space, Card, App, Modal, Form, Input, Switch } from 'antd';
import { useQuery, useMutation } from '@tanstack/react-query';
import { ReloadOutlined, EditOutlined, PlayCircleOutlined } from '@ant-design/icons';
import { scheduledTaskApi } from '../../services/scheduledTask';
import { fuzzyFilterOption } from '../../utils/selectFilter';
import type { ScheduledTask, TaskExecutionLog } from '../../types';

const categoryColorMap: Record<string, string> = {
  sync: 'blue',
  monitor: 'green',
  cleanup: 'orange',
  ops: 'purple',
};

const triggerTypeColorMap: Record<string, string> = {
  cron: 'blue',
  interval: 'cyan',
};

const statusColorMap: Record<string, string> = {
  success: 'green',
  failed: 'red',
};

const logTriggerTypeColorMap: Record<string, string> = {
  scheduled: 'blue',
  manual: 'orange',
};

const formatTriggerConfig = (triggerType: string, config: Record<string, unknown>) => {
  if (triggerType === 'cron') {
    const hour = String(config.hour ?? '*').padStart(2, '0');
    const minute = String(config.minute ?? '0').padStart(2, '0');
    return `每天 ${hour}:${minute}`;
  }
  if (triggerType === 'interval') {
    const hours = config.hours as number | undefined;
    const minutes = config.minutes as number | undefined;
    const seconds = config.seconds as number | undefined;
    if (hours && hours > 0) return `每 ${hours} 小时`;
    if (minutes && minutes > 0) return `每 ${minutes} 分钟`;
    if (seconds && seconds > 0) return `每 ${seconds} 秒`;
    return '-';
  }
  return '-';
};

const formatDuration = (seconds: number | null) => {
  if (seconds === null || seconds === undefined) return '-';
  if (seconds < 1) return `${(seconds * 1000).toFixed(0)}ms`;
  return `${seconds.toFixed(1)}s`;
};

const ScheduledTaskList = () => {
  const { message, modal } = App.useApp();
  const [filter, setFilter] = useState({
    name: undefined as string | undefined,
    category: undefined as string | undefined,
    isEnabled: undefined as boolean | undefined,
    triggerType: undefined as string | undefined,
  });
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
  });
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editingTask, setEditingTask] = useState<ScheduledTask | null>(null);
  const [editForm] = Form.useForm();
  const [expandedRowKeys, setExpandedRowKeys] = useState<string[]>([]);
  const [runningTaskId, setRunningTaskId] = useState<string | null>(null);

  const { data: taskNames } = useQuery({
    queryKey: ['scheduledTaskNames'],
    queryFn: () => scheduledTaskApi.getTaskNames(),
  });

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['scheduledTasks', filter, pagination],
    queryFn: async () => {
      const result = await scheduledTaskApi.getScheduledTasks({
        skip: (pagination.current - 1) * pagination.pageSize,
        limit: pagination.pageSize,
        name: filter.name,
        category: filter.category,
        isEnabled: filter.isEnabled,
        triggerType: filter.triggerType,
      });
      return {
        items: Array.isArray(result) ? result : result?.items ?? [],
        total: Array.isArray(result) ? result.length : result?.total ?? 0,
      };
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ taskId, data }: { taskId: string; data: Parameters<typeof scheduledTaskApi.updateScheduledTask>[1] }) =>
      scheduledTaskApi.updateScheduledTask(taskId, data),
    onSuccess: () => {
      message.success('更新成功');
      setEditModalOpen(false);
      setEditingTask(null);
      editForm.resetFields();
      refetch();
    },
    onError: () => {
      message.error('更新失败');
    },
  });

  const runMutation = useMutation({
    mutationFn: scheduledTaskApi.runScheduledTask,
    onSuccess: (result) => {
      message.success(`执行成功，耗时 ${formatDuration(result.duration ?? null)}`);
      setRunningTaskId(null);
      refetch();
    },
    onError: (error: Error) => {
      message.error(`执行失败: ${error.message || '未知错误'}`);
      setRunningTaskId(null);
    },
  });

  const handleEdit = (record: ScheduledTask) => {
    setEditingTask(record);
    editForm.setFieldsValue({
      name: record.name,
      triggerConfig: record.triggerConfig,
      description: record.description ?? '',
      isEnabled: record.isEnabled,
    });
    setEditModalOpen(true);
  };

  const handleRun = (record: ScheduledTask) => {
    modal.confirm({
      title: '确认执行',
      content: `确定要手动执行任务「${record.name}」吗？`,
      onOk: () => {
        setRunningTaskId(record.taskId);
        runMutation.mutate(record.taskId);
      },
    });
  };

  const handleSave = async () => {
    try {
      const values = await editForm.validateFields();
      if (!editingTask) return;
      updateMutation.mutate({ taskId: editingTask.taskId, data: values });
    } catch {
      // validation failed
    }
  };

  const columns = [
    {
      title: '任务名称',
      dataIndex: 'name',
      key: 'name',
      sorter: (a: ScheduledTask, b: ScheduledTask) => a.name.localeCompare(b.name),
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      sorter: (a: ScheduledTask, b: ScheduledTask) => a.category.localeCompare(b.category),
      render: (category: string) => (
        <Tag color={categoryColorMap[category] || 'default'}>{category}</Tag>
      ),
    },
    {
      title: '触发类型',
      dataIndex: 'triggerType',
      key: 'triggerType',
      sorter: (a: ScheduledTask, b: ScheduledTask) => a.triggerType.localeCompare(b.triggerType),
      render: (triggerType: string) => (
        <Tag color={triggerTypeColorMap[triggerType] || 'default'}>{triggerType}</Tag>
      ),
    },
    {
      title: '调度配置',
      key: 'triggerConfig',
      render: (_: unknown, record: ScheduledTask) => formatTriggerConfig(record.triggerType, record.triggerConfig),
    },
    {
      title: '状态',
      dataIndex: 'isEnabled',
      key: 'isEnabled',
      sorter: (a: ScheduledTask, b: ScheduledTask) => (a.isEnabled === b.isEnabled ? 0 : a.isEnabled ? -1 : 1),
      render: (isEnabled: boolean) => (
        <Tag color={isEnabled ? 'green' : 'default'}>{isEnabled ? '启用' : '禁用'}</Tag>
      ),
    },
    {
      title: '上次执行时间',
      dataIndex: 'lastRunAt',
      key: 'lastRunAt',
      sorter: (a: ScheduledTask, b: ScheduledTask) => {
        if (!a.lastRunAt && !b.lastRunAt) return 0;
        if (!a.lastRunAt) return 1;
        if (!b.lastRunAt) return -1;
        return new Date(a.lastRunAt).getTime() - new Date(b.lastRunAt).getTime();
      },
      render: (time: string | null) => (time ? new Date(time).toLocaleString() : '-'),
    },
    {
      title: '上次执行状态',
      dataIndex: 'lastRunStatus',
      key: 'lastRunStatus',
      render: (status: string | null) => {
        if (!status) return '-';
        return <Tag color={statusColorMap[status] || 'default'}>{status}</Tag>;
      },
    },
    {
      title: '上次耗时',
      dataIndex: 'lastRunDuration',
      key: 'lastRunDuration',
      sorter: (a: ScheduledTask, b: ScheduledTask) => (a.lastRunDuration ?? 0) - (b.lastRunDuration ?? 0),
      render: (duration: number | null) => formatDuration(duration),
    },
    {
      title: '下次执行时间',
      dataIndex: 'nextRunTime',
      key: 'nextRunTime',
      sorter: (a: ScheduledTask, b: ScheduledTask) => {
        if (!a.nextRunTime && !b.nextRunTime) return 0;
        if (!a.nextRunTime) return 1;
        if (!b.nextRunTime) return -1;
        return new Date(a.nextRunTime).getTime() - new Date(b.nextRunTime).getTime();
      },
      render: (time: string | null) => (time ? new Date(time).toLocaleString() : '-'),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: ScheduledTask) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Button
            type="link"
            size="small"
            icon={<PlayCircleOutlined />}
            onClick={() => handleRun(record)}
            loading={runningTaskId === record.taskId && runMutation.isPending}
          >
            执行
          </Button>
        </Space>
      ),
    },
  ];

  const logColumns = [
    {
      title: '执行时间',
      dataIndex: 'startedAt',
      key: 'startedAt',
      render: (time: string) => (time ? new Date(time).toLocaleString() : '-'),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => <Tag color={statusColorMap[status] || 'default'}>{status}</Tag>,
    },
    {
      title: '耗时',
      dataIndex: 'duration',
      key: 'duration',
      render: (duration: number | null) => formatDuration(duration),
    },
    {
      title: '触发方式',
      dataIndex: 'triggerType',
      key: 'triggerType',
      render: (triggerType: string) => (
        <Tag color={logTriggerTypeColorMap[triggerType] || 'default'}>{triggerType}</Tag>
      ),
    },
    {
      title: '操作人',
      dataIndex: 'triggeredBy',
      key: 'triggeredBy',
      render: (triggeredBy: string | null) => triggeredBy || '-',
    },
    {
      title: '错误信息',
      dataIndex: 'errorMessage',
      key: 'errorMessage',
      ellipsis: true,
      render: (errorMessage: string | null) => errorMessage || '-',
    },
  ];

  const expandedRowRender = (record: ScheduledTask) => {
    return (
      <TaskLogTable taskId={record.taskId} columns={logColumns} />
    );
  };

  return (
    <div>
      <Card style={{ marginBottom: 24 }}>
        <Space wrap>
          <Select
            placeholder="搜索任务名称"
            value={filter.name}
            onChange={(value) => setFilter({ ...filter, name: value })}
            style={{ width: 200 }}
            allowClear
            showSearch
            filterOption={fuzzyFilterOption}
          >
            {(taskNames || []).map((name: string) => (
              <Select.Option key={name} value={name}>{name}</Select.Option>
            ))}
          </Select>
          <Select
            placeholder="分类"
            value={filter.category}
            onChange={(value) => setFilter({ ...filter, category: value })}
            style={{ width: 120 }}
            allowClear
            showSearch
            filterOption={fuzzyFilterOption}
          >
            <Select.Option value="sync">sync</Select.Option>
            <Select.Option value="monitor">monitor</Select.Option>
            <Select.Option value="cleanup">cleanup</Select.Option>
            <Select.Option value="ops">ops</Select.Option>
          </Select>
          <Select
            placeholder="状态"
            value={filter.isEnabled}
            onChange={(value) => setFilter({ ...filter, isEnabled: value })}
            style={{ width: 120 }}
            allowClear
            showSearch
            filterOption={fuzzyFilterOption}
          >
            <Select.Option value={true}>启用</Select.Option>
            <Select.Option value={false}>禁用</Select.Option>
          </Select>
          <Select
            placeholder="触发类型"
            value={filter.triggerType}
            onChange={(value) => setFilter({ ...filter, triggerType: value })}
            style={{ width: 120 }}
            allowClear
            showSearch
            filterOption={fuzzyFilterOption}
          >
            <Select.Option value="cron">cron</Select.Option>
            <Select.Option value="interval">interval</Select.Option>
          </Select>
          <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
            刷新
          </Button>
        </Space>
      </Card>

      <Table
        columns={columns}
        dataSource={data?.items || []}
        rowKey="taskId"
        loading={isLoading}
        expandable={{
          expandedRowKeys,
          onExpandedRowsChange: (keys) => setExpandedRowKeys(keys as string[]),
          expandedRowRender,
        }}
        pagination={{
          current: pagination.current,
          pageSize: pagination.pageSize,
          total: data?.total || 0,
          showSizeChanger: true,
          showTotal: (total: number) => `共 ${total} 条`,
          onChange: (page: number, pageSize: number) => setPagination({ current: page, pageSize }),
        }}
      />

      <Modal
        title="编辑定时任务"
        open={editModalOpen}
        onOk={handleSave}
        onCancel={() => {
          setEditModalOpen(false);
          setEditingTask(null);
          editForm.resetFields();
        }}
        confirmLoading={updateMutation.isPending}
        destroyOnHidden
      >
        <Form form={editForm} layout="vertical">
          <Form.Item label="任务名称" name="name" rules={[{ required: true, message: '请输入任务名称' }]}>
            <Input placeholder="输入任务名称" />
          </Form.Item>
          {editingTask?.triggerType === 'cron' && (
            <>
              <Form.Item label="小时" name={['triggerConfig', 'hour']}>
                <Input type="number" min={0} max={23} />
              </Form.Item>
              <Form.Item label="分钟" name={['triggerConfig', 'minute']}>
                <Input type="number" min={0} max={59} />
              </Form.Item>
              <Form.Item label="秒" name={['triggerConfig', 'second']}>
                <Input type="number" min={0} max={59} />
              </Form.Item>
            </>
          )}
          {editingTask?.triggerType === 'interval' && (
            <>
              <Form.Item label="秒" name={['triggerConfig', 'seconds']}>
                <Input type="number" min={0} />
              </Form.Item>
              <Form.Item label="分钟" name={['triggerConfig', 'minutes']}>
                <Input type="number" min={0} />
              </Form.Item>
              <Form.Item label="小时" name={['triggerConfig', 'hours']}>
                <Input type="number" min={0} />
              </Form.Item>
            </>
          )}
          <Form.Item label="描述" name="description">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item label="启用状态" name="isEnabled" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

const TaskLogTable = ({ taskId, columns }: { taskId: string; columns: unknown[] }) => {
  const { data, isLoading } = useQuery({
    queryKey: ['taskExecutionLogs', taskId],
    queryFn: async () => {
      const result = await scheduledTaskApi.getTaskExecutionLogs(taskId, { limit: 10 });
      return Array.isArray(result) ? result : result?.items ?? [];
    },
  });

  return (
    <Table
      columns={columns as Parameters<typeof Table>[0]['columns']}
      dataSource={data}
      rowKey="id"
      loading={isLoading}
      pagination={false}
      size="small"
    />
  );
};

export default ScheduledTaskList;
