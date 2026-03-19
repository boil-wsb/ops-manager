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
  Typography,
  Tooltip,
  Modal,
  Form,
  Select,
  InputNumber,
  Switch,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  LinkOutlined,
  MonitorOutlined,
  CloudUploadOutlined,
  DatabaseOutlined,
  DesktopOutlined,
  CloudOutlined,
  SettingOutlined,
  DashboardOutlined,
  SafetyOutlined,
  ApiOutlined,
} from '@ant-design/icons';
import { navigationApi, type NavigationLink, type NavigationLinkCreate, type NavigationLinkUpdate } from '../../services/navigation';

const { Title } = Typography;
const { Search } = Input;

interface Role {
  id: number;
  name: string;
}

const iconMap: Record<string, React.ReactNode> = {
  MonitorOutlined: <MonitorOutlined />,
  CloudUploadOutlined: <CloudUploadOutlined />,
  LinkOutlined: <LinkOutlined />,
  DatabaseOutlined: <DatabaseOutlined />,
  DesktopOutlined: <DesktopOutlined />,
  CloudOutlined: <CloudOutlined />,
  SettingOutlined: <SettingOutlined />,
  DashboardOutlined: <DashboardOutlined />,
  SafetyOutlined: <SafetyOutlined />,
  ApiOutlined: <ApiOutlined />,
};

const iconOptions = [
  { value: 'MonitorOutlined', icon: <MonitorOutlined /> },
  { value: 'CloudUploadOutlined', icon: <CloudUploadOutlined /> },
  { value: 'LinkOutlined', icon: <LinkOutlined /> },
  { value: 'DatabaseOutlined', icon: <DatabaseOutlined /> },
  { value: 'DesktopOutlined', icon: <DesktopOutlined /> },
  { value: 'CloudOutlined', icon: <CloudOutlined /> },
  { value: 'SettingOutlined', icon: <SettingOutlined /> },
  { value: 'DashboardOutlined', icon: <DashboardOutlined /> },
  { value: 'SafetyOutlined', icon: <SafetyOutlined /> },
  { value: 'ApiOutlined', icon: <ApiOutlined /> },
];

const NavigationList = () => {
  const [links, setLinks] = useState<NavigationLink[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [searchText, setSearchText] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null);

  const [modalVisible, setModalVisible] = useState(false);
  const [editingLink, setEditingLink] = useState<NavigationLink | null>(null);
  const [form] = Form.useForm();

  const fetchLinks = useCallback(async () => {
    setLoading(true);
    try {
      const response = await navigationApi.getLinks({
        page: currentPage,
        page_size: pageSize,
        category: categoryFilter || undefined,
      });
      setLinks(response.items);
      setTotal(response.total);
    } catch {
      message.error('获取导航链接列表失败');
    } finally {
      setLoading(false);
    }
  }, [currentPage, pageSize, categoryFilter]);

  useEffect(() => {
    fetchLinks();
  }, [fetchLinks]);

  const handleCreate = () => {
    setEditingLink(null);
    form.resetFields();
    form.setFieldsValue({ sortOrder: 0, isActive: true, restrictToCurrentRole: true });
    setModalVisible(true);
  };

  const handleEdit = (link: NavigationLink) => {
    setEditingLink(link);
    const hasRoles = link.roles && link.roles.length > 0;
    form.setFieldsValue({
      category: link.category,
      name: link.name,
      url: link.url,
      icon: link.icon,
      description: link.description,
      sortOrder: link.sortOrder,
      isActive: link.isActive ?? true,
      restrictToCurrentRole: hasRoles,
    });
    setModalVisible(true);
  };

  const handleDelete = async (id: number) => {
    try {
      await navigationApi.deleteLink(id);
      message.success('删除成功');
      fetchLinks();
    } catch {
      message.error('删除失败');
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      if (editingLink) {
        await navigationApi.updateLink(editingLink.id, values as NavigationLinkUpdate);
        message.success('更新成功');
      } else {
        await navigationApi.createLink(values as NavigationLinkCreate);
        message.success('创建成功');
      }
      setModalVisible(false);
      fetchLinks();
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : '操作失败';
      message.error(errorMessage);
    }
  };

  const filteredLinks = links.filter(
    (link) =>
      link.name.toLowerCase().includes(searchText.toLowerCase()) ||
      link.url.toLowerCase().includes(searchText.toLowerCase()) ||
      link.category.toLowerCase().includes(searchText.toLowerCase())
  );

  const categories = [...new Set(links.map((link) => link.category))];

  const columns = [
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      width: 100,
      render: (text: string) => <Tag color="blue">{text}</Tag>,
    },
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      width: 150,
      render: (text: string) => <span style={{ fontWeight: 500 }}>{text}</span>,
    },
    {
      title: '链接地址',
      dataIndex: 'url',
      key: 'url',
      ellipsis: true,
      render: (text: string) => (
        <a href={text} target="_blank" rel="noopener noreferrer">
          <LinkOutlined style={{ marginRight: 4 }} />
          {text}
        </a>
      ),
    },
    {
      title: '图标',
      dataIndex: 'icon',
      key: 'icon',
      width: 80,
      align: 'center' as const,
      render: (iconName: string) => {
        if (!iconName) return '-';
        const icon = iconMap[iconName];
        return icon ? <span style={{ fontSize: 18 }}>{icon}</span> : '-';
      },
    },
    {
      title: '可见范围',
      dataIndex: 'roles',
      key: 'roles',
      width: 150,
      render: (rolesList: Role[]) => {
        if (!rolesList || rolesList.length === 0) {
          return <Tag color="green">全部可见</Tag>;
        }
        return (
          <Space size={4} wrap>
            {rolesList.map((role) => (
              <Tag key={role.id} color="orange">
                {role.name}
              </Tag>
            ))}
          </Space>
        );
      },
    },
    {
      title: '排序',
      dataIndex: 'sortOrder',
      key: 'sortOrder',
      width: 80,
      align: 'center' as const,
    },
    {
      title: '状态',
      dataIndex: 'isActive',
      key: 'isActive',
      width: 80,
      render: (isActive: boolean) => (
        <Tag color={isActive ? 'success' : 'default'}>{isActive ? '启用' : '禁用'}</Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_: unknown, record: NavigationLink) => (
        <Space size="small">
          <Tooltip title="编辑">
            <Button type="text" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          </Tooltip>
          <Popconfirm
            title="确认删除"
            description={`确定要删除导航链接 "${record.name}" 吗？`}
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
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Title level={4} style={{ margin: 0 }}>
              导航链接管理
            </Title>
            <Space>
              <Select
                placeholder="筛选分类"
                allowClear
                style={{ width: 150 }}
                value={categoryFilter}
                onChange={(value) => setCategoryFilter(value)}
              >
                {categories.map((cat) => (
                  <Select.Option key={cat} value={cat}>
                    {cat}
                  </Select.Option>
                ))}
              </Select>
              <Search
                placeholder="搜索名称或链接"
                allowClear
                onSearch={(value) => setSearchText(value)}
                onChange={(e) => setSearchText(e.target.value)}
                style={{ width: 200 }}
              />
              <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
                新增链接
              </Button>
            </Space>
          </div>
        }
        style={{ background: 'var(--bg-card)' }}
      >
        <Table
          columns={columns}
          dataSource={filteredLinks}
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
        title={editingLink ? '编辑导航链接' : '新增导航链接'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => setModalVisible(false)}
        width={600}
        okText="保存"
        cancelText="取消"
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="category"
            label="分类"
            rules={[{ required: true, message: '请输入分类名称' }]}
          >
            <Input placeholder="如：监控、工具、文档等" />
          </Form.Item>
          <Form.Item
            name="name"
            label="名称"
            rules={[{ required: true, message: '请输入链接名称' }]}
          >
            <Input placeholder="链接显示名称" />
          </Form.Item>
          <Form.Item
            name="url"
            label="链接地址"
            rules={[
              { required: true, message: '请输入链接地址' },
              { type: 'url', message: '请输入有效的URL地址' },
            ]}
          >
            <Input placeholder="https://example.com" />
          </Form.Item>
          <Form.Item name="icon" label="图标">
            <Select placeholder="选择图标" allowClear>
              {iconOptions.map((opt) => (
                <Select.Option key={opt.value} value={opt.value}>
                  <Space>{opt.icon}</Space>
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} placeholder="链接描述（可选）" />
          </Form.Item>
          <Form.Item name="restrictToCurrentRole" label="可见范围" valuePropName="checked">
            <Switch checkedChildren="当前角色" unCheckedChildren="全部" />
          </Form.Item>
          <Form.Item name="sortOrder" label="排序" help="数字越小越靠前">
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="isActive" label="启用状态" valuePropName="checked">
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default NavigationList;
