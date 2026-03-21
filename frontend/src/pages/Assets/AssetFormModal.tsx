import { useMemo, useState } from 'react';
import { Modal, Form, Input, Select, InputNumber, App, Alert, Space, Tag, Tooltip, Row, Col } from 'antd';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { LockOutlined, CloudOutlined } from '@ant-design/icons';
import { assetApi } from '../../services/assets';
import type { Asset, Label } from '../../types';

const { Option } = Select;
const { TextArea } = Input;

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
      ownerName: '',
    };
  }, [asset]);

  const createMutation = useMutation({
    mutationFn: (data: Partial<Asset>) =>
      assetApi.createAsset({ ...data, label_ids: selectedLabelIds } as unknown as Partial<Asset>),
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
    mutationFn: ({ id, data }: { id: number; data: Partial<Asset> & { label_ids?: number[] } }) =>
      assetApi.updateAsset(id, { ...data, label_ids: selectedLabelIds } as unknown as Partial<Asset>),
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

  const renderLabel = (label: string, isReadOnly: boolean = false) => (
    <Space>
      {label}
      {isReadOnly && isPrometheusSource && (
        <Tooltip title="从 Prometheus 同步的字段，不可编辑">
          <LockOutlined style={{ color: '#999' }} />
        </Tooltip>
      )}
    </Space>
  );

  const labels = labelsData || [];

  return (
    <Modal
      title={
        <Space>
          {isEdit ? '编辑资产' : '新增资产'}
          {isPrometheusSource && (
            <Tag icon={<CloudOutlined />} color="blue">
              Prometheus
            </Tag>
          )}
        </Space>
      }
      open={open}
      onCancel={handleClose}
      onOk={handleSubmit}
      confirmLoading={isLoading}
      width={700}
      destroyOnHidden
    >
      {isPrometheusSource && (
        <Alert
          description="此资产从 Prometheus 自动同步，基础信息字段不可编辑。您只能修改负责人、标签和描述等扩展信息。"
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      <Form form={form} layout="vertical" preserve={false} initialValues={initialValues}>
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              name="assetId"
              label={renderLabel('资产编号', true)}
              rules={[{ required: true, message: '请输入资产编号' }]}
            >
              <Input placeholder="请输入资产编号" disabled={isEdit || isPrometheusSource} />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              name="name"
              label={renderLabel('资产名称', isPrometheusSource)}
              rules={[{ required: true, message: '请输入资产名称' }]}
            >
              <Input placeholder="请输入资产名称" disabled={isPrometheusSource} />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              name="assetType"
              label={renderLabel('资产类型', isPrometheusSource)}
              rules={[{ required: true, message: '请选择资产类型' }]}
            >
              <Select placeholder="请选择资产类型" disabled={isPrometheusSource}>
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
              label={renderLabel('状态', isPrometheusSource)}
              rules={[{ required: true, message: '请选择状态' }]}
            >
              <Select placeholder="请选择状态" disabled={isPrometheusSource}>
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
            <Form.Item name="ipAddress" label={renderLabel('IP地址', isPrometheusSource)}>
              <Input placeholder="请输入IP地址" disabled={isPrometheusSource} />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item name="privateIp" label={renderLabel('内网IP', isPrometheusSource)}>
              <Input placeholder="请输入内网IP" disabled={isPrometheusSource} />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col span={8}>
            <Form.Item name="cpuCores" label={renderLabel('CPU核数', isPrometheusSource)}>
              <InputNumber min={1} max={1024} placeholder="CPU核数" style={{ width: '100%' }} disabled={isPrometheusSource} />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item name="memoryGb" label={renderLabel('内存(GB)', isPrometheusSource)}>
              <InputNumber min={1} max={1024} placeholder="内存大小" style={{ width: '100%' }} disabled={isPrometheusSource} />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item name="diskGb" label={renderLabel('磁盘(GB)', isPrometheusSource)}>
              <InputNumber min={1} max={102400} placeholder="磁盘大小" style={{ width: '100%' }} disabled={isPrometheusSource} />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col span={12}>
            <Form.Item name="osType" label={renderLabel('操作系统', isPrometheusSource)}>
              <Input placeholder="请输入操作系统" disabled={isPrometheusSource} />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item name="osVersion" label={renderLabel('系统版本', isPrometheusSource)}>
              <Input placeholder="请输入系统版本" disabled={isPrometheusSource} />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col span={12}>
            <Form.Item name="ownerName" label="负责人">
              <Input placeholder="请输入负责人姓名" />
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
