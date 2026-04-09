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
  Form,
  Select,
  Switch,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  UserOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import { notificationGroupApi, type NotificationGroup, type NotificationGroupCreate, type NotificationGroupUpdate } from '../../services/notification_group';
import { userApi } from '../../services/users';
import type { User } from '../../types';

const { Search } = Input;

const NOTIFICATION_TYPE_OPTIONS = [
  { value: 'it_feedback_created', label: 'IT反馈创建通知' },
  { value: 'it_feedback_resolved', label: 'IT反馈解决通知' },
];

const NotificationGroupList = () => {
  const [groups, setGroups] = useState<NotificationGroup[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [searchText, setSearchText] = useState('');
  const [notificationTypeFilter, setNotificationTypeFilter] = useState<string | null>(null);

  const [modalVisible, setModalVisible] = useState(false);
  const [editingGroup, setEditingGroup] = useState<NotificationGroup | null>(null);
  const [form] = Form.useForm();

  const [memberModalVisible, setMemberModalVisible] = useState(false);
  const [selectedGroup, setSelectedGroup] = useState<NotificationGroup | null>(null);
  const [allUsers, setAllUsers] = useState<User[]>([]);
  const [selectedUserIds, setSelectedUserIds] = useState<number[]>([]);
  const [memberLoading, setMemberLoading] = useState(false);

  const fetchGroups = useCallback(async () => {
    setLoading(true);
    try {
      const response = await notificationGroupApi.getGroups({
        page: currentPage,
        pageSize: pageSize,
        notificationType: notificationTypeFilter || undefined,
      });
      setGroups(response.items);
      setTotal(response.total);
    } catch {
      message.error('获取通知组列表失败');
    } finally {
      setLoading(false);
    }
  }, [currentPage, pageSize, notificationTypeFilter]);

  useEffect(() => {
    fetchGroups();
  }, [fetchGroups]);

  const fetchAllUsers = useCallback(async () => {
    try {
      const response = await userApi.getUsers({ page_size: 100 });
      setAllUsers(response.items);
    } catch {
      message.error('获取用户列表失败');
    }
  }, []);

  const handleCreate = () => {
    setEditingGroup(null);
    form.resetFields();
    form.setFieldsValue({ isActive: true });
    setModalVisible(true);
  };

  const handleEdit = (group: NotificationGroup) => {
    setEditingGroup(group);
    form.setFieldsValue({
      name: group.name,
      description: group.description,
      notificationType: group.notificationType,
      isActive: group.isActive ?? true,
    });
    setModalVisible(true);
  };

  const handleDelete = async (id: number) => {
    try {
      await notificationGroupApi.deleteGroup(id);
      message.success('删除成功');
      fetchGroups();
    } catch {
      message.error('删除失败');
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      if (editingGroup) {
        await notificationGroupApi.updateGroup(editingGroup.id, values as NotificationGroupUpdate);
        message.success('更新成功');
      } else {
        await notificationGroupApi.createGroup(values as NotificationGroupCreate);
        message.success('创建成功');
      }
      setModalVisible(false);
      fetchGroups();
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : '操作失败';
      message.error(errorMessage);
    }
  };

  const handleManageMembers = (group: NotificationGroup) => {
    setSelectedGroup(group);
    setSelectedUserIds(group.members.map((m) => m.id));
    fetchAllUsers();
    setMemberModalVisible(true);
  };

  const handleAddMembers = async () => {
    if (!selectedGroup) return;
    setMemberLoading(true);
    try {
      const currentMemberIds = selectedGroup.members.map((m) => m.id);
      const toAdd = selectedUserIds.filter((id) => !currentMemberIds.includes(id));
      const toRemove = currentMemberIds.filter((id) => !selectedUserIds.includes(id));

      for (const userId of toAdd) {
        await notificationGroupApi.addMember(selectedGroup.id, userId);
      }
      for (const userId of toRemove) {
        await notificationGroupApi.removeMember(selectedGroup.id, userId);
      }

      message.success('成员更新成功');
      setMemberModalVisible(false);
      fetchGroups();
    } catch {
      message.error('更新成员失败');
    } finally {
      setMemberLoading(false);
    }
  };

  const filteredGroups = groups.filter(
    (group) =>
      group.name.toLowerCase().includes(searchText.toLowerCase()) ||
      (group.description && group.description.toLowerCase().includes(searchText.toLowerCase()))
  );

  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      width: 150,
      sorter: (a: NotificationGroup, b: NotificationGroup) => a.name.localeCompare(b.name),
      render: (text: string) => <span style={{ fontWeight: 500 }}>{text}</span>,
    },
    {
      title: '通知类型',
      dataIndex: 'notificationType',
      key: 'notificationType',
      width: 150,
      sorter: (a: NotificationGroup, b: NotificationGroup) => (a.notificationType || '').localeCompare(b.notificationType || ''),
      render: (type: string) => {
        const option = NOTIFICATION_TYPE_OPTIONS.find((opt) => opt.value === type);
        return <Tag color="blue">{option?.label || type}</Tag>;
      },
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      sorter: (a: NotificationGroup, b: NotificationGroup) => (a.description || '').localeCompare(b.description || ''),
      render: (text: string) => text || '-',
    },
    {
      title: '成员',
      dataIndex: 'members',
      key: 'members',
      width: 200,
      sorter: (a: NotificationGroup, b: NotificationGroup) => (a.members?.length || 0) - (b.members?.length || 0),
      render: (members: NotificationGroup['members']) => {
        if (!members || members.length === 0) {
          return <Tag color="default">暂无成员</Tag>;
        }
        return (
          <Space size={4} wrap>
            {members.slice(0, 3).map((member) => (
              <Tag key={member.id} icon={<UserOutlined />}>
                {member.fullName || member.username}
              </Tag>
            ))}
            {members.length > 3 && (
              <Tag color="orange">+{members.length - 3}</Tag>
            )}
          </Space>
        );
      },
    },
    {
      title: '状态',
      dataIndex: 'isActive',
      key: 'isActive',
      width: 80,
      sorter: (a: NotificationGroup, b: NotificationGroup) => (a.isActive === b.isActive ? 0 : a.isActive ? -1 : 1),
      render: (isActive: boolean) => (
        <Tag color={isActive ? 'success' : 'default'}>{isActive ? '启用' : '禁用'}</Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 180,
      render: (_: unknown, record: NotificationGroup) => (
        <Space size="small">
          <Tooltip title="管理成员">
            <Button
              type="text"
              icon={<TeamOutlined />}
              onClick={() => handleManageMembers(record)}
            />
          </Tooltip>
          <Tooltip title="编辑">
            <Button type="text" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          </Tooltip>
          <Popconfirm
            title="确认删除"
            description={`确定要删除通知组 "${record.name}" 吗？`}
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
              <Select
                placeholder="筛选通知类型"
                allowClear
                style={{ width: 180 }}
                value={notificationTypeFilter}
                onChange={(value) => setNotificationTypeFilter(value)}
              >
                {NOTIFICATION_TYPE_OPTIONS.map((opt) => (
                  <Select.Option key={opt.value} value={opt.value}>
                    {opt.label}
                  </Select.Option>
                ))}
              </Select>
              <Search
                placeholder="搜索名称或描述"
                allowClear
                onSearch={(value) => setSearchText(value)}
                onChange={(e) => setSearchText(e.target.value)}
                style={{ width: 200 }}
              />
              <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
                新增通知组
              </Button>
            </Space>
          </div>
        }
        style={{ background: 'var(--bg-card)' }}
      >
        <Table
          columns={columns}
          dataSource={filteredGroups}
          rowKey="id"
          loading={loading}
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
        title={editingGroup ? '编辑通知组' : '新增通知组'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => setModalVisible(false)}
        width={500}
        okText="保存"
        cancelText="取消"
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="name"
            label="名称"
            rules={[{ required: true, message: '请输入通知组名称' }]}
          >
            <Input placeholder="通知组名称" />
          </Form.Item>
          <Form.Item
            name="notificationType"
            label="通知类型"
            rules={[{ required: true, message: '请选择通知类型' }]}
          >
            <Select placeholder="选择通知类型">
              {NOTIFICATION_TYPE_OPTIONS.map((opt) => (
                <Select.Option key={opt.value} value={opt.value}>
                  {opt.label}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} placeholder="通知组描述（可选）" />
          </Form.Item>
          <Form.Item name="isActive" label="启用状态" valuePropName="checked">
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={`管理通知组成员 - ${selectedGroup?.name}`}
        open={memberModalVisible}
        onOk={handleAddMembers}
        onCancel={() => setMemberModalVisible(false)}
        width={600}
        okText="保存"
        cancelText="取消"
        confirmLoading={memberLoading}
      >
        <div style={{ marginTop: 16 }}>
          <p style={{ marginBottom: 8, color: '#666' }}>
            选择接收此通知组通知的用户（已同步飞书且有 feishu_open_id 的用户将收到通知）
          </p>
          <Select
            mode="multiple"
            placeholder="选择用户"
            style={{ width: '100%' }}
            value={selectedUserIds}
            onChange={setSelectedUserIds}
            options={allUsers.map((user) => ({
              value: user.id,
              label: `${user.fullName || user.username}${user.feishuOpenId ? ' ✓' : ' (无飞书)'}`,
            }))}
          />
        </div>
      </Modal>
    </div>
  );
};

export default NotificationGroupList;