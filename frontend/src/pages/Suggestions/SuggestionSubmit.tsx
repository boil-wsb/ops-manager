import { useState } from 'react';
import { Card, Form, Input, Button, TreeSelect, Select, App, Alert, Modal, Typography, Space } from 'antd';
import { BulbOutlined, CopyOutlined } from '@ant-design/icons';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { suggestionApi } from '../../services/suggestion';
import { departmentApi, type DepartmentNode } from '../../services/departments';
import { userApi } from '../../services/users';
import type { User } from '../../types';
import { fuzzyFilterOption } from '../../utils/selectFilter';

const { TextArea } = Input;
const { Text, Paragraph } = Typography;

// 提交表单字段
interface SuggestionFormValues {
  content: string;
  highlights?: string;
  innovationIdeas?: string;
  departmentId?: number | null;
  assigneeUserId?: number | null;
}

// TreeSelect 数据节点（antd TreeSelect 使用 value 而非 key）
interface TreeSelectDataNode {
  value: number;
  title: string;
  children?: TreeSelectDataNode[];
  selectable?: boolean;
}

// 将部门树转为 TreeSelect 数据格式（仅保留有负责人的部门，顶层可选）
const buildTreeSelectData = (nodes: DepartmentNode[]): TreeSelectDataNode[] => {
  const result: TreeSelectDataNode[] = [];
  for (const node of nodes) {
    // 仅当本节点有负责人时才可选；子节点递归处理
    const children = node.children?.length ? buildTreeSelectData(node.children) : undefined;
    // 有负责人的节点可选；无负责人的节点若有可选子节点则作为分组展示（不可选自身）
    if (node.leaderId) {
      result.push({
        value: node.id,
        title: `${node.name}（负责人：${node.leaderFullName || node.leaderUsername}）`,
        children,
        selectable: true,
      });
    } else if (children && children.length > 0) {
      // 无负责人但有可选子部门：作为分组节点（不可选）
      result.push({
        value: node.id,
        title: node.name,
        children,
        selectable: false,
      });
    }
    // 无负责人且无可选子节点：跳过（隐藏）
  }
  return result;
};

const SuggestionSubmit = () => {
  const navigate = useNavigate();
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [successModalOpen, setSuccessModalOpen] = useState(false);
  const [queryCode, setQueryCode] = useState('');

  // 获取部门树
  const { data: deptTree } = useQuery({
    queryKey: ['departments', 'tree', 'for-suggestion'],
    queryFn: departmentApi.getTree,
  });

  // 获取用户列表（有飞书open_id的活跃用户）
  const { data: usersData } = useQuery({
    queryKey: ['users', 'for-suggestion'],
    queryFn: () => userApi.getUsers({ page: 1, page_size: 200, is_active: true }),
  });

  const submitMutation = useMutation({
    mutationFn: suggestionApi.submit,
    onSuccess: (data) => {
      setQueryCode(data.queryCode);
      setSuccessModalOpen(true);
      form.resetFields();
    },
    onError: (error: unknown) => {
      const errorMsg = error instanceof Error ? error.message : '提交失败';
      message.error(errorMsg);
    },
  });

  const handleSubmit = async (values: SuggestionFormValues) => {
    submitMutation.mutate({
      content: values.content,
      highlights: values.highlights || undefined,
      innovationIdeas: values.innovationIdeas || undefined,
      departmentId: values.departmentId ?? null,
      assigneeUserId: values.assigneeUserId ?? null,
    });
  };

  // 筛选有飞书open_id的用户作为指派人候选
  const userOptions = (usersData?.items || [])
    .filter((u: User) => u.feishuOpenId)
    .map((u: User) => ({
      value: u.id,
      label: u.fullName ? `${u.fullName} (${u.username})` : u.username,
    }));

  const treeSelectData = deptTree ? buildTreeSelectData(deptTree) : [];

  return (
    <div>
      <Card>
        <Alert
          message="匿名建议提交"
          description="您的建议将以匿名形式提交，审批人无法看到您的身份。提交成功后将获得一个查询码，请妥善保存用于查询进度。"
          type="info"
          showIcon
          style={{ marginBottom: 24 }}
        />

        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          requiredMark
        >
          <Form.Item
            name="content"
            label="意见内容"
            rules={[
              { required: true, message: '请输入意见内容' },
              { max: 2000, message: '内容不超过2000字' },
            ]}
          >
            <TextArea
              rows={4}
              placeholder="请详细描述您的意见或建议..."
              showCount
              maxLength={2000}
            />
          </Form.Item>

          <Form.Item
            name="highlights"
            label="项目服务亮点"
            rules={[{ max: 2000, message: '内容不超过2000字' }]}
          >
            <TextArea
              rows={3}
              placeholder="项目或服务中值得肯定的亮点（选填）"
              showCount
              maxLength={2000}
            />
          </Form.Item>

          <Form.Item
            name="innovationIdeas"
            label="创新/团队协助效能提高 idea"
            rules={[{ max: 2000, message: '内容不超过2000字' }]}
          >
            <TextArea
              rows={3}
              placeholder="创新想法或团队效能提升建议（选填）"
              showCount
              maxLength={2000}
            />
          </Form.Item>

          <Form.Item
            name="departmentId"
            label="指派部门"
            tooltip="选择需要处理的部门（仅显示已配置负责人的部门），对应负责人将收到飞书审批卡片"
          >
            <TreeSelect
              treeData={treeSelectData}
              placeholder="选择指派部门"
              showSearch
              treeNodeFilterProp="title"
              style={{ width: '100%' }}
              allowClear
              treeDefaultExpandAll
            />
          </Form.Item>

          <Form.Item
            name="assigneeUserId"
            label="指派人"
            tooltip="直接指派给具体人员，被指派人将收到飞书审批卡片"
          >
            <Select
              placeholder="选择指派人"
              options={userOptions}
              showSearch
              optionFilterProp="label"
              filterOption={fuzzyFilterOption}
              style={{ width: '100%' }}
              allowClear
            />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button
                type="primary"
                htmlType="submit"
                loading={submitMutation.isPending}
                icon={<BulbOutlined />}
              >
                提交建议
              </Button>
              <Button onClick={() => navigate('/suggestions/track')}>
                查询进度
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>

      <Modal
        title="提交成功"
        open={successModalOpen}
        onCancel={() => setSuccessModalOpen(false)}
        footer={[
          <Button key="track" type="primary" onClick={() => { setSuccessModalOpen(false); navigate('/suggestions/track'); }}>
            查询进度
          </Button>,
          <Button key="close" onClick={() => setSuccessModalOpen(false)}>
            关闭
          </Button>,
        ]}
      >
        <Alert
          message="建议已匿名提交成功"
          description="请保存以下查询码用于查询建议处理进度"
          type="success"
          showIcon
          style={{ marginBottom: 16 }}
        />
        <Card style={{ textAlign: 'center', background: '#f6ffed', borderColor: '#b7eb8f' }}>
          <Paragraph style={{ margin: 0 }}>
            <Text strong style={{ fontSize: 28, letterSpacing: 4, color: '#52c41a' }}>
              {queryCode}
            </Text>
            <Button
              type="text"
              icon={<CopyOutlined />}
              onClick={() => {
                navigator.clipboard.writeText(queryCode);
                message.success('查询码已复制');
              }}
            />
          </Paragraph>
        </Card>
      </Modal>
    </div>
  );
};

export default SuggestionSubmit;
