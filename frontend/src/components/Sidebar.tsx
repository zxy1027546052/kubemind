import { NavLink } from 'react-router-dom';

interface NavItem {
  path: string;
  label: string;
  icon: string;
}

const opsItems: NavItem[] = [
  { path: '/dashboard', label: '运维总览', icon: '◈' },
  { path: '/clusters', label: '集群管理', icon: '◫' },
  { path: '/topology', label: '业务拓扑', icon: '◬' },
  { path: '/alerts', label: '告警中心', icon: '⚡' },
];

const aiItems: NavItem[] = [
  { path: '/knowledge', label: '知识中心', icon: '▣' },
  { path: '/diagnosis', label: '智能诊断', icon: '◎' },
  { path: '/workflows', label: '工作流', icon: '▻' },
  { path: '/models', label: 'AI 模型', icon: '◉' },
];

const systemItems: NavItem[] = [
  { path: '/settings', label: '系统配置', icon: '⚙' },
];

function NavSection({ title, items }: { title: string; items: NavItem[] }) {
  return (
    <>
      <div className="nav-section">{title}</div>
      {items.map((item) => (
        <NavLink
          key={item.path}
          to={item.path}
          className={({ isActive }) =>
            `nav-item ${isActive ? 'active' : ''}`
          }
        >
          <span className="nav-icon">{item.icon}</span>
          {item.label}
        </NavLink>
      ))}
    </>
  );
}

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <span className="prompt-sign">[kubemind:~]$</span>
        <div className="brand-name">
          Kube<span>Mind</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        <NavSection title="运营管理" items={opsItems} />
        <NavSection title="智能引擎" items={aiItems} />
        <NavSection title="系统" items={systemItems} />
      </nav>

      <div className="sidebar-footer">
        <div className="cluster-status">
          <div className="status-dot" />
          <span className="status-label">CLUSTER</span>
          <span className="status-value">LIVE</span>
        </div>
      </div>
    </aside>
  );
}
