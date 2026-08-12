import {
  FolderGit2,
  GitCompareArrows,
  Home,
  ScanSearch,
  Settings2,
  Sparkles,
  TestTube2,
} from 'lucide-react';

export type ViewName = 'home' | 'repositories' | 'ask' | 'changes' | 'tests' | 'system';

const items: [ViewName, string, typeof Home][] = [
  ['home', 'Home', Home],
  ['repositories', 'Repositories', FolderGit2],
  ['ask', 'Ask', Sparkles],
  ['changes', 'Changes', GitCompareArrows],
  ['tests', 'Test Runs', TestTube2],
];

type SidebarProps = {
  active: ViewName;
  onNavigate: (view: ViewName) => void;
};

export function Sidebar({ active, onNavigate }: SidebarProps) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brandmark">
          <ScanSearch size={18} />
        </div>
        <div>
          <span>RepoLens</span>
          <small>Ask your codebase</small>
        </div>
      </div>

      <nav>
        {items.map(([key, label, Icon]) => (
          <button
            key={key}
            onClick={() => onNavigate(key)}
            className={active === key ? 'nav active' : 'nav'}
          >
            <Icon size={17} />
            <span>{label}</span>
          </button>
        ))}
      </nav>

      <button
        onClick={() => onNavigate('system')}
        className={active === 'system' ? 'nav system active' : 'nav system'}
      >
        <Settings2 size={17} />
        <span>System</span>
      </button>
    </aside>
  );
}
