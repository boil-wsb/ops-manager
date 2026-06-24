import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';
import { Tooltip } from 'antd';
import {
  DesktopOutlined,
  HddOutlined,
  GlobalOutlined,
  DatabaseOutlined,
  LaptopOutlined,
} from '@ant-design/icons';
import type { TopologyNode } from '../../services/topology';
import { useThemeStore } from '../../stores/themeStore';

// ====== Types ======

export interface AssetNodeData {
  asset: TopologyNode;
  isSelected: boolean;
  highlightLabelId: number | null;
}

type AssetNodeType = NodeProps<AssetNodeData>;

// ====== Style constants ======

const STATUS_COLORS: Record<string, string> = {
  ACTIVE: '#52c41a', // green
  OFFLINE: '#8c8c8c', // gray
  MAINTENANCE: '#fa8c16', // orange
  RETIRED: '#bfbfbf',
};

const TYPE_LABELS: Record<string, string> = {
  SERVER: '物理机',
  VM: '虚拟机',
  NETWORK: '网络设备',
  STORAGE: '存储设备',
  TERMINAL: '终端',
};

// ====== Metric color helper ======

function metricColor(value: number | null | undefined): string {
  if (value == null) return '#8c8c8c';
  if (value > 80) return '#f5222d';
  if (value > 60) return '#fa8c16';
  return '#52c41a';
}

function metricText(value: number | null | undefined): string {
  if (value == null) return '—';
  return `${Math.round(value)}%`;
}

// ====== Type icon ======

function TypeIcon({ type, size, color }: { type: string; size: number; color: string }) {
  const common = { style: { fontSize: size, color } };
  switch (type) {
    case 'SERVER':
      return <HddOutlined {...common} />;
    case 'VM':
      return <DesktopOutlined {...common} />;
    case 'NETWORK':
      return <GlobalOutlined {...common} />;
    case 'STORAGE':
      return <DatabaseOutlined {...common} />;
    case 'TERMINAL':
      return <LaptopOutlined {...common} />;
    default:
      return <DesktopOutlined {...common} />;
  }
}

// ====== Node size ======

const NODE_DIAMETER = 56;

// ====== Main component ======

function AssetNodeImpl({ data, selected }: AssetNodeType) {
  const { asset, isSelected, highlightLabelId } = data;
  const mode = useThemeStore((s) => s.mode);
  const isDark = mode === 'dark';

  const statusColor = STATUS_COLORS[asset.status] || '#8c8c8c';
  const active = isSelected || selected;
  const hasHighlightLabel =
    highlightLabelId != null && (asset.labels || []).some((l) => l.id === highlightLabelId);

  // Theme-aware colors
  const textColor = isDark ? 'rgba(255,255,255,0.85)' : 'rgba(20,25,50,0.88)';
  const textSecondary = isDark ? 'rgba(255,255,255,0.55)' : 'rgba(20,25,50,0.55)';
  const ringBase = isDark ? '#3a3a5a' : '#e0e0e0';
  const iconColor = isDark ? 'rgba(255,255,255,0.85)' : 'rgba(20,25,50,0.85)';
  const nodeBg = isDark ? '#1e1e36' : '#ffffff';
  const dimOpacity = highlightLabelId != null && !hasHighlightLabel ? 0.25 : 1;

  // Build tooltip content
  const metrics = asset.metrics;
  const tooltipContent = (
    <div style={{ minWidth: 200, fontSize: 12, lineHeight: '18px' }}>
      <div style={{ fontWeight: 600, marginBottom: 4 }}>
        {asset.name}
        <span style={{ color: 'rgba(255,255,255,0.5)', marginLeft: 8, fontWeight: 400 }}>
          {TYPE_LABELS[asset.type] || asset.type}
        </span>
      </div>
      <div style={{ color: 'rgba(255,255,255,0.65)' }}>
        {asset.ipAddress || '—'} · {asset.ownerName || '未分配'}
      </div>
      {(asset.type === 'SERVER' || asset.type === 'VM') && (
        <div style={{ marginTop: 6, borderTop: '1px solid rgba(255,255,255,0.15)', paddingTop: 6 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span>CPU</span>
            <span style={{ color: metricColor(metrics.cpu) }}>{metricText(metrics.cpu)}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span>内存</span>
            <span style={{ color: metricColor(metrics.mem) }}>{metricText(metrics.mem)}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span>磁盘</span>
            <span style={{ color: metricColor(metrics.disk) }}>{metricText(metrics.disk)}</span>
          </div>
          {metrics.checkedAt && (
            <div style={{ color: 'rgba(255,255,255,0.4)', marginTop: 4, fontSize: 11 }}>
              巡检: {new Date(metrics.checkedAt).toLocaleString('zh-CN')}
            </div>
          )}
        </div>
      )}
      {(asset.labels?.length ?? 0) > 0 && (
        <div style={{ marginTop: 6, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
          {asset.labels.map((l) => (
            <span
              key={l.id}
              style={{
                display: 'inline-block',
                padding: '0 6px',
                borderRadius: 8,
                fontSize: 10,
                lineHeight: '16px',
                backgroundColor: `${l.color}33`,
                color: l.color,
                border: `1px solid ${l.color}55`,
              }}
            >
              {l.name}
            </span>
          ))}
        </div>
      )}
    </div>
  );

  return (
    <Tooltip title={tooltipContent} placement="right" color="rgba(0,0,0,0.85)">
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          opacity: dimOpacity,
          transition: 'opacity 0.2s',
          cursor: 'pointer',
        }}
      >
        {/* Circular dot */}
        <div
          style={{
            width: NODE_DIAMETER,
            height: NODE_DIAMETER,
            borderRadius: '50%',
            backgroundColor: nodeBg,
            border: `3px solid ${active ? '#1890ff' : statusColor}`,
            boxShadow: active
              ? `0 0 0 3px rgba(24,144,255,0.25), 0 4px 12px rgba(0,0,0,${isDark ? 0.5 : 0.12})`
              : hasHighlightLabel
              ? `0 0 0 3px rgba(24,144,255,0.2)`
              : `0 2px 6px rgba(0,0,0,${isDark ? 0.4 : 0.1})`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            position: 'relative',
            transition: 'box-shadow 0.2s, border-color 0.2s',
          }}
        >
          <TypeIcon type={asset.type} size={22} color={iconColor} />
          {/* Status dot at top-right */}
          <span
            style={{
              position: 'absolute',
              top: -2,
              right: -2,
              width: 10,
              height: 10,
              borderRadius: '50%',
              backgroundColor: statusColor,
              border: `2px solid ${nodeBg}`,
            }}
          />
        </div>
        {/* Name label below */}
        <div
          style={{
            marginTop: 4,
            fontSize: 11,
            color: textColor,
            maxWidth: 90,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            textAlign: 'center',
            fontWeight: active ? 600 : 400,
          }}
          title={asset.name}
        >
          {asset.name}
        </div>
        {/* IP below name */}
        {asset.ipAddress && (
          <div
            style={{
              fontSize: 9,
              color: textSecondary,
              maxWidth: 90,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              textAlign: 'center',
            }}
          >
            {asset.ipAddress}
          </div>
        )}

        {/* Hidden handles so the node is still connectable if needed */}
        <Handle type="target" position={Position.Top} id="t" style={{ opacity: 0, top: -6 }} />
        <Handle type="source" position={Position.Bottom} id="b" style={{ opacity: 0, bottom: -6 }} />
      </div>
    </Tooltip>
  );
}

export const AssetNode = memo(AssetNodeImpl);
export default AssetNode;
