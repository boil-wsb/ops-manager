import { memo, useState } from 'react';
import {
  BaseEdge,
  EdgeLabelRenderer,
  getBezierPath,
} from '@xyflow/react';
import type { Edge, EdgeProps } from '@xyflow/react';
import { Tag } from 'antd';
import { useThemeStore } from '../../stores/themeStore';

// ====== Types ======

// Index signature required by @xyflow/react v12's `Edge<Record<string, unknown>>`
// constraint. Known fields keep their declared (more specific) types.
export interface AssetEdgeData {
  relationType: 'CONNECTED' | 'LOCATED_IN' | 'CUSTOM';
  autoInferred: boolean;
  label?: string | null;
  labelColor?: string | null;
  highlightLabelId: number | null;
  [key: string]: unknown;
}

// Full Flow edge type (data = AssetEdgeData). EdgeProps<T> requires T to be a
// complete Edge, not just the data shape.
export type AssetFlowEdge = Edge<AssetEdgeData>;
type AssetEdgeType = EdgeProps<AssetFlowEdge>;

// ====== Style ======

const RELATION_LABELS: Record<string, string> = {
  CONNECTED: '网络连接',
  LOCATED_IN: '同位置',
  CUSTOM: '自定义',
};

// ====== Main component ======

function AssetEdgeImpl({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  selected,
}: AssetEdgeType) {
  const [hovered, setHovered] = useState(false);
  const mode = useThemeStore((s) => s.mode);
  const isDark = mode === 'dark';

  const relationType = data?.relationType || 'CUSTOM';
  const autoInferred = data?.autoInferred ?? true;
  const edgeLabel = data?.label || null;
  const edgeLabelColor = data?.labelColor || '#1890ff';
  const highlightLabelId = data?.highlightLabelId ?? null;

  // Label-colored edges take their color from the label; others use theme-aware default
  const defaultEdgeColor = isDark ? 'rgba(255,255,255,0.35)' : 'rgba(20,25,50,0.35)';
  const color = edgeLabel ? edgeLabelColor : defaultEdgeColor;

  // Dim non-highlighted edges when a label is being highlighted
  const dimmed =
    highlightLabelId != null
      ? // label edges: dim if their label isn't the highlighted one (we can't know label id here,
        // so dim if this edge has no label OR... actually we pass highlight via data; the parent
        // sets highlightLabelId; label edges keep their color, non-label edges dim)
        !edgeLabel
      : false;
  const opacity = dimmed ? 0.15 : autoInferred ? 0.6 : 1;

  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  const showLabel = hovered || selected || !!edgeLabel;

  return (
    <>
      {/* Invisible wider path for easier hover */}
      <path
        d={edgePath}
        fill="none"
        stroke="transparent"
        strokeWidth={16}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
      />
      <BaseEdge
        id={id}
        path={edgePath}
        style={{
          stroke: color,
          strokeWidth: selected || hovered ? 2.5 : edgeLabel ? 2 : 1.5,
          strokeDasharray: autoInferred && !edgeLabel ? '5 5' : undefined,
          opacity,
          transition: 'opacity 0.2s, stroke-width 0.2s',
        }}
      />
      <EdgeLabelRenderer>
        {showLabel && (
          <div
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
              pointerEvents: 'none',
              opacity,
            }}
            className="nodrag nopan"
          >
            {edgeLabel ? (
              <Tag
                color={edgeLabelColor}
                style={{ margin: 0, padding: '0 6px', fontSize: 10, lineHeight: '16px' }}
              >
                {edgeLabel}
              </Tag>
            ) : (
              (hovered || selected) && (
                <span
                  style={{
                    backgroundColor: isDark ? 'rgba(30,30,54,0.95)' : 'rgba(255,255,255,0.95)',
                    color: isDark ? 'rgba(255,255,255,0.85)' : 'rgba(20,25,50,0.75)',
                    padding: '1px 6px',
                    borderRadius: 4,
                    border: `1px solid ${isDark ? 'rgba(255,255,255,0.2)' : 'rgba(20,25,50,0.15)'}`,
                    fontSize: 10,
                    boxShadow: '0 2px 4px rgba(0,0,0,0.15)',
                  }}
                >
                  {RELATION_LABELS[relationType] || relationType}
                </span>
              )
            )}
          </div>
        )}
      </EdgeLabelRenderer>
    </>
  );
}

export const AssetEdge = memo(AssetEdgeImpl);
export default AssetEdge;
