import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
  useReactFlow,
} from '@xyflow/react';
import type {
  Edge,
  EdgeTypes,
  Node,
  NodeMouseHandler,
  NodeTypes,
} from '@xyflow/react';
import dagre from 'dagre';
import { useQuery } from '@tanstack/react-query';
import {
  App,
  Button,
  Card,
  Drawer,
  Empty,
  Select,
  Space,
  Spin,
  Tag,
  Tooltip,
} from 'antd';
import {
  CompressOutlined,
  FilterOutlined,
  LayoutOutlined,
  ReloadOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import '@xyflow/react/dist/style.css';

import {
  topologyApi,
  type TopologyEdge,
  type TopologyLabel,
  type TopologyNode,
} from '../../services/topology';
import { AssetNode, type AssetNodeData } from '../../components/Topology/AssetNode';
import { AssetEdge, type AssetEdgeData } from '../../components/Topology/AssetEdge';
import StatusTag from '../../components/StatusTag';
import { useThemeStore } from '../../stores/themeStore';

// ====== Types ======

interface FlowNode extends Node<AssetNodeData> {}
interface FlowEdge extends Edge<AssetEdgeData> {}

// ====== Layout config ======

const NODE_WIDTH = 90;
const NODE_HEIGHT = 90;

// ====== Dagre layout ======

function layoutWithDagre(
  nodes: FlowNode[],
  edges: FlowEdge[],
  direction: 'LR' | 'TB' = 'LR'
): FlowNode[] {
  const g = new dagre.graphlib.Graph();
  g.setGraph({
    rankdir: direction,
    nodesep: 50,
    ranksep: 100,
    marginx: 40,
    marginy: 40,
  });
  g.setDefaultEdgeLabel(() => ({}));

  nodes.forEach((node) => {
    g.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  });
  edges.forEach((edge) => {
    g.setEdge(edge.source, edge.target);
  });

  dagre.layout(g);

  return nodes.map((node) => {
    const pos = g.node(node.id);
    if (pos) {
      return {
        ...node,
        position: {
          x: pos.x - NODE_WIDTH / 2,
          y: pos.y - NODE_HEIGHT / 2,
        },
      };
    }
    return node;
  });
}

// ====== Converters ======

function toFlowNode(
  asset: TopologyNode,
  highlightLabelId: number | null
): FlowNode {
  return {
    id: asset.id,
    type: 'asset',
    position: { x: 0, y: 0 },
    data: {
      asset,
      isSelected: false,
      highlightLabelId,
    },
  };
}

function toFlowEdge(
  edge: TopologyEdge,
  highlightLabelId: number | null
): FlowEdge {
  return {
    id: edge.id,
    source: edge.source,
    target: edge.target,
    type: 'asset',
    data: {
      relationType: edge.relationType,
      autoInferred: edge.autoInferred,
      label: edge.label,
      labelColor: edge.labelColor,
      highlightLabelId,
    },
  };
}

// ====== Node/Edge types ======

const nodeTypes: NodeTypes = { asset: AssetNode };
const edgeTypes: EdgeTypes = { asset: AssetEdge };

// ====== Main inner component ======

function AssetTopologyInner() {
  const { message } = App.useApp();
  const reactFlow = useReactFlow<FlowNode, FlowEdge>();
  const mode = useThemeStore((s) => s.mode);
  const isDark = mode === 'dark';

  const [refresh, setRefresh] = useState(false);
  const [selectedAsset, setSelectedAsset] = useState<TopologyNode | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [highlightLabelId, setHighlightLabelId] = useState<number | null>(null);
  const [filters, setFilters] = useState<{
    assetType?: string;
    status?: string;
  }>({});

  const [nodes, setNodes, onNodesChange] = useNodesState<FlowNode>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<FlowEdge>([]);

  // ====== Query ======

  const { data, isLoading, isFetching, refetch } = useQuery({
    queryKey: ['asset-topology', filters, refresh],
    queryFn: () => topologyApi.getTopology({ ...filters, refresh }),
    staleTime: refresh ? 0 : 60_000,
  });

  // Build nodes/edges when data or highlight changes
  useEffect(() => {
    if (!data) return;

    let flowNodes = data.nodes.map((n) => toFlowNode(n, highlightLabelId));
    const flowEdges = data.edges.map((e) => toFlowEdge(e, highlightLabelId));

    flowNodes = layoutWithDagre(flowNodes, flowEdges);

    setNodes(flowNodes);
    setEdges(flowEdges);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, highlightLabelId]);

  // ====== Handlers ======

  const onNodeClick: NodeMouseHandler<FlowNode> = useCallback(
    (_evt, node) => {
      setNodes((nds) =>
        nds.map((n) => ({
          ...n,
          data: { ...n.data, isSelected: n.id === node.id },
        }))
      );
      setSelectedAsset(node.data.asset);
      setDrawerOpen(true);
    },
    [setNodes]
  );

  const onPaneClick = useCallback(() => {
    setNodes((nds) =>
      nds.map((n) => ({ ...n, data: { ...n.data, isSelected: false } }))
    );
    setDrawerOpen(false);
  }, [setNodes]);

  const handleAutoLayout = useCallback(() => {
    setNodes((nds) => layoutWithDagre(nds, edges));
    setTimeout(() => reactFlow.fitView({ padding: 0.2, duration: 400 }), 50);
    message.info('已重新计算自动布局');
  }, [edges, setNodes, reactFlow, message]);

  const handleFitView = useCallback(() => {
    reactFlow.fitView({ padding: 0.2, duration: 400 });
  }, [reactFlow]);

  const handleRefresh = useCallback(() => {
    setRefresh((r) => !r);
    message.info(refresh ? '切换为读最新巡检报告' : '切换为实时拉取 Prometheus 指标');
  }, [refresh, message]);

  const handleForceRefresh = useCallback(() => {
    refetch();
    message.info('正在刷新拓扑数据');
  }, [refetch, message]);

  // ====== Derived ======

  const groupStats = useMemo(() => data?.groups ?? [], [data]);

  // All labels present in the topology (for highlight selector)
  const allLabels: TopologyLabel[] = useMemo(() => {
    if (!data) return [];
    const map = new Map<number, TopologyLabel>();
    data.nodes.forEach((n) => {
      (n.labels || []).forEach((l) => {
        if (!map.has(l.id)) map.set(l.id, l);
      });
    });
    return Array.from(map.values()).sort((a, b) => a.name.localeCompare(b.name));
  }, [data]);

  // Theme-aware styles for React Flow controls
  const controlsBg = isDark ? '#1e1e36' : '#ffffff';
  const controlsBorder = isDark ? '#2a2a4a' : '#d9d9d9';
  const controlsColor = isDark ? 'rgba(255,255,255,0.85)' : 'rgba(20,25,50,0.65)';
  const controlsHoverBg = isDark ? '#2a2a4a' : '#f0f3fa';
  const controlsSvgFill = isDark ? 'rgba(255,255,255,0.85)' : 'rgba(20,25,50,0.75)';
  const bgDotColor = isDark ? '#2a2a4a' : '#e0e0e0';
  const minimapMaskColor = isDark ? 'rgba(0,0,0,0.4)' : 'rgba(0,0,0,0.05)';

  // ====== Render ======

  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 500 }}>
        <Spin tip="加载拓扑数据中..." size="large" />
      </div>
    );
  }

  if (!data || data.nodes.length === 0) {
    return (
      <Empty description="暂无资产数据" style={{ padding: 80 }}>
        <Button icon={<ReloadOutlined />} onClick={handleForceRefresh}>
          刷新
        </Button>
      </Empty>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 200px)', minHeight: 500 }}>
      {/* Inline style overrides for React Flow Controls/MiniMap dark mode */}
      <style>{`
        .topology-canvas .react-flow__controls {
          box-shadow: 0 0 8px rgba(0,0,0,0.15);
        }
        .topology-canvas .react-flow__controls-button {
          background: ${controlsBg};
          border-bottom: 1px solid ${controlsBorder};
          color: ${controlsColor};
          fill: ${controlsSvgFill};
        }
        .topology-canvas .react-flow__controls-button:hover {
          background: ${controlsHoverBg};
        }
        .topology-canvas .react-flow__controls-button svg {
          fill: ${controlsSvgFill};
        }
        .topology-canvas .react-flow__minimap {
          background: ${controlsBg};
          border: 1px solid ${controlsBorder};
        }
      `}</style>

      {/* Toolbar */}
      <Card size="small" style={{ marginBottom: 8 }} styles={{ body: { padding: '8px 12px' } }}>
        <Space wrap>
          <Tooltip title="重新计算 dagre 自动布局">
            <Button icon={<LayoutOutlined />} onClick={handleAutoLayout}>
              自动布局
            </Button>
          </Tooltip>
          <Tooltip title="适应画布">
            <Button icon={<CompressOutlined />} onClick={handleFitView} />
          </Tooltip>
          <Tooltip title={refresh ? '当前：实时拉取 Prometheus 指标（点击切回读巡检报告）' : '当前：读最新巡检报告（点击切为实时拉取）'}>
            <Button
              type={refresh ? 'primary' : 'default'}
              icon={<ThunderboltOutlined />}
              onClick={handleRefresh}
            >
              {refresh ? '实时指标' : '巡检指标'}
            </Button>
          </Tooltip>
          <Tooltip title="刷新数据">
            <Button icon={<ReloadOutlined />} onClick={handleForceRefresh} loading={isFetching} />
          </Tooltip>

          <span style={{ color: '#999', margin: '0 4px' }}>|</span>

          <FilterOutlined />
          <Select
            placeholder="资产类型"
            allowClear
            style={{ width: 120 }}
            value={filters.assetType}
            onChange={(v) => setFilters((f) => ({ ...f, assetType: v }))}
            options={[
              { value: 'SERVER', label: '物理机' },
              { value: 'VM', label: '虚拟机' },
              { value: 'NETWORK', label: '网络设备' },
              { value: 'STORAGE', label: '存储设备' },
              { value: 'TERMINAL', label: '终端' },
            ]}
          />
          <Select
            placeholder="状态"
            allowClear
            style={{ width: 110 }}
            value={filters.status}
            onChange={(v) => setFilters((f) => ({ ...f, status: v }))}
            options={[
              { value: 'ACTIVE', label: '运行中' },
              { value: 'OFFLINE', label: '离线' },
              { value: 'MAINTENANCE', label: '维护中' },
            ]}
          />

          {allLabels.length > 0 && (
            <>
              <span style={{ color: '#999', margin: '0 4px' }}>|</span>
              <Select
                placeholder="高亮标签关联"
                allowClear
                showSearch
                style={{ width: 160 }}
                value={highlightLabelId}
                onChange={(v) => setHighlightLabelId(v ?? null)}
                options={allLabels.map((l) => ({
                  value: l.id,
                  label: (
                    <span>
                      <span
                        style={{
                          display: 'inline-block',
                          width: 8,
                          height: 8,
                          borderRadius: '50%',
                          backgroundColor: l.color,
                          marginRight: 6,
                        }}
                      />
                      {l.name}
                    </span>
                  ),
                }))}
              />
            </>
          )}

          <span style={{ marginLeft: 'auto', color: '#8c8c8c', fontSize: 12 }}>
            共 {data.nodes.length} 节点 / {data.edges.length} 关联
            {refresh && (
              <Tag color="processing" style={{ marginLeft: 8 }}>
                实时
              </Tag>
            )}
          </span>
        </Space>

        {/* Group stats chips */}
        <div style={{ marginTop: 6, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {groupStats.map((g) => (
            <Tag key={g.type} style={{ margin: 0 }}>
              {g.type}: {g.count}
            </Tag>
          ))}
        </div>
      </Card>

      {/* React Flow canvas */}
      <div
        className="topology-canvas"
        style={{ flex: 1, border: `1px solid ${isDark ? '#2a2a4a' : '#f0f0f0'}`, borderRadius: 6, overflow: 'hidden' }}
      >
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          onPaneClick={onPaneClick}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          minZoom={0.2}
          maxZoom={2.5}
          proOptions={{ hideAttribution: true }}
          nodesConnectable={false}
        >
          <Background variant={BackgroundVariant.Dots} gap={16} size={1} color={bgDotColor} />
          <Controls showInteractive={false} />
          <MiniMap
            pannable
            zoomable
            nodeColor={(n) => {
              const status = (n.data as AssetNodeData | undefined)?.asset?.status;
              if (status === 'ACTIVE') return '#52c41a';
              if (status === 'OFFLINE') return '#8c8c8c';
              if (status === 'MAINTENANCE') return '#fa8c16';
              return '#d9d9d9';
            }}
            maskColor={minimapMaskColor}
          />
        </ReactFlow>
      </div>

      {/* Detail drawer */}
      <Drawer
        title="资产详情"
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={420}
        destroyOnClose
      >
        {selectedAsset && <DetailPanel asset={selectedAsset} />}
      </Drawer>
    </div>
  );
}

// ====== Detail panel ======

function DetailPanel({ asset }: { asset: TopologyNode }) {
  const typeLabels: Record<string, string> = {
    SERVER: '物理机',
    VM: '虚拟机',
    NETWORK: '网络设备',
    STORAGE: '存储设备',
    TERMINAL: '终端',
  };
  const m = asset.metrics;

  return (
    <div>
      <Card size="small" title="基础信息" style={{ marginBottom: 12 }}>
        <p><strong>名称：</strong>{asset.name}</p>
        <p><strong>类型：</strong>{typeLabels[asset.type] || asset.type}</p>
        <p>
          <strong>状态：</strong>
          <StatusTag status={asset.status} type={asset.type === 'TERMINAL' ? 'terminal' : 'asset'} />
        </p>
        <p><strong>IP：</strong>{asset.ipAddress || '—'}</p>
        <p><strong>负责人：</strong>{asset.ownerName || '未分配'}</p>
      </Card>

      {(asset.type === 'SERVER' || asset.type === 'VM') && (
        <Card
          size="small"
          title={`资源指标${m.checkedAt ? ` · 巡检于 ${new Date(m.checkedAt).toLocaleString('zh-CN')}` : ''}`}
          style={{ marginBottom: 12 }}
        >
          <MetricRow label="CPU 使用率" value={m.cpu} />
          <MetricRow label="内存使用率" value={m.mem} />
          <MetricRow label="磁盘使用率" value={m.disk} />
          {m.load1 != null && (
            <p><strong>1分钟负载：</strong>{m.load1.toFixed(2)}</p>
          )}
          {m.memoryTotalMb != null && (
            <p><strong>内存总量：</strong>{Math.round(m.memoryTotalMb)} MB</p>
          )}
          {m.diskTotalGb != null && (
            <p><strong>磁盘总量：</strong>{m.diskTotalGb.toFixed(1)} GB</p>
          )}
          {m.hostStatus && (
            <p>
              <strong>巡检状态：</strong>
              <Tag color={m.hostStatus === 'ok' ? 'green' : m.hostStatus === 'warning' ? 'orange' : 'red'}>
                {m.hostStatus === 'ok' ? '正常' : m.hostStatus === 'warning' ? '警告' : '严重'}
              </Tag>
            </p>
          )}
        </Card>
      )}

      <Card size="small" title="配置信息" style={{ marginBottom: 12 }}>
        <p><strong>操作系统：</strong>{asset.osType || '—'} {asset.osVersion || ''}</p>
        <p><strong>CPU 核数：</strong>{asset.cpuCores ?? '—'}</p>
        <p><strong>内存：</strong>{asset.memoryGb ? `${asset.memoryGb} GB` : '—'}</p>
        <p><strong>磁盘：</strong>{asset.diskGb ? `${asset.diskGb} GB` : '—'}</p>
      </Card>

      {asset.labels?.length > 0 && (
        <Card size="small" title="标签（同标签自动关联）" style={{ marginBottom: 12 }}>
          <Space wrap>
            {asset.labels.map((l) => (
              <Tag key={l.id} color={l.color}>{l.name}</Tag>
            ))}
          </Space>
        </Card>
      )}
    </div>
  );
}

function MetricRow({ label, value }: { label: string; value?: number | null }) {
  let color = '#8c8c8c';
  let text = '—';
  if (value != null) {
    text = `${Math.round(value)}%`;
    if (value > 80) color = '#f5222d';
    else if (value > 60) color = '#fa8c16';
    else color = '#52c41a';
  }
  return (
    <p>
      <strong>{label}：</strong>
      <span style={{ color, fontWeight: 600 }}>{text}</span>
    </p>
  );
}

// ====== Exported wrapper with provider ======

export default function AssetTopology() {
  return (
    <ReactFlowProvider>
      <AssetTopologyInner />
    </ReactFlowProvider>
  );
}
