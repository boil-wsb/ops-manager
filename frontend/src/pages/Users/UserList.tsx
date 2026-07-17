import { useState } from 'react';
import { Table, Button, Input, Select, Tag, Space, Card, App, Popconfirm, Modal, Tooltip, Tree, Segmented, Empty } from 'antd';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { PlusOutlined, SearchOutlined, EditOutlined, DeleteOutlined, SendOutlined, SyncOutlined, UserOutlined, ApartmentOutlined, CrownOutlined } from '@ant-design/icons';
import { userApi } from '../../services/users';
import { departmentApi, type DepartmentNode } from '../../services/departments';
import { fuzzyFilterOption } from '../../utils/selectFilter';
import { PermissionGuard } from '../../components/PermissionGuard';
import StatusTag from '../../components/StatusTag';
import UserFormModal from './UserFormModal';
import type { User } from '../../types';

const { Option } = Select;

interface TreeDataItem {
  key: string;
  title: React.ReactNode;
  children?: TreeDataItem[];
  isLeaf?: boolean;
}

const UserList = () => {
  const queryClient = useQueryClient();
  const { message } = App.useApp();
  const [searchParams, setSearchParams] = useState({
    page: 1,
    page_size: 10,
    keyword: '',
    isActive: undefined as boolean | undefined,
  });
  const [modalOpen, setModalOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [messageModalOpen, setMessageModalOpen] = useState(false);
  const [messageUser, setMessageUser] = useState<User | null>(null);
  const [messageContent, setMessageContent] = useState('');
  const [viewMode, setViewMode] = useState<'list' | 'tree'>('list');
  const [leaderModalOpen, setLeaderModalOpen] = useState(false);
  const [editingDept, setEditingDept] = useState<DepartmentNode | null>(null);
  const [selectedLeaderId, setSelectedLeaderId] = useState<number | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['users', searchParams],
    queryFn: () => userApi.getUsers({
      page: searchParams.page,
      page_size: searchParams.page_size,
      keyword: searchParams.keyword,
      is_active: searchParams.isActive,
    }),
    enabled: viewMode === 'list',
  });

  const { data: deptTree, isLoading: isTreeLoading, refetch: refetchTree } = useQuery({
    queryKey: ['departments', 'tree'],
    queryFn: departmentApi.getTree,
    enabled: viewMode === 'tree',
  });

  const syncMutation = useMutation({
    mutationFn: departmentApi.syncFromFeishu,
    onSuccess: () => {
      message.success('同步已启动，请稍后刷新');
      setTimeout(() => refetchTree(), 3000);
    },
    onError: () => {
      message.error('同步启动失败');
    },
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

  const sendMessageMutation = useMutation({
    mutationFn: ({ id, msg }: { id: number; msg: string }) => userApi.sendMessage(id, msg),
    onSuccess: () => {
      message.success('消息发送成功');
      setMessageModalOpen(false);
      setMessageUser(null);
      setMessageContent('');
    },
    onError: (error: unknown) => {
      const errorMsg = error instanceof Error ? error.message : '消息发送失败';
      message.error(errorMsg);
    },
  });

  const setLeaderMutation = useMutation({
    mutationFn: ({ deptId, leaderId }: { deptId: number; leaderId: number | null }) =>
      departmentApi.setLeader(deptId, leaderId),
    onSuccess: () => {
      message.success('部门负责人设置成功');
      setLeaderModalOpen(false);
      setEditingDept(null);
      setSelectedLeaderId(null);
      refetchTree();
    },
    onError: (error: unknown) => {
      const errorMsg = error instanceof Error ? error.message : '部门负责人设置失败';
      message.error(errorMsg);
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

  const handleSendMessage = (user: User) => {
    setMessageUser(user);
    setMessageContent('');
    setMessageModalOpen(true);
  };

  const handleSendMessageConfirm = () => {
    if (!messageUser || !messageContent.trim()) return;
    sendMessageMutation.mutate({ id: messageUser.id, msg: messageContent.trim() });
  };

  const handleSetLeader = (dept: DepartmentNode) => {
    setEditingDept(dept);
    setSelectedLeaderId(dept.leaderId ?? null);
    setLeaderModalOpen(true);
  };

  const handleLeaderModalConfirm = () => {
    if (!editingDept) return;
    setLeaderMutation.mutate({ deptId: editingDept.id, leaderId: selectedLeaderId });
  };

  // 获取部门下可作为负责人的候选用户（活跃且有飞书open_id）
  const getLeaderCandidates = (dept: DepartmentNode | null) => {
    if (!dept) return [];
    return dept.users.filter((u) => u.isActive && u.feishuOpenId);
  };

  const columns = [
    {
      title: '用户名',
      dataIndex: 'username',
      key: 'username',
      sorter: (a: User, b: User) => a.username.localeCompare(b.username),
    },
    {
      title: '邮箱',
      dataIndex: 'email',
      key: 'email',
      sorter: (a: User, b: User) => (a.email || '').localeCompare(b.email || ''),
    },
    {
      title: '姓名',
      key: 'fullName',
      sorter: (a: User, b: User) => ((a as unknown as Record<string, unknown>).fullName as string || '').localeCompare((b as unknown as Record<string, unknown>).fullName as string || ''),
      render: (_: unknown, record: User) => {
        return (record as unknown as Record<string, unknown>).fullName || '-';
      },
    },
    {
      title: '状态',
      dataIndex: 'isActive',
      key: 'isActive',
      sorter: (a: User, b: User) => (a.isActive === b.isActive ? 0 : a.isActive ? -1 : 1),
      render: (isActive: boolean) => <StatusTag status={isActive ? 'active' : 'inactive'} type="user" />,
    },
    {
      title: '超级管理员',
      dataIndex: 'isSuperuser',
      key: 'isSuperuser',
      sorter: (a: User, b: User) => (a.isSuperuser === b.isSuperuser ? 0 : a.isSuperuser ? -1 : 1),
      render: (isSuperuser: boolean) => (
        <Tag color={isSuperuser ? 'purple' : 'default'}>
          {isSuperuser ? '是' : '否'}
        </Tag>
      ),
    },
    {
      title: '最后登录',
      key: 'lastLogin',
      sorter: (a: User, b: User) => {
        const aLogin = (a as unknown as Record<string, unknown>).lastLogin as string | undefined | null;
        const bLogin = (b as unknown as Record<string, unknown>).lastLogin as string | undefined | null;
        if (!aLogin && !bLogin) return 0;
        if (!aLogin) return 1;
        if (!bLogin) return -1;
        return new Date(aLogin).getTime() - new Date(bLogin).getTime();
      },
      render: (_: unknown, record: User) => {
        const lastLogin = (record as unknown as Record<string, unknown>).lastLogin as string | undefined | null;
        return lastLogin ? new Date(lastLogin).toLocaleString('zh-CN') : '-';
      },
    },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: User) => {
        const hasFeishuOpenId = !!(record as unknown as Record<string, unknown>).feishuOpenId;
        return (
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
            <PermissionGuard permissions="user:write">
              <Tooltip title={hasFeishuOpenId ? '发送飞书消息' : '该用户未绑定飞书账号'}>
                <Button
                  type="link"
                  icon={<SendOutlined />}
                  disabled={!hasFeishuOpenId}
                  onClick={() => handleSendMessage(record)}
                >
                  发送消息
                </Button>
              </Tooltip>
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
        );
      },
    },
  ];

  // 将部门树转为 Ant Design Tree 组件的 treeData
  const countAllUsers = (node: DepartmentNode): number => {
    return node.users.length + node.children.reduce((sum, child) => sum + countAllUsers(child), 0);
  };

  const buildTreeData = (nodes: DepartmentNode[]): TreeDataItem[] => {
    return nodes.map((node) => ({
      key: `dept-${node.id}`,
      title: (
        <span style={{ fontWeight: 500 }}>
          <ApartmentOutlined style={{ marginRight: 4 }} />
          {node.name}
          <Tag color="blue" style={{ marginLeft: 8, fontSize: 11 }}>{countAllUsers(node)}人</Tag>
          {node.leaderFullName ? (
            <Tag color="green" style={{ marginLeft: 4, fontSize: 11 }}>
              <CrownOutlined style={{ marginRight: 2 }} />
              负责人：{node.leaderFullName}
            </Tag>
          ) : (
            <Tag color="orange" style={{ marginLeft: 4, fontSize: 11 }}>未配置负责人</Tag>
          )}
          <PermissionGuard permissions="user:update">
            <Button
              type="link"
              size="small"
              icon={<CrownOutlined />}
              style={{ marginLeft: 4, padding: 0 }}
              onClick={(e) => {
                e.stopPropagation();
                handleSetLeader(node);
              }}
            >
              设置负责人
            </Button>
          </PermissionGuard>
        </span>
      ),
      children: [
        // 部门下的用户作为子节点
        ...node.users.map((user) => ({
          key: `user-${user.id}`,
          title: (
            <span>
              <UserOutlined style={{ marginRight: 4, color: '#1890ff' }} />
              {user.fullName || user.username}
              {user.email && <span style={{ color: '#999', marginLeft: 8, fontSize: 12 }}>{user.email}</span>}
              {!user.isActive && <Tag color="red" style={{ marginLeft: 4, fontSize: 11 }}>禁用</Tag>}
              {user.feishuOpenId && (
                <Tooltip title="发送飞书消息">
                  <Button
                    type="link"
                    size="small"
                    icon={<SendOutlined />}
                    style={{ marginLeft: 4, padding: 0 }}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleSendMessage({
                        id: user.id,
                        username: user.username,
                        email: user.email,
                        fullName: user.fullName,
                        feishuOpenId: user.feishuOpenId,
                      } as unknown as User);
                    }}
                  />
                </Tooltip>
              )}
            </span>
          ),
          isLeaf: true,
        })),
        // 递归子部门
        ...buildTreeData(node.children),
      ],
    }));
  };

  return (
    <div>
      <Card style={{ marginBottom: 24 }}>
        <Space wrap>
          <Segmented
            value={viewMode}
            onChange={(val) => setViewMode(val as 'list' | 'tree')}
            options={[
              { label: '列表视图', value: 'list', icon: <UserOutlined /> },
              { label: '组织架构', value: 'tree', icon: <ApartmentOutlined /> },
            ]}
          />
          {viewMode === 'list' && (
            <>
              <Input.Search
                placeholder="搜索用户名/邮箱/姓名"
                prefix={<SearchOutlined />}
                value={searchParams.keyword}
                onChange={(e) => setSearchParams({ ...searchParams, keyword: e.target.value, page: 1 })}
                style={{ width: 250 }}
                allowClear
              />
              <Select
                placeholder="状态"
                value={searchParams.isActive}
                onChange={(value) => setSearchParams({ ...searchParams, isActive: value, page: 1 })}
                style={{ width: 120 }}
                allowClear
                showSearch
                filterOption={fuzzyFilterOption}
              >
                <Option value={true}>启用</Option>
                <Option value={false}>禁用</Option>
              </Select>
            </>
          )}
          {viewMode === 'tree' && (
            <PermissionGuard permissions="user:write">
              <Button
                icon={<SyncOutlined spin={syncMutation.isPending} />}
                onClick={() => syncMutation.mutate()}
                loading={syncMutation.isPending}
              >
                同步飞书组织架构
              </Button>
            </PermissionGuard>
          )}
          {viewMode === 'list' && (
            <PermissionGuard permissions="user:write">
              <Button type="primary" icon={<PlusOutlined />} onClick={handleAddUser}>
                新增用户
              </Button>
            </PermissionGuard>
          )}
        </Space>
      </Card>

      {viewMode === 'list' ? (
        <Table
          columns={columns}
          dataSource={data?.items || []}
          rowKey="id"
          loading={isLoading}
          pagination={{
            current: searchParams.page,
            pageSize: searchParams.page_size,
            total: data?.total || 0,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 条`,
            onChange: (page, pageSize) => {
              setSearchParams((prev) => ({ ...prev, page, page_size: pageSize }));
            },
          }}
        />
      ) : (
        <Card loading={isTreeLoading}>
          {deptTree && deptTree.length > 0 ? (
            <Tree
              treeData={buildTreeData(deptTree)}
              defaultExpandAll
              showLine
              showIcon={false}
            />
          ) : (
            <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
              暂无组织架构数据，请点击"同步飞书组织架构"按钮获取
            </div>
          )}
        </Card>
      )}

      <UserFormModal
        open={modalOpen}
        onClose={handleModalClose}
        user={editingUser}
      />

      <Modal
        title={`发送消息给 ${messageUser ? ((messageUser as unknown as Record<string, unknown>).fullName || messageUser.username) : ''}`}
        open={messageModalOpen}
        onOk={handleSendMessageConfirm}
        onCancel={() => {
          setMessageModalOpen(false);
          setMessageUser(null);
          setMessageContent('');
        }}
        okText="发送"
        cancelText="取消"
        confirmLoading={sendMessageMutation.isPending}
        okButtonProps={{ disabled: !messageContent.trim() }}
      >
        <Input.TextArea
          value={messageContent}
          onChange={(e) => setMessageContent(e.target.value)}
          placeholder="请输入消息内容"
          autoSize={{ minRows: 3, maxRows: 8 }}
          maxLength={4000}
          showCount
        />
      </Modal>

      <Modal
        title={`设置部门负责人 - ${editingDept?.name || ''}`}
        open={leaderModalOpen}
        onOk={handleLeaderModalConfirm}
        onCancel={() => {
          setLeaderModalOpen(false);
          setEditingDept(null);
          setSelectedLeaderId(null);
        }}
        okText="确定"
        cancelText="取消"
        confirmLoading={setLeaderMutation.isPending}
      >
        {getLeaderCandidates(editingDept).length > 0 ? (
          <>
            <p style={{ marginBottom: 8, color: '#666' }}>
              选择本部门下已绑定飞书账号的活跃成员作为负责人（可清空以移除负责人）：
            </p>
            <Select
              style={{ width: '100%' }}
              placeholder="请选择负责人"
              value={selectedLeaderId}
              onChange={(value: number | null) => setSelectedLeaderId(value ?? null)}
              allowClear
              showSearch
              filterOption={fuzzyFilterOption}
            >
              {getLeaderCandidates(editingDept).map((user) => (
                <Option key={user.id} value={user.id}>
                  {user.fullName || user.username}
                </Option>
              ))}
            </Select>
          </>
        ) : (
          <Empty
            description="该部门暂无可用成员（需有飞书账号），请先同步或添加成员"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        )}
      </Modal>
    </div>
  );
};

export default UserList;
