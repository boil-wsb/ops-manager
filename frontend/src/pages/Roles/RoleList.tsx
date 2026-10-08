import { useState, useEffect } from 'react';
import {
  Table,
  Button,
  Space,
  Tag,
  Card,
  Input,
  App,
  Popconfirm,
  Tooltip,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SafetyOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import { roleApi, type Role } from '../../services/permissions';
import RoleFormModal from './RoleFormModal';
import RolePermissionModal from './RolePermissionModal';

const { Search } = Input;

const RoleList = () => {
  const { message } = App.useApp();
  const [roles, setRoles] = useState<Role[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [searchText, setSearchText] = useState('');
  
  // Modal states
  const [formModalVisible, setFormModalVisible] = useState(false);
  const [permissionModalVisible, setPermissionModalVisible] = useState(false);
  const [editingRole, setEditingRole] = useState<Role | null>(null);
  const [selectedRole, setSelectedRole] = useState<Role | null>(null);

  const fetchRoles = async () => {
    setLoading(true);
    try {
      const response = await roleApi.getRoles({
        page: currentPage,
        page_size: pageSize,
      });
      setRoles(response.data.items);
      setTotal(response.data.total);
    } catch {
      message.error('获取角色列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRoles();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentPage, pageSize]);

  const handleCreate = () => {
    setEditingRole(null);
    setFormModalVisible(true);
  };

  const handleEdit = (role: Role) => {
    setEditingRole(role);
    setFormModalVisible(true);
  };

  const handleDelete = async (id: number) => {
    try {
      await roleApi.deleteRole(id);
      message.success('删除成功');
      fetchRoles();
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      message.error(err.response?.data?.detail || '删除失败');
    }
  };

  const handleManagePermissions = (role: Role) => {
    setSelectedRole(role);
    setPermissionModalVisible(true);
  };

  const handleFormSuccess = () => {
    setFormModalVisible(false);
    fetchRoles();
  };

  const handlePermissionSuccess = () => {
    setPermissionModalVisible(false);
    fetchRoles();
  };

  const filteredRoles = roles.filter(
    (role) =>
      role.name.toLowerCase().includes(searchText.toLowerCase()) ||
      role.description?.toLowerCase().includes(searchText.toLowerCase())
  );

  const columns = [
    {
      title: '角色名称',
      dataIndex: 'name',
      key: 'name',
      sorter: (a: Role, b: Role) => a.name.localeCompare(b.name),
      render: (text: string, record: Role) => (
        <Space>
          <span style={{ fontWeight: 500 }}>{text}</span>
          {record.isSystem && (
            <Tag color="blue" style={{ fontSize: '11px' }}>
              系统
            </Tag>
          )}
        </Space>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      sorter: (a: Role, b: Role) => (a.description || '').localeCompare(b.description || ''),
    },
    {
      title: '权限数量',
      dataIndex: 'permissionCount',
      key: 'permissionCount',
      width: 100,
      sorter: (a: Role, b: Role) => (a.permissionCount || 0) - (b.permissionCount || 0),
      render: (count: number) => (
        <Tag icon={<SafetyOutlined />} color="success">
          {count}
        </Tag>
      ),
    },
    {
      title: '用户数量',
      dataIndex: 'userCount',
      key: 'userCount',
      width: 100,
      sorter: (a: Role, b: Role) => (a.userCount || 0) - (b.userCount || 0),
      render: (count: number) => (
        <Tag icon={<TeamOutlined />} color="processing">
          {count}
        </Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'isActive',
      key: 'isActive',
      width: 80,
      sorter: (a: Role, b: Role) => (a.isActive === b.isActive ? 0 : a.isActive ? -1 : 1),
      render: (isActive: boolean) => (
        <Tag color={isActive ? 'success' : 'default'}>
          {isActive ? '启用' : '禁用'}
        </Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      key: 'createdAt',
      width: 180,
      sorter: (a: Role, b: Role) => {
        const aTime = a.createdAt ? new Date(a.createdAt).getTime() : 0;
        const bTime = b.createdAt ? new Date(b.createdAt).getTime() : 0;
        return aTime - bTime;
      },
      render: (text: string) => new Date(text).toLocaleString(),
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      render: (_: unknown, record: Role) => (
        <Space size="small">
          <Tooltip title="分配权限">
            <Button
              type="text"
              icon={<SafetyOutlined />}
              onClick={() => handleManagePermissions(record)}
            >
              权限
            </Button>
          </Tooltip>
          <Tooltip title="编辑">
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
              disabled={record.isSystem}
            />
          </Tooltip>
          <Popconfirm
            title="确认删除"
            description={`确定要删除角色 "${record.name}" 吗？`}
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
            disabled={!!record.isSystem || !!record.userCount}
          >
            <Tooltip title={record.isSystem ? '系统角色不能删除' : record.userCount ? '角色下还有用户' : '删除'}>
              <Button
                type="text"
                danger
                icon={<DeleteOutlined />}
                disabled={!!record.isSystem || !!record.userCount}
              />
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
              <Search
                placeholder="搜索角色名称或描述"
                allowClear
                onSearch={(value) => setSearchText(value)}
                onChange={(e) => setSearchText(e.target.value)}
                style={{ width: 250 }}
              />
              <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
                创建角色
              </Button>
            </Space>
          </div>
        }
        style={{ background: 'var(--bg-card)' }}
      >
        <Table
          columns={columns}
          dataSource={filteredRoles}
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

      {/* Role Form Modal */}
      <RoleFormModal
        visible={formModalVisible}
        onCancel={() => setFormModalVisible(false)}
        onSuccess={handleFormSuccess}
        role={editingRole}
      />

      {/* Role Permission Modal */}
      <RolePermissionModal
        visible={permissionModalVisible}
        onCancel={() => setPermissionModalVisible(false)}
        onSuccess={handlePermissionSuccess}
        role={selectedRole}
      />
    </div>
  );
};

export default RoleList;
