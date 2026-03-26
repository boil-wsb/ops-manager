import { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Modal,
  message,
  Spin,
  Typography,
  Space,
  Checkbox,
  Card,
  Button,
  Alert,
  Tooltip,
  Tag,
} from 'antd';
import { SafetyOutlined, LockOutlined, CheckCircleOutlined, StopOutlined } from '@ant-design/icons';
import {
  roleApi,
  permissionApi,
  type Role,
  type PermissionGroup,
} from '../../services/permissions';
import { MenuPreview } from '../../components/MenuPreview';
import {
  flattenMenuPermissions,
  getPermissionStatus,
  extractAllPermissions,
  type PermissionWithStatus,
  type PermissionStatus,
} from '../../config/menuPermissionConfig';
import { useThemeStore } from '../../stores/themeStore';

const { Text } = Typography;

interface RolePermissionModalProps {
  visible: boolean;
  onCancel: () => void;
  onSuccess: () => void;
  role: Role | null;
}

const getStatusConfig = (isDark: boolean): Record<
  PermissionStatus,
  { icon: React.ReactNode; color: string; bgColor: string; text: string }
> => ({
  enabled: {
    icon: <CheckCircleOutlined />,
    color: '#52c41a',
    bgColor: isDark ? '#1c1c1c' : '#f6ffed',
    text: '可访问',
  },
  disabled: {
    icon: <StopOutlined />,
    color: '#ff4d4f',
    bgColor: isDark ? '#2a1c1c' : '#fff2f0',
    text: '父权限缺失',
  },
  available: {
    icon: <CheckCircleOutlined />,
    color: '#1890ff',
    bgColor: isDark ? '#1c2420' : '#e6f7ff',
    text: '可勾选',
  },
  locked: {
    icon: <LockOutlined />,
    color: '#faad14',
    bgColor: isDark ? '#2a2418' : '#fffbe6',
    text: '需父权限',
  },
});

const RolePermissionModal = ({
  visible,
  onCancel,
  onSuccess,
  role,
}: RolePermissionModalProps) => {
  const { mode: themeMode } = useThemeStore();
  const isDark = themeMode === 'dark';
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [permissionGroups, setPermissionGroups] = useState<PermissionGroup[]>([]);
  const [selectedPermissionIds, setSelectedPermissionIds] = useState<number[]>([]);
  const [checkAllMap, setCheckAllMap] = useState<Record<string, boolean>>({});

  const flattenedPermissions = useMemo(() => flattenMenuPermissions(), []);

  const menuPermissionSet = useMemo(() => new Set(extractAllPermissions()), []);

  const selectedPermissionCodes = useMemo(() => {
    const codes: string[] = [];
    for (const group of permissionGroups) {
      for (const perm of group.permissions) {
        if (selectedPermissionIds.includes(perm.id)) {
          codes.push(perm.code);
        }
      }
    }
    return codes;
  }, [permissionGroups, selectedPermissionIds]);

  const allPermissionsWithStatus = useMemo((): PermissionWithStatus[] => {
    const result: PermissionWithStatus[] = [];

    for (const group of permissionGroups) {
      for (const perm of group.permissions) {
        result.push(getPermissionStatus(perm, selectedPermissionCodes, flattenedPermissions));
      }
    }

    return result;
  }, [permissionGroups, selectedPermissionCodes, flattenedPermissions]);

  const fetchData = useCallback(async () => {
    if (!role) return;

    setLoading(true);
    try {
      const allPermissionsRes = await permissionApi.getPermissions({ page: 1, page_size: 1000 });

      const rolePermissionsRes = await roleApi.getRolePermissions(role.id);

      setPermissionGroups(allPermissionsRes.data.items || []);

      const currentPermIds = rolePermissionsRes.data.permissions.map((p) => p.id);
      setSelectedPermissionIds(currentPermIds);

      const checkAllStatus: Record<string, boolean> = {};
      (allPermissionsRes.data.items || []).forEach((group) => {
        const groupPermIds = group.permissions.map((p) => p.id);
        const allSelected =
          groupPermIds.length > 0 &&
          groupPermIds.every((id) => currentPermIds.includes(id));
        checkAllStatus[group.module] = allSelected;
      });
      setCheckAllMap(checkAllStatus);
    } catch {
      message.error('获取权限数据失败');
    } finally {
      setLoading(false);
    }
  }, [role]);

  useEffect(() => {
    if (visible && role) {
      fetchData();
    }
  }, [visible, role, fetchData]);

  const handleCheckAll = (module: string, checked: boolean) => {
    const group = permissionGroups.find((g) => g.module === module);
    if (!group) return;

    const groupPermIds = group.permissions.map((p) => p.id);

    let newSelectedPermissions: number[];
    if (checked) {
      newSelectedPermissions = [...new Set([...selectedPermissionIds, ...groupPermIds])];
    } else {
      newSelectedPermissions = selectedPermissionIds.filter((id) => !groupPermIds.includes(id));
    }

    setSelectedPermissionIds(newSelectedPermissions);
    setCheckAllMap({ ...checkAllMap, [module]: checked });
  };

  const handlePermissionChange = (permId: number, checked: boolean, module: string) => {
    let newSelectedPermissions: number[];
    if (checked) {
      newSelectedPermissions = [...selectedPermissionIds, permId];
    } else {
      newSelectedPermissions = selectedPermissionIds.filter((id) => id !== permId);
    }
    setSelectedPermissionIds(newSelectedPermissions);

    const group = permissionGroups.find((g) => g.module === module);
    if (group) {
      const groupPermIds = group.permissions.map((p) => p.id);
      const allSelected = groupPermIds.every((id) => newSelectedPermissions.includes(id));
      setCheckAllMap({ ...checkAllMap, [module]: allSelected });
    }
  };

  const handleSubmit = async () => {
    if (!role) return;

    setSaving(true);
    try {
      await roleApi.updateRolePermissions(role.id, {
        permission_ids: selectedPermissionIds,
      });
      message.success('权限分配成功');
      onSuccess();
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : '权限分配失败';
      message.error(errorMessage);
    } finally {
      setSaving(false);
    }
  };

  const handleSelectAll = () => {
    const allPermIds = permissionGroups.flatMap((g) => g.permissions.map((p) => p.id));
    setSelectedPermissionIds(allPermIds);

    const newCheckAllMap: Record<string, boolean> = {};
    permissionGroups.forEach((g) => {
      newCheckAllMap[g.module] = true;
    });
    setCheckAllMap(newCheckAllMap);
  };

  const handleClearAll = () => {
    setSelectedPermissionIds([]);

    const newCheckAllMap: Record<string, boolean> = {};
    permissionGroups.forEach((g) => {
      newCheckAllMap[g.module] = false;
    });
    setCheckAllMap(newCheckAllMap);
  };

  const renderPermissionItem = (permWithStatus: PermissionWithStatus) => {
    const { permission, status, missingParentPermission } = permWithStatus;
    const isMenuRelated = menuPermissionSet.has(permission.code);
    const statusCfg = getStatusConfig(isDark);
    const config = isMenuRelated ? statusCfg[status] : null;
    const isLocked = isMenuRelated && (status === 'locked' || status === 'disabled');

    return (
      <Tooltip
        key={permission.id}
        title={
          isLocked && missingParentPermission
            ? `需要先勾选父权限: ${missingParentPermission}`
            : config?.text
        }
      >
        <div
          style={{
            padding: '8px 12px',
            borderRadius: 6,
            background: config?.bgColor || (selectedPermissionIds.includes(permission.id) ? (isDark ? '#1c1c1c' : '#f6ffed') : (isDark ? '#1f1f1f' : '#fff')),
            border: `1px solid ${config?.color || '#d9d9d9'}30`,
            opacity: isLocked ? 0.7 : 1,
          }}
        >
          <Checkbox
            checked={selectedPermissionIds.includes(permission.id)}
            onChange={(e) => {
              const group = permissionGroups.find((g) =>
                g.permissions.some((p) => p.id === permission.id)
              );
              handlePermissionChange(
                permission.id,
                e.target.checked,
                group?.module || ''
              );
            }}
          >
            <Space size={4}>
              <Text style={{ fontSize: 13 }}>{permission.name}</Text>
              <Text type="secondary" style={{ fontSize: 11 }}>
                {permission.code}
              </Text>
              {isMenuRelated && config && (
                <Tag
                  color={config.color}
                  style={{ marginLeft: 4, fontSize: 10, padding: '0 4px' }}
                >
                  {config.text}
                </Tag>
              )}
            </Space>
          </Checkbox>
        </div>
      </Tooltip>
    );
  };

  return (
    <Modal
      title={
        <Space>
          <SafetyOutlined />
          <span>分配权限 - {role?.name}</span>
        </Space>
      }
      open={visible}
      onOk={handleSubmit}
      onCancel={onCancel}
      width={1100}
      confirmLoading={saving}
      okText="保存"
      cancelText="取消"
    >
      <Spin spinning={loading}>
        <div style={{ display: 'flex', gap: 24 }}>
          <div style={{ flex: 1 }}>
            <div style={{ marginBottom: 12 }}>
              <Space>
                <Text strong>权限配置</Text>
                <Text type="secondary">（全部 {allPermissionsWithStatus.length} 项）</Text>
              </Space>
            </div>

            {allPermissionsWithStatus.some((p) => p.status === 'disabled') && (
              <Alert
                type="warning"
                showIcon
                icon={<LockOutlined />}
                message="部分权限缺少父权限，即使勾选也无法生效"
                style={{ marginBottom: 12 }}
              />
            )}

            <div
              style={{
                maxHeight: 450,
                overflowY: 'auto',
                border: `1px solid ${isDark ? '#303030' : '#f0f0f0'}`,
                borderRadius: 8,
                padding: 12,
              }}
            >
              {permissionGroups.length === 0 && !loading && (
                <Text type="secondary">暂无权限数据</Text>
              )}
              {permissionGroups.map((group) => (
                <Card
                  key={group.module}
                  size="small"
                  style={{ marginBottom: 12 }}
                  title={
                    <Space>
                      <span style={{ fontWeight: 600 }}>{group.module_name}</span>
                      <Tag>{group.permissions.length} 项</Tag>
                      <Checkbox
                        checked={checkAllMap[group.module] || false}
                        onChange={(e) => handleCheckAll(group.module, e.target.checked)}
                      >
                        全选
                      </Checkbox>
                    </Space>
                  }
                >
                  <Space direction="vertical" style={{ width: '100%' }} size={8}>
                    {group.permissions.map((perm) => {
                      const permWithStatus = allPermissionsWithStatus.find(
                        (p) => p.permission.id === perm.id
                      );
                      if (!permWithStatus) return null;
                      return renderPermissionItem(permWithStatus);
                    })}
                  </Space>
                </Card>
              ))}
            </div>

            <div style={{ marginTop: 12 }}>
              <Space>
                <Text type="secondary">
                  已选择 {selectedPermissionIds.length} / {allPermissionsWithStatus.length} 个权限
                </Text>
                <Button type="link" size="small" onClick={handleSelectAll}>
                  全选
                </Button>
                <Button type="link" size="small" onClick={handleClearAll}>
                  清空
                </Button>
              </Space>
            </div>
          </div>

          <div style={{ flex: 1 }}>
            <div style={{ marginBottom: 12 }}>
              <Text strong>菜单预览</Text>
              <Text type="secondary">（实时效果）</Text>
            </div>
            <MenuPreview selectedPermissions={selectedPermissionCodes} />
          </div>
        </div>
      </Spin>
    </Modal>
  );
};

export default RolePermissionModal;
