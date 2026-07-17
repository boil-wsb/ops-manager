import { useState } from 'react';
import { Card, Input, Button, Alert, Descriptions, Tag, Steps, Spin, Empty, Select, Typography } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { suggestionApi } from '../../services/suggestion';
import type { MySuggestionCode } from '../../services/suggestion';
import { fuzzyFilterOption } from '../../utils/selectFilter';

const { Text } = Typography;

const statusConfig: Record<string, { color: string; text: string }> = {
  pending: { color: 'orange', text: '待审批' },
  approved: { color: 'blue', text: '已审批' },
  archived: { color: 'green', text: '已存档' },
  rejected: { color: 'default', text: '已驳回' },
};

const SuggestionTrack = () => {
  const [queryCode, setQueryCode] = useState('');
  const [trackTrigger, setTrackTrigger] = useState(0);

  // 获取当前用户的历史查询码列表
  const { data: myCodesData, isLoading: codesLoading } = useQuery({
    queryKey: ['suggestions', 'my-codes'],
    queryFn: suggestionApi.getMyCodes,
  });

  // 查询进度（手动触发）
  const { data, isLoading, isError } = useQuery({
    queryKey: ['suggestions', 'track', queryCode, trackTrigger],
    queryFn: () => suggestionApi.track(queryCode),
    enabled: trackTrigger > 0 && !!queryCode.trim(),
  });

  const handleTrack = () => {
    if (queryCode.trim()) {
      setTrackTrigger((n) => n + 1);
    }
  };

  const handleSelectCode = (value: string) => {
    setQueryCode(value);
    if (value) {
      setTrackTrigger((n) => n + 1);
    }
  };

  const getStatusStep = (status: string): number => {
    switch (status) {
      case 'pending': return 0;
      case 'approved': return 1;
      case 'archived': return 2;
      case 'rejected': return 1;
      default: return 0;
    }
  };

  const status = data?.status;
  const statusCfg = status ? (statusConfig[status] || { color: 'default', text: status }) : null;
  const myCodes = myCodesData?.items || [];

  return (
    <div style={{ maxWidth: 700, margin: '0 auto' }}>
      <Card>
        <Alert
          message="匿名建议进度查询"
          description="请选择或输入您提交建议时获得的6位查询码进行进度查询"
          type="info"
          showIcon
          style={{ marginBottom: 24 }}
        />

        {/* 我的历史查询码下拉选择 */}
        <div style={{ marginBottom: 16 }}>
          <Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>
            我的历史建议查询码：
          </Text>
          {codesLoading ? (
            <Spin size="small" />
          ) : myCodes.length > 0 ? (
            <Select
              placeholder="选择我提交过的建议查询码"
              style={{ width: '100%' }}
              onChange={handleSelectCode}
              value={queryCode || undefined}
              allowClear
              showSearch
              filterOption={fuzzyFilterOption}
              optionFilterProp="label"
              options={myCodes.map((item: MySuggestionCode) => ({
                value: item.queryCode,
                label: `${item.queryCode} | ${statusConfig[item.status]?.text || item.status} | ${(item.contentPreview || '').slice(0, 30)}`,
              }))}
            />
          ) : (
            <Empty
              description="您还没有提交过建议"
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              style={{ margin: '8px 0' }}
            />
          )}
        </div>

        {/* 手动输入查询码 */}
        <Input.Group compact style={{ marginBottom: 24 }}>
          <Input
            style={{ width: '70%' }}
            placeholder="或手动输入6位查询码"
            value={queryCode}
            onChange={(e) => setQueryCode(e.target.value.toUpperCase())}
            onPressEnter={handleTrack}
            maxLength={6}
            prefix={<SearchOutlined />}
          />
          <Button
            type="primary"
            style={{ width: '30%' }}
            onClick={handleTrack}
            loading={isLoading}
            disabled={!queryCode.trim()}
          >
            查询
          </Button>
        </Input.Group>

        {isLoading && (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin size="large" />
          </div>
        )}

        {isError && !isLoading && queryCode && (
          <Alert
            message="查询失败"
            description="查询码无效、不存在或非您提交的建议，请检查后重试"
            type="error"
            showIcon
          />
        )}

        {data && !isLoading && (
          <div>
            <div style={{ textAlign: 'center', marginBottom: 24 }}>
              {statusCfg && (
                <Tag color={statusCfg.color} style={{ fontSize: 16, padding: '8px 24px' }}>
                  {statusCfg.text}
                </Tag>
              )}
            </div>

            {status === 'rejected' ? (
              <Alert
                message="建议已驳回"
                description={data.rejectReason || '无驳回原因'}
                type="error"
                showIcon
                style={{ marginBottom: 16 }}
              />
            ) : (
              <Steps
                current={getStatusStep(status || '')}
                style={{ marginBottom: 24 }}
                items={[
                  { title: '提交成功', description: new Date(data.createdAt).toLocaleString('zh-CN') },
                  { title: '部门审批', description: status === 'approved' || status === 'archived' ? '已通过' : '处理中' },
                  { title: '市场部存档', description: status === 'archived' ? '已存档' : '待处理' },
                ]}
              />
            )}

            <Descriptions bordered column={1}>
              <Descriptions.Item label="提交时间">
                {new Date(data.createdAt).toLocaleString('zh-CN')}
              </Descriptions.Item>
              {data.archivedAt && (
                <Descriptions.Item label="存档时间">
                  {new Date(data.archivedAt).toLocaleString('zh-CN')}
                </Descriptions.Item>
              )}
              {data.marketResult && (
                <Descriptions.Item label="执行结果">
                  {data.marketResult}
                </Descriptions.Item>
              )}
              {data.rejectReason && (
                <Descriptions.Item label="驳回原因">
                  {data.rejectReason}
                </Descriptions.Item>
              )}
            </Descriptions>
          </div>
        )}

        {!data && !isLoading && !isError && (
          <Empty description="请选择或输入查询码查询进度" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        )}
      </Card>
    </div>
  );
};

export default SuggestionTrack;
