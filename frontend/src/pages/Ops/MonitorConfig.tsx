import { useState } from 'react';
import {
  Table,
  Button,
  Card,
  Space,
  Tag,
  App,
  Modal,
  Form,
  Input,
  Select,
  InputNumber,
} from 'antd';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  PlusOutlined,
  SendOutlined,
  ReloadOutlined,
  EditOutlined,
  MinusCircleOutlined,
} from '@ant-design/icons';
import {
  monitorConfigApi,
  type MonitorHost,
  type HostPayload,
  type OperationResult,
} from '../../services/monitorConfig';
import { usePermission } from '../../hooks/usePermission';

const fileLabel: Record<string, string> = {
  linux: 'Linux',
  windows: 'Windows',
};

const fileColor: Record<string, string> = {
  linux: 'blue',
  windows: 'cyan',
};

const commonLinuxJobs = [
  'linux服务器监控',
  'pd3-monitor',
  'pd4-monitor',
  'pd5-monitor',
  'ops-monitor',
  'ops-服务器监控',
  'PD3-服务器监控',
];

const MonitorConfig = () => {
  const { message, modal } = App.useApp();
  const { hasAnyPermission } = usePermission();
  const canCreate = hasAnyPermission(['monitor:create']);
  const canWrite = hasAnyPermission(['monitor:update']);
  const canCommit = hasAnyPermission(['monitor:update']);

  const [filter, setFilter] = useState<'linux' | 'windows' | 'all'>('all');
  const [editOpen, setEditOpen] = useState(false);
  const [editing, setEditing] = useState<MonitorHost | null>(null);
  const [form] = Form.useForm();
  const [committing, setCommitting] = useState(false);
  const selectedFile = (form.getFieldValue('file') as 'linux' | 'windows' | undefined) ?? 'linux';

  const { data: hosts, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['monitorHosts'],
    queryFn: monitorConfigApi.getHosts,
  });

  // 后端为准的待提交操作（刷新/多标签页能恢复，驱动提交按钮状态）
  const { data: pendingOps = [], refetch: refetchPending } = useQuery({
    queryKey: ['monitorPending'],
    queryFn: monitorConfigApi.getPending,
  });

  const { data: gitStatus } = useQuery({
    queryKey: ['gitRepoStatus'],
    queryFn: monitorConfigApi.getGitStatus,
    retry: false,
  });

  // 本地与远端同步状态（含 pending 与节点是否领先/落后）
  const { data: syncStatus, refetch: refetchSync } = useQuery({
    queryKey: ['gitSync'],
    queryFn: monitorConfigApi.getSync,
    retry: false,
  });

  const pendingCount = pendingOps.length;

  const addMutation = useMutation<OperationResult, Error, HostPayload>({
    mutationFn: (payload) => monitorConfigApi.addHost(payload),
    onSuccess: (result) => {
      message.success(result?.message || '新增已暂存');
      setEditOpen(false);
      setEditing(null);
      form.resetFields();
      refetch();
      refetchPending();
    },
    onError: (e: Error) => message.error(`新增失败: ${e.message || '未知错误'}`),
  });

  const updateMutation = useMutation<
    OperationResult,
    Error,
    { index: number; payload: HostPayload }
  >({
    mutationFn: ({ index, payload }) => monitorConfigApi.updateHost({ ...payload, index }),
    onSuccess: (result) => {
      message.success(result?.message || '更新已暂存');
      setEditOpen(false);
      setEditing(null);
      form.resetFields();
      refetch();
      refetchPending();
    },
    onError: (e: Error) => message.error(`更新失败: ${e.message || '未知错误'}`),
  });

  const commitMutation = useMutation<OperationResult, Error, string>({
    mutationFn: (msg) => monitorConfigApi.commit(msg),
    onSuccess: (result) => {
      message.success(result?.message || '提交成功');
      setCommitting(false);
      refetch();
      refetchPending();
      refetchSync();
    },
    onError: (e: Error) => {
      setCommitting(false);
      message.error(`提交失败: ${e.message || '未知错误'}`);
    },
  });

  const pushMutation = useMutation<OperationResult, Error, void>({
    mutationFn: () => monitorConfigApi.push(),
    onSuccess: (result) => {
      message.success(result?.message || '已推送本地提交');
      setCommitting(false);
      refetch();
      refetchPending();
      refetchSync();
    },
    onError: (e: Error) => {
      setCommitting(false);
      message.error(`推送失败: ${e.message || '未知错误'}`);
    },
  });

  const handleAdd = () => {
    setEditing(null);
    form.resetFields();
    // 默认类型为 windows，端口自动 9182，job 默认 windows服务器监控
    form.setFieldsValue({ file: 'windows', port: 9182, job: 'windows服务器监控', labels: [] });
    setEditOpen(true);
  };

  const handleEdit = (record: MonitorHost) => {
    setEditing(record);
    // 从 raw.labels 中还原除 env/job/instance 之外的自定义标签
    const rawLabels = (record.raw?.labels as Record<string, string> | undefined) || {};
    const extraLabels = Object.entries(rawLabels)
      .filter(([k]) => !['env', 'job', 'instance'].includes(k))
      .map(([key, value]) => ({ key, value }));
    form.setFieldsValue({
      file: record.file,
      ip: record.ip,
      port: record.port,
      env: record.env,
      job: record.job,
      instance: record.instance,
      labels: extraLabels,
    });
    setEditOpen(true);
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      // 将自定义标签键值对数组转换为后端期望的 dict；空 key / 空 value 忽略
      const labelRows: Array<{ key?: string; value?: string }> = (values.labels ??
        []) as Array<{ key?: string; value?: string }>;
      const labels = labelRows.reduce<Record<string, string>>((acc, row) => {
        const key = (row?.key ?? '').trim();
        const value = String(row?.value ?? '').trim();
        if (key && value) acc[key] = value;
        return acc;
      }, {});
      const payload: HostPayload = {
        file: values.file,
        ip: values.ip,
        port: String(values.port),
        env: values.env,
        job: values.job,
        instance: values.instance,
        ...(Object.keys(labels).length ? { labels } : {}),
      };
      if (editing) {
        updateMutation.mutate({ index: editing.index, payload });
      } else {
        addMutation.mutate(payload);
      }
    } catch {
      // validation failed
    }
  };

  const handleCommit = () => {
    const hasDirty = !!syncStatus?.dirty;
    if (pendingCount === 0 && !syncStatus?.local_newer && !hasDirty) {
      message.warning('无待提交变更');
      return;
    }
    if (pendingCount === 0 && syncStatus?.local_newer && !hasDirty) {
      // 本地区有未推送提交但无 pending 暂存操作 → 仅推送
      modal.confirm({
        title: '确认推送',
        content: '本地存在尚未推送到远端分支的提交，确定推送吗？',
        onOk: () => {
          setCommitting(true);
          pushMutation.mutate();
        },
      });
      return;
    }
    const detail = pendingOps
      .map((op) => `${op.type}(${fileLabel[op.file] || op.file} ${op.addr})`)
      .join('; ');
    const msg = detail ? `同步监控主机: ${detail}` : 'sync: 监控配置同步';
    modal.confirm({
      title: '确认提交并推送',
      content: detail
        ? `将提交变更到 GitLab，提交信息：\n${msg}`
        : '检测到未提交的配置变更（可能为上次提交失败产生），将直接提交到 GitLab。',
      onOk: () => {
        setCommitting(true);
        commitMutation.mutate(msg);
      },
    });
  };

  const handleFileChange = (file: 'linux' | 'windows') => {
    // 切换类型时清理不适用的标签默认值，避免残留旧类型的 job/env/instance 被提交
    form.setFieldsValue({
      job: file === 'windows' ? 'windows服务器监控' : undefined,
      env: undefined,
      instance: undefined,
      // windows 主机默认端口 9182，linux 主机默认端口 9100
      port: file === 'windows' ? 9182 : 9100,
    });
  };

  const filteredHosts =
    filter === 'all' ? hosts : (hosts ?? []).filter((h) => h.file === filter);

  const columns = [
    {
      title: '类型',
      dataIndex: 'file',
      key: 'file',
      width: 90,
      render: (file: string) => <Tag color={fileColor[file]}>{fileLabel[file] || file}</Tag>,
    },
    { title: 'IP', dataIndex: 'ip', key: 'ip' },
    { title: '端口', dataIndex: 'port', key: 'port', width: 90 },
    { title: 'env', dataIndex: 'env', key: 'env' },
    { title: 'job', dataIndex: 'job', key: 'job' },
    { title: 'instance', dataIndex: 'instance', key: 'instance' },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_: unknown, record: MonitorHost) => (
        <Space>
          <Button
            size="small"
            icon={<EditOutlined />}
            disabled={!canWrite}
            title={canWrite ? undefined : '无编辑权限'}
            onClick={() => handleEdit(record)}
          />
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        <Card
          size="small"
          title="Git 仓库状态"
          extra={
            <Space>
              <Button
                icon={<ReloadOutlined />}
                onClick={() => {
                  refetch();
                  refetchSync();
                }}
              >
                刷新
              </Button>
              <Button
                type="primary"
                icon={<SendOutlined />}
                loading={committing}
                disabled={
                  !canCommit ||
                  (pendingCount === 0 &&
                    !syncStatus?.local_newer &&
                    !syncStatus?.dirty)
                }
                onClick={handleCommit}
              >
                提交并推送{pendingCount > 0 ? ` (${pendingCount})` : ''}
              </Button>
            </Space>
          }
        >
          <Space size={16}>
            <span>
              状态：
              {gitStatus?.cloned ? (
                <Tag color="green">已克隆</Tag>
              ) : (
                <Tag color="orange">未克隆</Tag>
              )}
            </span>
            {gitStatus?.branch && <span>分支：{gitStatus.branch}</span>}
            {gitStatus?.head && <span>HEAD：{gitStatus.head}</span>}
            <span>
              同步：
              {syncStatus?.local_newer ? (
                <Tag color="orange">本地较新（领先 {syncStatus?.ahead ?? 0}）</Tag>
              ) : syncStatus?.remote_newer ? (
                <Tag color="blue">远端较新（落后 {syncStatus?.behind ?? 0}）</Tag>
              ) : syncStatus?.is_synced ? (
                <Tag color="green">已同步</Tag>
              ) : gitStatus?.cloned ? (
                <Tag color="default">检查中</Tag>
              ) : null}
            </span>
          </Space>
        </Card>

        <Card
          size="small"
          title="监控主机"
          extra={
            <Space>
              <Select
                value={filter}
                onChange={setFilter}
                style={{ width: 110 }}
                options={[
                  { value: 'all', label: '全部' },
                  { value: 'linux', label: 'Linux' },
                  { value: 'windows', label: 'Windows' },
                ]}
              />
              <Button
                type="primary"
                icon={<PlusOutlined />}
                disabled={!canCreate}
                title={canCreate ? undefined : '无新增权限'}
                onClick={handleAdd}
              >
                新增主机
              </Button>
            </Space>
          }
        >
          <Table
            rowKey={(r: MonitorHost) => `${r.file}-${r.index}`}
            columns={columns}
            dataSource={filteredHosts}
            loading={isLoading || isFetching}
            pagination={{ pageSize: 20, showSizeChanger: true }}
            size="middle"
          />
        </Card>
      </Space>

      <Modal
        title={editing ? '编辑主机' : '新增主机'}
        open={editOpen}
        onOk={handleSave}
        onCancel={() => {
          setEditOpen(false);
          setEditing(null);
          form.resetFields();
        }}
        confirmLoading={addMutation.isPending || updateMutation.isPending}
        destroyOnClose
      >
        <Form form={form} layout="vertical" style={{ marginTop: 8 }}>
          <Form.Item name="file" label="类型" rules={[{ required: true }]}>
            <Select
              options={[
                { value: 'linux', label: 'Linux' },
                { value: 'windows', label: 'Windows' },
              ]}
              onChange={handleFileChange}
            />
          </Form.Item>
          <Form.Item
            name="ip"
            label="IP"
            rules={[
              { required: true, message: '请输入 IP' },
              {
                validator: (_, v) => {
                  if (!v) return Promise.resolve();
                  const ipv4 = /^(\d{1,3}\.){3}\d{1,3}$/;
                  const ipv6 = /^[0-9a-fA-F:]+$/;
                  if (ipv4.test(v)) {
                    const valid = v
                      .split('.')
                      .every((oct: string) => Number(oct) >= 0 && Number(oct) <= 255);
                    return valid
                      ? Promise.resolve()
                      : Promise.reject(new Error('IP 各段需在 0-255'));
                  }
                  return ipv6.test(v) ? Promise.resolve() : Promise.reject(new Error('IP 格式非法'));
                },
              },
            ]}
          >
            <Input placeholder="192.168.x.x" />
          </Form.Item>
          <Form.Item
            name="port"
            label="端口"
            rules={[{ required: true, message: '请输入端口' }]}
          >
            <InputNumber style={{ width: '100%' }} min={1} max={65535} />
          </Form.Item>
          <Form.Item
            name="env"
            label="env"
            rules={[{ required: true, message: '请输入 env' }]}
          >
            <Input placeholder="如 shanqi / promethues" />
          </Form.Item>
          <Form.Item name="job" label="job">
            <Select
              allowClear
              showSearch
              options={
                selectedFile === 'windows'
                  ? [{ value: 'windows服务器监控', label: 'windows服务器监控' }]
                  : commonLinuxJobs.map((j) => ({ value: j, label: j }))
              }
            />
          </Form.Item>
          <Form.Item
            name="instance"
            label="instance"
            rules={[{ required: true, message: '请输入 instance' }]}
          >
            <Input placeholder="主机名或 IP" />
          </Form.Item>
          <Form.Item label="自定义标签">
            <Form.List name="labels">
              {(fields, { add, remove }) => (
                <>
                  {fields.map(({ key, name, ...restField }) => (
                    <Space key={key} align="baseline" style={{ display: 'flex', marginBottom: 8 }}>
                      <Form.Item
                        {...restField}
                        name={[name, 'key']}
                        rules={[{ required: true, message: '请输入标签名' }]}
                        style={{ marginBottom: 0 }}
                      >
                        <Input placeholder="标签名" style={{ width: 180 }} />
                      </Form.Item>
                      <Form.Item
                        {...restField}
                        name={[name, 'value']}
                        style={{ marginBottom: 0 }}
                      >
                        <Input placeholder="标签值" style={{ width: 200 }} />
                      </Form.Item>
                      <MinusCircleOutlined onClick={() => remove(name)} />
                    </Space>
                  ))}
                  <Button
                    type="dashed"
                    onClick={() => add({ key: '', value: '' })}
                    block
                    icon={<PlusOutlined />}
                  >
                    添加标签
                  </Button>
                </>
              )}
            </Form.List>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default MonitorConfig;