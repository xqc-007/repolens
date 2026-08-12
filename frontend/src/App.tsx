import { useState } from 'react';

import { Sidebar, type ViewName } from './components/Sidebar';
import { AskPage } from './features/ask/AskPage';
import './styles.css';

export default function App() {
  const [view, setView] = useState<ViewName>('ask');

  return (
    <div className="shell">
      <Sidebar active={view} onNavigate={setView} />
      <AskPage view={view} onNavigate={setView} />
    </div>
  );
}
