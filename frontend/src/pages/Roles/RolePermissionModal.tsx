import { useState, useEffect } from 'react';
import {
  Modal,
  Tree,
  message,
  Spin,
  Typography,
  Space,
  Checkbox,
  Card,
  Divider,
  Button,
} from 'antd';
import { SafetyOutlined, CheckOutlined, CloseOutlined } from '@ant-design/icons';
import {
  roleApi,
  permissionApi,
  Role,
  PermissionGroup,
  Permission,
} from '../../services/permissions';

const { Title, Text } = Typography;

interface RolePermissionModalProps {
  visible: boolean;
  onCancel: () => void;
  onSuccess: () => void;
  role: Role | null;
}

interface TreeNode {
  title: string;
  key: string;
  children?: TreeNode[];
  permission?: Permission;
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
  const [expandedKeys, setExpandedKeys] = useState<string[]>([]);
  const [checkAllMap, setCheckAllMap] = useState<Record<string, boolean>>({});

  useEffect(() => {
    if (visible && role) {
      fetchData();
    }
  }, [visible, role]);

  const fetchData = async () => {
    if (!role) return;

    setLoading(true);
    try {
      // Fetch all permissions grouped by module
      const [permissionsRes, rolePermissionsRes] = await Promise.all([
        permissionApi.getPermissions(),
        roleApi.getRolePermissions(role.id),
      ]);

      const groups = permissionsRes.data.items;
      setPermissionGroups(groups);

      // Get currently selected permission IDs
      const currentPermIds = rolePermissionsRes.data.permissions.map((p) => p.id);
      setSelectedPermissions(currentPermIds);

      // Expand all module nodes
      const moduleKeys = groups.map((g) => `module-${g.module}`);
      setExpandedKeys(moduleKeys);

      // Calculate check-all status for each module
      const checkAllStatus: Record<string, boolean> = {};
      groups.forEach((group) => {
        const groupPermIds = group.permissions.map((p) => p.id);
        const allSelected = groupPermIds.every((id) => currentPermIds.includes(id));
        checkAllStatus[group.module] = allSelected;
      });
      setCheckAllMap(checkAllStatus);
    } catch (error) {
      message.error('获取权限数据失败');
    } finally {
      setLoading(false);
    }
  };

  const buildTreeData = (): TreeNode[] => {
    return permissionGroups.map((group) => ({
      title: (
        <Space>
          <span style={{ fontWeight: 600 }}>{group.module_name}</span>
          <Text type="secondary" style={{ fontSize: 12 }}>
            ({group.permissions.length} 个权限)
          </Text>
        </Space>
      ),
      key: `module-${group.module}`,
      children: group.permissions.map((perm) => ({
        title: (
          <Space direction="vertical" size={0} style={{ marginLeft: 8 }}>
            <Text>{perm.name}</Text>
            <Text type="secondary" style={{ fontSize: 11 }}>
              {perm.description || perm.code}
            </Text>
          </Space>
        ),
        key: `perm-${perm.id}`,
        permission: perm,
      })),
    }));
  };

  const handleCheck = (checkedKeys: string[]) => {
    // Extract permission IDs from checked keys
    const permIds = checkedKeys
      .filter((key) => key.startsWith('perm-'))
      .map((key) => parseInt(key.replace('perm-', '')));

    setSelectedPermissions(permIds);

    // Update check-all status for each module
    const newCheckAllMap: Record<string, boolean> = {};
    permissionGroups.forEach((group) => {
      const groupPermIds = group.permissions.map((p) => p.id);
      const allSelected = groupPermIds.every((id) => permIds.includes(id));
      newCheckAllMap[group.module] = allSelected;
    });
    setCheckAllMap(newCheckAllMap);
  };

  const handleCheckAll = (module: string, checked: boolean) => {
    const group = permissionGroups.find((g) => g.module === module);
    if (!group) return;

    const groupPermIds = group.permissions.map((p) => p.id);

    let newSelectedPermissions: number[];
    if (checked) {
      // Add all permissions from this module
      newSelectedPermissions = [...new Set([...selectedPermissions, ...groupPermIds])];
    } else {
      // Remove all permissions from this module
      newSelectedPermissions = selectedPermissions.filter((id) => !groupPermIds.includes(id));
    }

    setSelectedPermissions(newSelectedPermissions);
    setCheckAllMap({ ...checkAllMap, [module]: checked });
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
    } catch (error: any) {
      message.error(error.response?.data?.detail || '权限分配失败');
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

  const treeData = buildTreeData();
  const checkedKeys = selectedPermissions.map((id) => `perm-${id}`);

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
                    onChange={(e) => {
                      const newSelected = e.target.checked
                        ? [...selectedPermissions, perm.id]
                        : selectedPermissions.filter((id) => id !== perm.id);
                      handleCheck(newSelected.map((id) => `perm-${id}`));
                    }}
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
