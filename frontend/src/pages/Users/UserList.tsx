import { useState } from 'react';
import { Table, Button, Input, Select, Tag, Space, Card, App, Popconfirm } from 'antd';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { PlusOutlined, SearchOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { userApi } from '../../services/users';
import { PermissionGuard } from '../../components/PermissionGuard';
import StatusTag from '../../components/StatusTag';
import UserFormModal from './UserFormModal';
import type { User } from '../../types';

const { Option } = Select;

const UserList = () => {
  const queryClient = useQueryClient();
  const { message } = App.useApp();
  const [searchParams, setSearchParams] = useState({
    keyword: '',
    isActive: undefined as boolean | undefined,
  });
  const [modalOpen, setModalOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['users', searchParams],
    queryFn: () => userApi.getUsers(searchParams),
  });

  const deleteMutation = useMutation({
    mutationFn: userApi.deleteUser,
    onSuccess: () => {
      message.success('用户删除成功');
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
    onError: () => {
      message.error('用户删除失败');
    },
  });

  const handleAddUser = () => {
    setEditingUser(null);
    setModalOpen(true);
  };

  const handleEditUser = (user: User) => {
    setEditingUser(user);
    setModalOpen(true);
  };

  const handleModalClose = () => {
    setModalOpen(false);
    setEditingUser(null);
  };

  const columns = [
    {
      title: '用户名',
      dataIndex: 'username',
      key: 'username',
    },
    {
      title: '邮箱',
      dataIndex: 'email',
      key: 'email',
    },
    {
      title: '姓名',
      key: 'fullName',
      render: (_: unknown, record: User) => {
        return (record as unknown as Record<string, unknown>).fullName || '-';
      },
    },
    {
      title: '状态',
      dataIndex: 'isActive',
      key: 'isActive',
      render: (isActive: boolean) => <StatusTag status={isActive ? 'active' : 'inactive'} type="user" />,
    },
    {
      title: '超级管理员',
      dataIndex: 'isSuperuser',
      key: 'isSuperuser',
      render: (isSuperuser: boolean) => (
        <Tag color={isSuperuser ? 'purple' : 'default'}>
          {isSuperuser ? '是' : '否'}
        </Tag>
      ),
    },
    {
      title: '最后登录',
      key: 'lastLogin',
      render: (_: unknown, record: User) => {
        const lastLogin = (record as unknown as Record<string, unknown>).lastLogin as string | undefined | null;
        return lastLogin ? new Date(lastLogin).toLocaleString('zh-CN') : '-';
      },
    },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: User) => (
        <Space size="small">
          <PermissionGuard permissions="user:write">
            <Button
              type="link"
              icon={<EditOutlined />}
              onClick={() => handleEditUser(record)}
            >
              编辑
            </Button>
          </PermissionGuard>
          <PermissionGuard permissions="user:delete">
            <Popconfirm
              title="确定要删除这个用户吗？"
              onConfirm={() => deleteMutation.mutate(record.id)}
              okText="确定"
              cancelText="取消"
            >
              <Button type="link" danger icon={<DeleteOutlined />}>
                删除
              </Button>
            </Popconfirm>
          </PermissionGuard>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Card style={{ marginBottom: 24 }}>
        <Space wrap>
          <Input
            placeholder="搜索用户名/邮箱/姓名"
            prefix={<SearchOutlined />}
            value={searchParams.keyword}
            onChange={(e) => setSearchParams({ ...searchParams, keyword: e.target.value })}
            style={{ width: 250 }}
            allowClear
          />
          <Select
            placeholder="状态"
            value={searchParams.isActive}
            onChange={(value) => setSearchParams({ ...searchParams, isActive: value })}
            style={{ width: 120 }}
            allowClear
          >
            <Option value={true}>启用</Option>
            <Option value={false}>禁用</Option>
          </Select>
          <PermissionGuard permissions="user:write">
            <Button type="primary" icon={<PlusOutlined />} onClick={handleAddUser}>
              新增用户
            </Button>
          </PermissionGuard>
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
          showQuickJumper: true,
          showTotal: (total) => `共 ${total} 条`,
        }}
      />

      <UserFormModal
        open={modalOpen}
        onClose={handleModalClose}
        user={editingUser}
      />
    </div>
  );
};

export default UserList;
