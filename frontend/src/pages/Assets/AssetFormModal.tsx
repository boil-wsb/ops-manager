import { useMemo, useState, useEffect } from 'react';
import { Modal, Form, Input, Select, InputNumber, App, Alert, Space, Tag, Row, Col, Descriptions } from 'antd';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { CloudOutlined } from '@ant-design/icons';
import { assetApi, type OwnerUser } from '../../services/assets';
import type { Asset, Label } from '../../types';

const { Option } = Select;
const { TextArea } = Input;

// 资产类型中文映射
const ASSET_TYPE_LABELS: Record<string, string> = {
  SERVER: '物理机',
  VM: '虚拟机',
  NETWORK: '网络设备',
  STORAGE: '存储设备',
  TERMINAL: '终端',
};

// 资产状态中文映射 + 颜色
const ASSET_STATUS_META: Record<string, { label: string; color: string }> = {
  ACTIVE: { label: '运行中', color: 'green' },
  OFFLINE: { label: '离线', color: 'default' },
  MAINTENANCE: { label: '维护中', color: 'orange' },
  RETIRED: { label: '已退役', color: 'red' },
};

interface AssetFormModalProps {
  open: boolean;
  onClose: () => void;
  asset?: Asset | null;
}

const AssetFormModal: React.FC<AssetFormModalProps> = ({ open, onClose, asset }) => {
  const [form] = Form.useForm();
  const queryClient = useQueryClient();
  const { message } = App.useApp();
  const isEdit = !!asset;
  const isPrometheusSource = asset?.source === 'PROMETHEUS';

  const { data: labelsData } = useQuery({
    queryKey: ['labels'],
    queryFn: assetApi.getLabels,
  });

  const [searchKeyword, setSearchKeyword] = useState('');
  const [debouncedKeyword, setDebouncedKeyword] = useState('');

  // 防抖搜索
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedKeyword(searchKeyword), 300);
    return () => clearTimeout(timer);
  }, [searchKeyword]);

  const { data: ownerUsers = [] } = useQuery({
    queryKey: ['owner-users', debouncedKeyword],
    queryFn: () => assetApi.getUsersForOwner(debouncedKeyword || undefined),
  });

  const initialLabelIds = useMemo(() => asset?.labels?.map((l) => l.id) || [], [asset]);

  const [selectedLabelIds, setSelectedLabelIds] = useState<number[]>(initialLabelIds);

  const initialValues = useMemo(() => {
    if (asset) {
      return {
        assetId: asset.assetId,
        name: asset.name,
        assetType: asset.assetType,
        status: asset.status,
        ipAddress: asset.ipAddress,
        privateIp: asset.privateIp,
        cpuCores: asset.cpuCores,
        memoryGb: asset.memoryGb,
        diskGb: asset.diskGb,
        osType: asset.osType,
        osVersion: asset.osVersion,
        description: asset.description,
        ownerId: asset.ownerId,
        ownerName: asset.ownerName,
      };
    }
    return {
      assetId: '',
      name: '',
      assetType: 'SERVER',
      status: 'ACTIVE',
      ipAddress: '',
      privateIp: '',
      cpuCores: undefined,
      memoryGb: undefined,
      diskGb: undefined,
      osType: '',
      osVersion: '',
      description: '',
      ownerId: undefined,
      ownerName: '',
    };
  }, [asset]);

  const createMutation = useMutation({
    mutationFn: (data: { ownerName?: string; ownerId?: number; [key: string]: unknown }) => {
      const { ownerName, ownerId, ...rest } = data;
      return assetApi.createAsset({
        ...rest,
        owner_name: ownerName,
        owner_id: ownerId,
        label_ids: selectedLabelIds,
      } as Partial<Asset>);
    },
    onSuccess: () => {
      message.success('资产创建成功');
      queryClient.invalidateQueries({ queryKey: ['assets'] });
      handleClose();
    },
    onError: () => {
      message.error('资产创建失败');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: { ownerName?: string; ownerId?: number; [key: string]: unknown } }) => {
      const { ownerName, ownerId, ...rest } = data;
      return assetApi.updateAsset(id, {
        ...rest,
        owner_name: ownerName,
        owner_id: ownerId,
        label_ids: selectedLabelIds,
      } as Partial<Asset>);
    },
    onSuccess: () => {
      message.success('资产更新成功');
      queryClient.invalidateQueries({ queryKey: ['assets'] });
      handleClose();
    },
    onError: () => {
      message.error('资产更新失败');
    },
  });

  const handleClose = () => {
    form.resetFields();
    setSelectedLabelIds([]);
    onClose();
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      if (isEdit && asset) {
        updateMutation.mutate({ id: asset.id, data: values });
      } else {
        createMutation.mutate(values);
      }
    } catch {
      console.error('Validation failed');
    }
  };

  const isLoading = createMutation.isPending || updateMutation.isPending;

  // 编辑时确保当前负责人出现在选项中
  const ownerOptions = useMemo(() => {
    const options = ownerUsers.map((user: OwnerUser) => ({
      value: user.id,
      label: user.fullName ? `${user.fullName}（${user.username}）` : user.username,
    }));
    if (asset?.ownerId && !options.find((o) => o.value === asset.ownerId)) {
      options.unshift({
        value: asset.ownerId,
        label: asset.ownerName || `ID: ${asset.ownerId}`,
      });
    }
    return options;
  }, [ownerUsers, asset]);

  const labels = labelsData || [];

  // 状态展示：Prometheus 模式下用 Tag 着色
  const renderStatusValue = (status?: string) => {
    if (!status) return '-';
    const meta = ASSET_STATUS_META[status];
    if (!meta) return status;
    return <Tag color={meta.color}>{meta.label}</Tag>;
  };

  return (
    <Modal
      title={
        <Space>
          {isEdit ? '编辑资产' : '新增资产'}
          {isPrometheusSource && (
            <Tag icon={<CloudOutlined />} color="blue">
              Prometheus 同步
            </Tag>
          )}
        </Space>
      }
      open={open}
      onCancel={handleClose}
      onOk={handleSubmit}
      confirmLoading={isLoading}
      width={720}
      destroyOnHidden
    >
      {isPrometheusSource && (
        <Alert
          description="此资产从 Prometheus 自动同步，基础信息以属性详情形式展示，仅可修改负责人、标签和描述等扩展信息。"
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      <Form form={form} layout="vertical" preserve={false} initialValues={initialValues}>
        {isPrometheusSource ? (
          <>
            {/* Prometheus 同步资产：基础信息以属性详情方式展示 */}
            <Descriptions
              title="基础信息"
              bordered
              column={2}
              size="small"
              style={{ marginBottom: 16 }}
              labelStyle={{ width: 110, backgroundColor: '#fafafa' }}
            >
              <Descriptions.Item label="资产编号">{asset?.assetId || '-'}</Descriptions.Item>
              <Descriptions.Item label="资产名称">{asset?.name || '-'}</Descriptions.Item>
              <Descriptions.Item label="资产类型">
                {ASSET_TYPE_LABELS[asset?.assetType || ''] || asset?.assetType || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="状态">{renderStatusValue(asset?.status)}</Descriptions.Item>
              <Descriptions.Item label="IP地址">{asset?.ipAddress || '-'}</Descriptions.Item>
              <Descriptions.Item label="内网IP">{asset?.privateIp || '-'}</Descriptions.Item>
              <Descriptions.Item label="CPU核数">{asset?.cpuCores ?? '-'}</Descriptions.Item>
              <Descriptions.Item label="内存(GB)">{asset?.memoryGb ?? '-'}</Descriptions.Item>
              <Descriptions.Item label="磁盘(GB)">{asset?.diskGb ?? '-'}</Descriptions.Item>
              <Descriptions.Item label="操作系统">{asset?.osType || '-'}</Descriptions.Item>
              <Descriptions.Item label="系统版本" span={2}>{asset?.osVersion || '-'}</Descriptions.Item>
            </Descriptions>

            {/* 隐藏字段：保证表单提交时包含完整数据 */}
            <Form.Item name="assetId" hidden><Input /></Form.Item>
            <Form.Item name="name" hidden><Input /></Form.Item>
            <Form.Item name="assetType" hidden><Input /></Form.Item>
            <Form.Item name="status" hidden><Input /></Form.Item>
            <Form.Item name="ipAddress" hidden><Input /></Form.Item>
            <Form.Item name="privateIp" hidden><Input /></Form.Item>
            <Form.Item name="cpuCores" hidden><Input /></Form.Item>
            <Form.Item name="memoryGb" hidden><Input /></Form.Item>
            <Form.Item name="diskGb" hidden><Input /></Form.Item>
            <Form.Item name="osType" hidden><Input /></Form.Item>
            <Form.Item name="osVersion" hidden><Input /></Form.Item>
          </>
        ) : (
          <>
            {/* 新增或非 Prometheus 资产：完整可编辑表单 */}
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  name="assetId"
                  label="资产编号"
                  rules={[{ required: true, message: '请输入资产编号' }]}
                >
                  <Input placeholder="请输入资产编号" disabled={isEdit} />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  name="name"
                  label="资产名称"
                  rules={[{ required: true, message: '请输入资产名称' }]}
                >
                  <Input placeholder="请输入资产名称" />
                </Form.Item>
              </Col>
            </Row>

            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  name="assetType"
                  label="资产类型"
                  rules={[{ required: true, message: '请选择资产类型' }]}
                >
                  <Select placeholder="请选择资产类型">
                    <Option value="SERVER">物理机</Option>
                    <Option value="VM">虚拟机</Option>
                    <Option value="NETWORK">网络设备</Option>
                    <Option value="STORAGE">存储设备</Option>
                  </Select>
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  name="status"
                  label="状态"
                  rules={[{ required: true, message: '请选择状态' }]}
                >
                  <Select placeholder="请选择状态">
                    <Option value="ACTIVE">运行中</Option>
                    <Option value="OFFLINE">离线</Option>
                    <Option value="MAINTENANCE">维护中</Option>
                    <Option value="RETIRED">已退役</Option>
                  </Select>
                </Form.Item>
              </Col>
            </Row>

            <Row gutter={16}>
              <Col span={12}>
                <Form.Item name="ipAddress" label="IP地址">
                  <Input placeholder="请输入IP地址" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="privateIp" label="内网IP">
                  <Input placeholder="请输入内网IP" />
                </Form.Item>
              </Col>
            </Row>

            <Row gutter={16}>
              <Col span={8}>
                <Form.Item name="cpuCores" label="CPU核数">
                  <InputNumber min={1} max={1024} placeholder="CPU核数" style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="memoryGb" label="内存(GB)">
                  <InputNumber min={1} max={1024} placeholder="内存大小" style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="diskGb" label="磁盘(GB)">
                  <InputNumber min={1} max={102400} placeholder="磁盘大小" style={{ width: '100%' }} />
                </Form.Item>
              </Col>
            </Row>

            <Row gutter={16}>
              <Col span={12}>
                <Form.Item name="osType" label="操作系统">
                  <Input placeholder="请输入操作系统" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="osVersion" label="系统版本">
                  <Input placeholder="请输入系统版本" />
                </Form.Item>
              </Col>
            </Row>
          </>
        )}

        {/* 可编辑字段：负责人、标签、描述（所有模式通用） */}
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item name="ownerId" label="负责人">
              <Select
                showSearch
                placeholder="请输入姓名或用户名搜索"
                allowClear
                filterOption={false}
                onSearch={setSearchKeyword}
                notFoundContent={null}
                onChange={(value) => {
                  if (value === undefined) {
                    form.setFieldValue('ownerName', undefined);
                  } else {
                    const selectedUser = ownerUsers.find((u: OwnerUser) => u.id === value);
                    form.setFieldValue('ownerName', selectedUser?.fullName || value);
                  }
                }}
                options={ownerOptions}
              />
            </Form.Item>
            <Form.Item name="ownerName" hidden>
              <Input />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item label="标签">
              <Select
                mode="multiple"
                placeholder="请选择标签"
                value={selectedLabelIds}
                onChange={setSelectedLabelIds}
                style={{ width: '100%' }}
                optionFilterProp="children"
              >
                {labels.map((label: Label) => (
                  <Option key={label.id} value={label.id}>
                    <Tag color={label.color}>{label.name}</Tag>
                  </Option>
                ))}
              </Select>
            </Form.Item>
          </Col>
        </Row>

        <Form.Item name="description" label="描述">
          <TextArea rows={3} placeholder="请输入描述" />
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default AssetFormModal;
