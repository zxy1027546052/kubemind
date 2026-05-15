import { type AgentEvent, type RuntimeEvent } from '../hooks/useChatOpsStream';

interface DagNode {
  name: string;
  status: 'pending' | 'running' | 'success' | 'failed';
  duration_ms?: number;
}

interface Props {
  events: RuntimeEvent[];
}

function buildDagNodes(events: RuntimeEvent[]): DagNode[] {
  const agents = new Map<string, DagNode>();

  for (const event of events) {
    if (event.type === 'agent.started') {
      const e = event as AgentEvent;
      agents.set(e.agent, { name: e.agent, status: 'running' });
    } else if (event.type === 'agent.completed') {
      const e = event as AgentEvent;
      const existing = agents.get(e.agent);
      if (existing) {
        existing.status = 'success';
        existing.duration_ms = e.duration_ms;
      }
    } else if (event.type === 'agent.failed') {
      const e = event as AgentEvent;
      const existing = agents.get(e.agent);
      if (existing) {
        existing.status = 'failed';
      }
    }
  }

  return Array.from(agents.values());
}

const STATUS_COLORS: Record<string, string> = {
  pending: '#505470',
  running: '#00e5ff',
  success: '#39ff14',
  failed: '#ff3366',
};

export default function DagView({ events }: Props) {
  const nodes = buildDagNodes(events);

  if (nodes.length === 0) return null;

  const nodeWidth = 140;
  const nodeHeight = 36;
  const gapY = 20;
  const startX = 20;
  const startY = 20;
  const connectorX = startX + nodeWidth + 16;
  const childX = connectorX + 24;

  const plannerNode = nodes[0];
  const childNodes = nodes.slice(1);

  const totalHeight = startY + nodeHeight + (childNodes.length > 0 ? gapY + childNodes.length * (nodeHeight + gapY) : 0) + 10;
  const totalWidth = childX + nodeWidth + 20;

  const plannerCenterY = startY + nodeHeight / 2;

  return (
    <div className="dag-view">
      <div className="dag-header">
        <span className="dag-title">Execution DAG</span>
        <span className="dag-count">{nodes.length} nodes</span>
      </div>
      <svg
        width="100%"
        height={totalHeight}
        viewBox={`0 0 ${totalWidth} ${totalHeight}`}
        className="dag-svg"
      >
        {/* Planner (root) node */}
        <DagNodeRect
          x={startX}
          y={startY}
          width={nodeWidth}
          height={nodeHeight}
          node={plannerNode}
        />

        {/* Child nodes with connectors */}
        {childNodes.map((child, i) => {
          const childY = startY + nodeHeight + gapY + i * (nodeHeight + gapY);
          const childCenterY = childY + nodeHeight / 2;

          return (
            <g key={child.name}>
              {/* Connector line: horizontal from planner, then vertical, then horizontal to child */}
              <path
                d={`M ${startX + nodeWidth} ${plannerCenterY}
                    L ${connectorX} ${plannerCenterY}
                    L ${connectorX} ${childCenterY}
                    L ${childX} ${childCenterY}`}
                fill="none"
                stroke={STATUS_COLORS[child.status]}
                strokeWidth="1.5"
                strokeOpacity="0.5"
                strokeDasharray={child.status === 'running' ? '4 3' : 'none'}
              />
              <DagNodeRect
                x={childX}
                y={childY}
                width={nodeWidth}
                height={nodeHeight}
                node={child}
              />
            </g>
          );
        })}
      </svg>
    </div>
  );
}

function DagNodeRect({ x, y, width, height, node }: {
  x: number;
  y: number;
  width: number;
  height: number;
  node: DagNode;
}) {
  const color = STATUS_COLORS[node.status];
  const displayName = node.name.replace(/Agent$/, '');

  return (
    <g>
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        rx={4}
        fill="rgba(15, 17, 25, 0.9)"
        stroke={color}
        strokeWidth="1.5"
        strokeOpacity={node.status === 'running' ? 0.8 : 0.5}
      />
      {/* Status dot */}
      <circle
        cx={x + 12}
        cy={y + height / 2}
        r={3.5}
        fill={color}
        opacity={node.status === 'running' ? 1 : 0.8}
      >
        {node.status === 'running' && (
          <animate attributeName="opacity" values="1;0.4;1" dur="1.2s" repeatCount="indefinite" />
        )}
      </circle>
      {/* Name */}
      <text
        x={x + 22}
        y={y + height / 2 + 1}
        fill="#e4e6f0"
        fontSize="10"
        fontFamily="'JetBrains Mono', monospace"
        dominantBaseline="middle"
      >
        {displayName}
      </text>
      {/* Duration */}
      {node.duration_ms != null && (
        <text
          x={x + width - 8}
          y={y + height / 2 + 1}
          fill="#8b8fa8"
          fontSize="9"
          fontFamily="'JetBrains Mono', monospace"
          dominantBaseline="middle"
          textAnchor="end"
        >
          {node.duration_ms}ms
        </text>
      )}
    </g>
  );
}
