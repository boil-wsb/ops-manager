import { useState, useEffect, useCallback } from 'react';
import {
  Modal,
  message,
  Spin,
  Typography,
  Space,
  Checkbox,
  Card,
  Button,
} from 'antd';
import { SafetyOutlined } from '@ant-design/icons';
import {
  roleApi,
  permissionApi,
  type Role,
  type PermissionGroup,
} from '../../services/permissions';

const { Text } = Typography;

interface RolePermissionModalProps {
  visible: boolean;
  onCancel: () => void;
  onSuccess: () => void;
  role: Role | null;
}

const RolePermissionModal = ({
  visible,
  onCancel,
  onSuccess,
  role,
}: RolePermissionModalProps) => {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [permissionGroups, setPermissionGroups] = useState<PermissionGroup[]>([]);
  const [selectedPermissions, setSelectedPermissions] = useState<number[]>([]);
  const [checkAllMap, setCheckAllMap] = useState<Record<string, boolean>>({});

  const fetchData = useCallback(async () => {
    if (!role) return;

    setLoading(true);
    try {
      const allPermissionsRes = await permissionApi.getPermissions({ page: 1, page_size: 1000 });
      
      const rolePermissionsRes = await roleApi.getRolePermissions(role.id);

      setPermissionGroups(allPermissionsRes.data.items || []);

      const currentPermIds = rolePermissionsRes.data.permissions.map((p) => p.id);
      setSelectedPermissions(currentPermIds);

      const checkAllStatus: Record<string, boolean> = {};
      (allPermissionsRes.data.items || []).forEach((group) => {
        const groupPermIds = group.permissions.map((p) => p.id);
        const allSelected = groupPermIds.length > 0 && groupPermIds.every((id) => currentPermIds.includes(id));
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
      newSelectedPermissions = [...new Set([...selectedPermissions, ...groupPermIds])];
    } else {
      newSelectedPermissions = selectedPermissions.filter((id) => !groupPermIds.includes(id));
    }

    setSelectedPermissions(newSelectedPermissions);
    setCheckAllMap({ ...checkAllMap, [module]: checked });
  };

  const handlePermissionChange = (permId: number, checked: boolean, module: string) => {
    let newSelectedPermissions: number[];
    if (checked) {
      newSelectedPermissions = [...selectedPermissions, permId];
    } else {
      newSelectedPermissions = selectedPermissions.filter((id) => id !== permId);
    }
    setSelectedPermissions(newSelectedPermissions);

    // Update check-all status for this module
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
        permission_ids: selectedPermissions,
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
    setSelectedPermissions(allPermIds);

    const newCheckAllMap: Record<string, boolean> = {};
    permissionGroups.forEach((g) => {
      newCheckAllMap[g.module] = true;
    });
    setCheckAllMap(newCheckAllMap);
  };

  const handleClearAll = () => {
    setSelectedPermissions([]);

    const newCheckAllMap: Record<string, boolean> = {};
    permissionGroups.forEach((g) => {
      newCheckAllMap[g.module] = false;
    });
    setCheckAllMap(newCheckAllMap);
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
      width={700}
      confirmLoading={saving}
      okText="保存"
      cancelText="取消"
    >
      <Spin spinning={loading}>
        <div style={{ marginBottom: 16 }}>
          <Space>
            <Text strong>已选择 {selectedPermissions.length} 个权限</Text>
            <Button type="link" size="small" onClick={handleSelectAll}>
              全选
            </Button>
            <Button type="link" size="small" onClick={handleClearAll}>
              清空
            </Button>
          </Space>
        </div>

        <div
          style={{
            maxHeight: 500,
            overflowY: 'auto',
            border: '1px solid #f0f0f0',
            borderRadius: 8,
            padding: 16,
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
                  <Checkbox
                    checked={checkAllMap[group.module] || false}
                    onChange={(e) => handleCheckAll(group.module, e.target.checked)}
                  >
                    全选
                  </Checkbox>
                </Space>
              }
            >
              <Space wrap>
                {group.permissions.map((perm) => (
                  <Checkbox
                    key={perm.id}
                    checked={selectedPermissions.includes(perm.id)}
                    onChange={(e) => handlePermissionChange(perm.id, e.target.checked, group.module)}
                  >
                    <Space direction="vertical" size={0}>
                      <Text style={{ fontSize: 13 }}>{perm.name}</Text>
                      <Text type="secondary" style={{ fontSize: 11 }}>
                        {perm.code}
                      </Text>
                    </Space>
                  </Checkbox>
                ))}
              </Space>
            </Card>
          ))}
        </div>
      </Spin>
    </Modal>
  );
};

export default RolePermissionModal;
