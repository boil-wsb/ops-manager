import { useState } from 'react';
import { Table, Button, Tag, Space, Card, Progress, Alert } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { PlusOutlined, SafetyCertificateOutlined } from '@ant-design/icons';
import type { Certificate } from '../../types';

// Mock API for now
const mockCertificates: Certificate[] = [
  {
    id: 1,
    domain: 'ops-manager.example.com',
    issuer: 'Let\'s Encrypt',
    subject: 'CN=ops-manager.example.com',
    serialNumber: '00:11:22:33:44:55:66:77:88:99:aa:bb:cc:dd:ee:ff',
    validFrom: '2024-01-01T00:00:00Z',
    validUntil: '2024-04-01T00:00:00Z',
    daysUntilExpiry: 15,
    alertThresholdDays: 30,
    isAutoRenewal: true,
    status: 'expiring',
    assetIds: [1, 2],
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-15T00:00:00Z',
  },
  {
    id: 2,
    domain: 'api.example.com',
    issuer: 'DigiCert',
    subject: 'CN=api.example.com',
    serialNumber: '11:22:33:44:55:66:77:88:99:aa:bb:cc:dd:ee:ff:00',
    validFrom: '2024-01-01T00:00:00Z',
    validUntil: '2025-01-01T00:00:00Z',
    daysUntilExpiry: 350,
    alertThresholdDays: 30,
    isAutoRenewal: false,
    status: 'active',
    assetIds: [3],
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
  },
];

const certificateApi = {
  getCertificates: async () => ({ total: mockCertificates.length, items: mockCertificates }),
};

const CertificateList = () => {
  const [filter] = useState({
    expiringSoon: false,
  });

  const { data, isLoading } = useQuery({
    queryKey: ['certificates', filter],
    queryFn: () => certificateApi.getCertificates(),
  });

  const expiringCerts = data?.items.filter((c) => c.daysUntilExpiry <= c.alertThresholdDays) || [];

  const columns = [
    {
      title: '域名',
      dataIndex: 'domain',
      key: 'domain',
      render: (domain: string) => (
        <Space>
          <SafetyCertificateOutlined />
          {domain}
        </Space>
      ),
    },
    {
      title: '颁发者',
      dataIndex: 'issuer',
      key: 'issuer',
    },
    {
      title: '有效期至',
      dataIndex: 'validUntil',
      key: 'validUntil',
      render: (time: string) => new Date(time).toLocaleDateString(),
    },
    {
      title: '剩余天数',
      dataIndex: 'daysUntilExpiry',
      key: 'daysUntilExpiry',
      render: (days: number, record: Certificate) => {
        const percent = Math.max(0, Math.min(100, (days / 365) * 100));
        let status: 'success' | 'normal' | 'exception' = 'success';
        if (days <= 7) status = 'exception';
        else if (days <= record.alertThresholdDays) status = 'normal';

        return (
          <Space>
            <Progress
              percent={percent}
              size="small"
              status={status}
              style={{ width: 100 }}
              showInfo={false}
            />
            <span>{days}天</span>
          </Space>
        );
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const colorMap: Record<string, string> = {
          active: 'green',
          expiring: 'orange',
          expired: 'red',
          revoked: 'gray',
        };
        const labelMap: Record<string, string> = {
          active: '有效',
          expiring: '即将过期',
          expired: '已过期',
          revoked: '已吊销',
        };
        return <Tag color={colorMap[status]}>{labelMap[status]}</Tag>;
      },
    },
    {
      title: '自动续期',
      dataIndex: 'isAutoRenewal',
      key: 'isAutoRenewal',
      render: (enabled: boolean) => (
        <Tag color={enabled ? 'green' : 'default'}>{enabled ? '是' : '否'}</Tag>
      ),
    },
  ];

  return (
    <div>
      <h1>证书管理</h1>

      {expiringCerts.length > 0 && (
        <Alert
          message={`有 ${expiringCerts.length} 个证书即将过期`}
          description="请及时更新证书以避免服务中断"
          type="warning"
          showIcon
          style={{ marginBottom: 24 }}
        />
      )}

      <Card style={{ marginBottom: 24 }}>
        <Space wrap>
          <Button type="primary" icon={<PlusOutlined />}>
            新增证书
          </Button>
        </Space>
      </Card>

      <Table
        columns={columns}
        dataSource={data?.items || []}
        rowKey="id"
        loading={isLoading}
        pagination={{
          total: data?.total || 0,
          showSizeChanger: true,
          showTotal: (total) => `共 ${total} 条`,
        }}
      />
    </div>
  );
};

export default CertificateList;
