import { useState, useEffect, useCallback, useRef } from 'react';
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
  InputNumber,
  Switch,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  LinkOutlined,
  CloudUploadOutlined,
  DatabaseOutlined,
  DesktopOutlined,
  CloudOutlined,
  SettingOutlined,
  DashboardOutlined,
  SafetyOutlined,
  ApiOutlined,
  UploadOutlined,
  DownloadOutlined,
} from '@ant-design/icons';
import { navigationApi, type NavigationLink, type NavigationLinkCreate, type NavigationLinkUpdate, type NavigationImportResponse } from '../../services/navigation';
import { fuzzyFilterOption } from '../../utils/selectFilter';

const { Search } = Input;

interface Role {
  id: number;
  name: string;
}

const iconMap: Record<string, React.ReactNode> = {
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
  const [importLoading, setImportLoading] = useState(false);
  const [importResult, setImportResult] = useState<NavigationImportResponse | null>(null);
  const [importResultModalVisible, setImportResultModalVisible] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

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

  const handleExport = async () => {
    try {
      await navigationApi.exportLinks();
      message.success('导出成功');
    } catch {
      message.error('导出失败');
    }
  };

  const handleImportClick = () => {
    fileInputRef.current?.click();
  };

  const parseCSV = (csvText: string) => {
    const lines = csvText.split('\n').filter(line => line.trim());
    if (lines.length < 2) return [];
    const headers = lines[0].split(',').map(h => h.trim().toLowerCase());
    const data: Record<string, string>[] = [];
    for (let i = 1; i < lines.length; i++) {
      const values = lines[i].split(',').map(v => v.trim());
      const row: Record<string, string> = {};
      headers.forEach((header, index) => {
        row[header] = values[index] || '';
      });
      data.push(row);
    }
    return data;
  };

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setImportLoading(true);
    try {
      const text = await file.text();
      const csvData = parseCSV(text);

      const importData = csvData.map(row => ({
        category: row.category || '',
        name: row.name || '',
        url: row.url || '',
        icon: row.icon || undefined,
        description: row.description || undefined,
        sortOrder: parseInt(row.sort_order || '0', 10) || 0,
        isActive: row.is_active?.toLowerCase() !== 'false',
        roleNames: row.role_names || '',
      })).filter(item => item.name && item.url);

      if (importData.length === 0) {
        message.error('CSV 文件中没有有效数据');
        return;
      }

      const result = await navigationApi.importLinks(importData);
      setImportResult(result);
      setImportResultModalVisible(true);
      fetchLinks();
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : '导入失败';
      message.error(errorMessage);
    } finally {
      setImportLoading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
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
      sorter: (a: NavigationLink, b: NavigationLink) => a.category.localeCompare(b.category),
      render: (text: string) => <Tag color="blue">{text}</Tag>,
    },
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      width: 150,
      sorter: (a: NavigationLink, b: NavigationLink) => a.name.localeCompare(b.name),
      render: (text: string) => <span style={{ fontWeight: 500 }}>{text}</span>,
    },
    {
      title: '链接地址',
      dataIndex: 'url',
      key: 'url',
      ellipsis: true,
      sorter: (a: NavigationLink, b: NavigationLink) => a.url.localeCompare(b.url),
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
      sorter: (a: NavigationLink, b: NavigationLink) => (a.icon || '').localeCompare(b.icon || ''),
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
      sorter: (a: NavigationLink, b: NavigationLink) => (a.roles?.length || 0) - (b.roles?.length || 0),
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
      sorter: (a: NavigationLink, b: NavigationLink) => a.sortOrder - b.sortOrder,
    },
    {
      title: '状态',
      dataIndex: 'isActive',
      key: 'isActive',
      width: 80,
      sorter: (a: NavigationLink, b: NavigationLink) => (a.isActive === b.isActive ? 0 : a.isActive ? -1 : 1),
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
          <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center' }}>
            <Space>
              <Select
                placeholder="筛选分类"
                allowClear
                style={{ width: 150 }}
                value={categoryFilter}
                onChange={(value) => setCategoryFilter(value)}
                showSearch
                filterOption={fuzzyFilterOption}
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
              <Button icon={<DownloadOutlined />} onClick={handleExport}>
                导出
              </Button>
              <Button icon={<UploadOutlined />} onClick={handleImportClick} loading={importLoading}>
                导入
              </Button>
            </Space>
          </div>
        }
        style={{ background: 'var(--bg-card)' }}
      >
        <input
          type="file"
          accept=".csv"
          ref={fileInputRef}
          style={{ display: 'none' }}
          onChange={handleFileChange}
        />
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

      <Modal
        title="导入结果"
        open={importResultModalVisible}
        onOk={() => setImportResultModalVisible(false)}
        onCancel={() => setImportResultModalVisible(false)}
        width={600}
        okText="确定"
        cancelText="取消"
      >
        {importResult && (
          <div>
            <p>总记录数：{importResult.total}</p>
            <p style={{ color: 'green' }}>成功：{importResult.success_count}</p>
            <p style={{ color: importResult.failed_count > 0 ? 'red' : 'inherit' }}>失败：{importResult.failed_count}</p>
            {importResult.results.length > 0 && (
              <div style={{ maxHeight: 300, overflowY: 'auto', marginTop: 16 }}>
                {importResult.results.map((result, index) => (
                  <div
                    key={index}
                    style={{
                      padding: '8px',
                      marginBottom: 4,
                      background: result.success ? '#f6ffed' : '#fff2f0',
                      border: `1px solid ${result.success ? '#b7eb8f' : '#ffccc7'}`,
                      borderRadius: 4,
                    }}
                  >
                    <strong>{result.name}</strong>: {result.message}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};

export default NavigationList;
