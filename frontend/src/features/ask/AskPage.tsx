import { useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import {
  AlertTriangle,
  ArrowUp,
  Braces,
  Check,
  CheckCircle2,
  ChevronDown,
  CircleDot,
  Database,
  ExternalLink,
  FileCode2,
  GitBranch,
  GitCompareArrows,
  Globe2,
  LoaderCircle,
  LockKeyhole,
  RefreshCw,
  Search,
  ServerCog,
  Shield,
  ShieldCheck,
  TestTube2,
  Workflow,
} from 'lucide-react';

import type { ViewName } from '../../components/Sidebar';
import { api } from '../../lib/api';
import type {
  EventRow,
  GitHubRepo,
  GitHubStatus,
  Health,
  Repo,
  Run,
  TestResult,
  ToolDescriptor,
} from '../../types';

const suggestions = [
  'Explain this project to me',
  'What will break if I change authentication?',
  'Fix the login bug and show me the diff',
];

type AskPageProps = {
  view: ViewName;
  onNavigate: (view: ViewName) => void;
};

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : 'Something went wrong';
}

export function AskPage({ view, onNavigate }: AskPageProps) {
  const [repo, setRepo] = useState<Repo | null>(null);
  const [question, setQuestion] = useState('Why is login failing?');
  const [run, setRun] = useState<Run | null>(null);
  const [events, setEvents] = useState<EventRow[]>([]);
  const [busy, setBusy] = useState(false);
  const [test, setTest] = useState<TestResult | null>(null);
  const [error, setError] = useState('');

  const [repoUrl, setRepoUrl] = useState('');
  const [connecting, setConnecting] = useState(false);
  const [githubStatus, setGithubStatus] = useState<GitHubStatus | null>(null);
  const [githubRepos, setGithubRepos] = useState<GitHubRepo[]>([]);
  const [loadingRepos, setLoadingRepos] = useState(false);
  const [repoSearch, setRepoSearch] = useState('');

  const [health, setHealth] = useState<Health | null>(null);
  const [tools, setTools] = useState<ToolDescriptor[]>([]);

  useEffect(() => {
    api.demo().then(setRepo).catch((err) => setError(errorMessage(err)));
    refreshGitHubStatus();
    api.health().then(setHealth).catch(() => undefined);
    api.tools().then((result) => setTools(result.tools)).catch(() => undefined);
  }, []);

  const filteredRepos = useMemo(() => {
    const needle = repoSearch.trim().toLowerCase();
    if (!needle) return githubRepos;
    return githubRepos.filter((item) => item.full_name.toLowerCase().includes(needle));
  }, [githubRepos, repoSearch]);

  async function refreshGitHubStatus() {
    try {
      setGithubStatus(await api.githubStatus());
    } catch (err) {
      setGithubStatus({
        configured: false,
        connected: false,
        error: errorMessage(err),
      });
    }
  }

  async function loadGitHubRepos() {
    setLoadingRepos(true);
    setError('');
    try {
      setGithubRepos(await api.githubRepos());
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoadingRepos(false);
    }
  }

  async function ask() {
    if (!repo || !question.trim()) return;

    setBusy(true);
    setRun(null);
    setEvents([]);
    setTest(null);
    setError('');
    onNavigate('ask');

    try {
      const created = await api.ask(repo.id, question);
      setRun(created);

      const eventSource = new EventSource(api.eventsUrl(created.id));
      eventSource.onmessage = (event) => {
        setEvents((current) => [...current, JSON.parse(event.data)]);
      };

      const timer = window.setInterval(async () => {
        try {
          const latest = await api.run(created.id);
          setRun(latest);

          if (latest.status === 'completed' || latest.status === 'failed') {
            window.clearInterval(timer);
            eventSource.close();
            setBusy(false);
          }
        } catch (err) {
          window.clearInterval(timer);
          eventSource.close();
          setError(errorMessage(err));
          setBusy(false);
        }
      }, 450);
    } catch (err) {
      setError(errorMessage(err));
      setBusy(false);
    }
  }

  async function runTests() {
    if (!run) return;

    setTest({ status: 'running' });
    try {
      setTest(await api.tests(run.id, 'pytest'));
    } catch (err) {
      setTest({ status: 'error', output_summary: errorMessage(err) });
    }
  }

  async function connectRepo() {
    if (!repoUrl.trim()) return;

    setConnecting(true);
    setError('');
    try {
      selectConnectedRepo(await api.connect(repoUrl.trim()));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setConnecting(false);
    }
  }

  async function connectGitHubRepo(item: GitHubRepo) {
    setConnecting(true);
    setError('');
    try {
      const connected = await api.connectGitHub(item.full_name, item.default_branch);
      selectConnectedRepo(connected);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setConnecting(false);
    }
  }

  function selectConnectedRepo(connected: Repo) {
    setRepo(connected);
    setRepoUrl('');
    setRun(null);
    setEvents([]);
    setTest(null);
    onNavigate('ask');
  }

  function eventIcon(type: string) {
    if (type === 'completed' || type === 'tool_completed') return <Check size={14} />;
    if (type === 'guardrail') return <Shield size={14} />;
    if (type === 'tool_started') return <Search size={14} />;
    if (type === 'plan') return <Workflow size={14} />;
    return <CircleDot size={12} />;
  }

  const latestEvents = events.slice(-8);
  const header = (
    <header className="top">
      <div>
        <div className="eyebrow">CONNECTED REPOSITORY</div>
        <h1>{repo?.name || 'Loading repository…'}</h1>
      </div>

      {repo && (
        <div className="repoMeta">
          <span>
            <GitBranch size={14} />
            {repo.branch}
          </span>
          <span>{repo.file_count} files</span>
          <span className="ready">Ready</span>
          <button className="connectBtn" onClick={() => onNavigate('repositories')}>
            Change repository
          </button>
        </div>
      )}
    </header>
  );

  if (view === 'home') {
    return (
      <main className="page">
        {header}
        <section className="homeHero">
          <div className="eyebrow">REPOLENS</div>
          <h2>Understand your codebase without living in an IDE.</h2>
          <p>
            RepoLens investigates repositories with constrained tools, retrieves only relevant
            context, and keeps every proposed change reviewable.
          </p>
          <button className="primary" onClick={() => onNavigate('ask')}>
            Ask your codebase <ArrowUp size={16} />
          </button>
        </section>

        <section className="featureGrid">
          <Feature
            icon={<Search />}
            title="Scoped retrieval"
            text="Ranks files, symbols and dependencies instead of sending the whole repository to the model."
          />
          <Feature
            icon={<ShieldCheck />}
            title="Controlled tools"
            text="Read, propose and execution permissions are enforced by application logic."
          />
          <Feature
            icon={<GitCompareArrows />}
            title="Review-first changes"
            text="Generated fixes are shown as diffs before tests or any future write action."
          />
        </section>

        <section className="statusStrip">
          <div>
            <strong>{repo?.file_count || 0}</strong>
            <span>files mapped</span>
          </div>
          <div>
            <strong>{repo?.languages?.length || 0}</strong>
            <span>languages detected</span>
          </div>
          <div>
            <strong>{health?.llm_mode || '—'}</strong>
            <span>LLM mode</span>
          </div>
          <div>
            <strong>{githubStatus?.connected ? 'Connected' : 'Demo'}</strong>
            <span>GitHub</span>
          </div>
        </section>
      </main>
    );
  }

  if (view === 'repositories') {
    return (
      <main className="page">
        {header}
        <section className="pageIntro">
          <div className="eyebrow">REPOSITORIES</div>
          <h2>Choose what RepoLens can inspect.</h2>
          <p>
            GitHub credentials remain server-side. V1 clones repositories into isolated local
            workspaces for analysis.
          </p>
        </section>

        <section className="connectPanel card standalone">
          <div className="connectHeader">
            <div>
              {githubStatus?.connected ? (
                <div className="ghIdentity">
                  {githubStatus.avatar_url && <img src={githubStatus.avatar_url} alt="" />}
                  <div>
                    <strong>Connected as {githubStatus.login}</strong>
                    <span>Read access is limited by your GitHub token.</span>
                  </div>
                </div>
              ) : (
                <div className="ghSetup">
                  <strong>
                    {githubStatus?.configured
                      ? 'GitHub token needs attention'
                      : 'GitHub token not configured'}
                  </strong>
                  <span>
                    Add a fine-grained token to <code>backend/.env</code> as{' '}
                    <code>GITHUB_TOKEN</code>.
                  </span>
                  {githubStatus?.error && <small>{githubStatus.error}</small>}
                </div>
              )}
            </div>

            <button
              className="iconButton"
              onClick={async () => {
                const status = await api.githubStatus().catch(() => null);
                if (status) setGithubStatus(status);
                if (status?.connected) await loadGitHubRepos();
              }}
              aria-label="Refresh GitHub connection"
            >
              <RefreshCw size={15} />
            </button>
          </div>

          {githubStatus?.connected && (
            <>
              <div className="repoPickerTop">
                <input
                  value={repoSearch}
                  onChange={(event) => setRepoSearch(event.target.value)}
                  placeholder="Search your repositories…"
                />
                <button onClick={loadGitHubRepos} disabled={loadingRepos}>
                  {loadingRepos ? 'Loading…' : 'Refresh repos'}
                </button>
              </div>

              <div className="repoList">
                {filteredRepos.slice(0, 30).map((item) => (
                  <button
                    className="repoChoice"
                    key={item.full_name}
                    onClick={() => connectGitHubRepo(item)}
                    disabled={connecting}
                  >
                    <span className="repoChoiceIcon">
                      {item.private ? <LockKeyhole size={16} /> : <Globe2 size={16} />}
                    </span>
                    <span className="repoChoiceText">
                      <strong>{item.full_name}</strong>
                      <small>
                        {item.language || 'Repository'} · {item.default_branch}
                      </small>
                    </span>
                    <span className="repoPrivacy">{item.private ? 'Private' : 'Public'}</span>
                  </button>
                ))}

                {!loadingRepos && githubRepos.length === 0 && (
                  <div className="emptyMini">No repositories loaded yet. Click “Refresh repos”.</div>
                )}
              </div>
            </>
          )}

          <div className="manualConnect">
            <div className="sectionTitle">PUBLIC REPOSITORY URL</div>
            <p>Connect a public repository without using authenticated GitHub access.</p>
            <div className="connectRow">
              <input
                value={repoUrl}
                onChange={(event) => setRepoUrl(event.target.value)}
                placeholder="https://github.com/owner/repository"
              />
              <button onClick={connectRepo} disabled={connecting}>
                {connecting ? 'Connecting…' : 'Connect'}
              </button>
            </div>
          </div>
        </section>
      </main>
    );
  }

  if (view === 'changes') {
    return (
      <main className="page">
        {header}
        <section className="pageIntro">
          <div className="eyebrow">CHANGES</div>
          <h2>Review proposed code changes.</h2>
          <p>
            RepoLens never pushes automatically in V1. A patch is an artifact for review, not
            permission to write.
          </p>
        </section>

        {run?.patch ? (
          <PatchCard run={run} test={test} onRunTests={runTests} />
        ) : (
          <EmptyState
            icon={<GitCompareArrows />}
            title="No proposed changes yet"
            text="Ask RepoLens to fix a bug or generate tests. Any patch will appear here before execution."
            action="Ask for a change"
            onAction={() => onNavigate('ask')}
          />
        )}
      </main>
    );
  }

  if (view === 'tests') {
    return (
      <main className="page">
        {header}
        <section className="pageIntro">
          <div className="eyebrow">TEST RUNS</div>
          <h2>Validate proposed changes before trust.</h2>
          <p>
            Execution is an explicit permission boundary and is kept separate from read-only
            investigation.
          </p>
        </section>

        {test ? (
          <section className={`card testPanel ${test.status}`}>
            <div className="testHeadline">
              <div className="testIcon">
                <TestTube2 size={20} />
              </div>
              <div>
                <div className="sectionTitle">CURRENT SESSION</div>
                <h3>
                  {test.status === 'running'
                    ? 'Tests are running'
                    : test.status === 'passed'
                      ? 'Tests passed'
                      : test.status === 'failed'
                        ? 'Tests failed'
                        : 'Test execution error'}
                </h3>
              </div>
            </div>

            <div className="testStats">
              <span>
                <strong>{test.command || 'pytest'}</strong>command
              </span>
              {typeof test.exit_code === 'number' && (
                <span>
                  <strong>{test.exit_code}</strong>exit code
                </span>
              )}
              {typeof test.duration_ms === 'number' && (
                <span>
                  <strong>{test.duration_ms} ms</strong>duration
                </span>
              )}
            </div>

            {test.output_summary && (
              <details open>
                <summary>
                  Test output <ChevronDown size={15} />
                </summary>
                <pre>{test.output_summary}</pre>
              </details>
            )}
          </section>
        ) : (
          <EmptyState
            icon={<TestTube2 />}
            title="No test run yet"
            text="Tests run only after a proposed patch exists and you explicitly approve execution."
            action={run?.patch ? 'Run tests' : 'Ask for a change'}
            onAction={run?.patch ? runTests : () => onNavigate('ask')}
          />
        )}
      </main>
    );
  }

  if (view === 'system') {
    return (
      <main className="page">
        {header}
        <section className="pageIntro">
          <div className="eyebrow">SYSTEM</div>
          <h2>Runtime and safety boundaries.</h2>
          <p>Operational state is visible without exposing credentials or private repository content.</p>
        </section>

        <section className="systemGrid">
          <article className="card">
            <div className="sectionTitle">RUNTIME</div>
            <InfoRow label="API" value={health?.status === 'ok' ? 'Healthy' : 'Unavailable'} good={health?.status === 'ok'} />
            <InfoRow label="Environment" value={health?.environment || '—'} />
            <InfoRow label="Repository mode" value={health?.repository_mode || '—'} />
            <InfoRow label="LLM mode" value={health?.llm_mode || '—'} />
          </article>

          <article className="card">
            <div className="sectionTitle">GITHUB</div>
            <InfoRow label="Connection" value={githubStatus?.connected ? 'Connected' : 'Not connected'} good={githubStatus?.connected} />
            <InfoRow label="Account" value={githubStatus?.login || '—'} />
            <InfoRow label="Credential location" value="Server environment" />
          </article>

          <article className="card toolsCard">
            <div className="sectionTitle">TOOL PERMISSIONS</div>
            {tools.map((tool) => (
              <div className="toolRow" key={tool.name}>
                <span>
                  <Braces size={14} />
                  {tool.name}
                </span>
                <span className={`permission ${tool.permission}`}>{tool.permission}</span>
                <span className={tool.enabled ? 'enabled' : 'disabled'}>
                  {tool.enabled ? 'Enabled' : 'Disabled'}
                </span>
              </div>
            ))}
          </article>

          <article className="card">
            <div className="sectionTitle">V1 GUARDRAILS</div>
            <div className="guardrail">
              <Shield size={16} />
              <span>Repository content is treated as untrusted data.</span>
            </div>
            <div className="guardrail">
              <Database size={16} />
              <span>Context is bounded instead of sending whole repositories.</span>
            </div>
            <div className="guardrail">
              <ServerCog size={16} />
              <span>GitHub write capability remains disabled.</span>
            </div>
          </article>
        </section>
      </main>
    );
  }

  return (
    <main className="page">
      {header}

      <section className="hero">
        <div className="modePill">
          <ShieldCheck size={13} /> Controlled agent · read-only investigation
        </div>
        <h2>What would you like to understand or change?</h2>
        <p>Ask in plain English. RepoLens gathers evidence first and keeps every change reviewable.</p>

        <div className="askbox">
          <textarea
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Ask your codebase…"
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                ask();
              }
            }}
          />
          <div className="askfooter">
            <span>
              <ShieldCheck size={14} /> Repository-scoped tools
            </span>
            <button aria-label="Ask RepoLens" onClick={ask} disabled={busy}>
              {busy ? <LoaderCircle className="spin" size={18} /> : <ArrowUp size={18} />}
            </button>
          </div>
        </div>

        <div className="suggestions">
          {suggestions.map((item) => (
            <button onClick={() => setQuestion(item)} key={item}>
              {item}
            </button>
          ))}
        </div>
      </section>

      {error && (
        <div className="error">
          <AlertTriangle size={17} />
          {error}
        </div>
      )}

      {(busy || events.length > 0) && (
        <section className="activity card">
          <div className="activityHead">
            <div>
              <div className="sectionTitle">AGENT ACTIVITY</div>
              <strong>{busy ? 'Investigating repository' : 'Investigation complete'}</strong>
            </div>
            <span className={busy ? 'livePill' : 'donePill'}>{busy ? 'Live' : 'Complete'}</span>
          </div>

          <div className="timeline">
            {latestEvents.map((event, index) => (
              <div className="event" key={event.id}>
                <div className={`eventIcon ${event.event_type === 'completed' ? 'complete' : ''}`}>
                  {eventIcon(event.event_type)}
                </div>
                <div>
                  <span>{event.message}</span>
                  <small>
                    {index === latestEvents.length - 1 && busy ? 'Current step' : 'Recorded activity'}
                  </small>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {run?.answer && <AnswerResult run={run} onChanges={() => onNavigate('changes')} />}
      {run?.patch && <PatchCard run={run} test={test} onRunTests={runTests} />}
    </main>
  );
}

function Feature({ icon, title, text }: { icon: ReactNode; title: string; text: string }) {
  return (
    <article className="featureCard">
      <div>{icon}</div>
      <h3>{title}</h3>
      <p>{text}</p>
    </article>
  );
}

function EmptyState({
  icon,
  title,
  text,
  action,
  onAction,
}: {
  icon: ReactNode;
  title: string;
  text: string;
  action: string;
  onAction: () => void;
}) {
  return (
    <section className="emptyState card">
      <div className="emptyIcon">{icon}</div>
      <h3>{title}</h3>
      <p>{text}</p>
      <button className="secondary" onClick={onAction}>
        {action}
      </button>
    </section>
  );
}

function InfoRow({ label, value, good }: { label: string; value: string; good?: boolean }) {
  return (
    <div className="infoRow">
      <span>{label}</span>
      <strong className={good ? 'good' : ''}>{value}</strong>
    </div>
  );
}

function AnswerResult({ run, onChanges }: { run: Run; onChanges: () => void }) {
  const answer = run.answer!;

  return (
    <>
      <section className="answer">
        <div className="answerHead">
          <div>
            <div className="eyebrow">SUMMARY</div>
            <h2>{answer.summary}</h2>
          </div>
          <div className="confidence">
            <strong>{Math.round(answer.confidence * 100)}%</strong>
            <span>confidence</span>
          </div>
        </div>

        <div className="answerGrid">
          <article className="card">
            <div className="sectionTitle">WHAT I FOUND</div>
            <ul>
              {answer.what_i_found.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </article>

          <article className="card">
            <div className="sectionTitle">WHY THIS IS HAPPENING</div>
            <p>{answer.why}</p>
          </article>

          {answer.suggested_fix && (
            <article className="card">
              <div className="sectionTitle">SUGGESTED FIX</div>
              <p>{answer.suggested_fix}</p>
            </article>
          )}

          <article className="card">
            <div className="sectionTitle">IMPACT</div>
            {answer.impact.length ? (
              answer.impact.map((item) => (
                <div className="impact" key={item}>
                  <CheckCircle2 size={15} />
                  {item}
                </div>
              ))
            ) : (
              <p className="muted">No material impact identified yet.</p>
            )}
          </article>
        </div>
      </section>

      <section className="card files">
        <div className="sectionTitle">FILES INVOLVED</div>
        {answer.files.map((file) => (
          <details key={file.path}>
            <summary>
              <span>
                <FileCode2 size={16} />
                {file.path}
              </span>
              <ChevronDown size={15} />
            </summary>
            <p>
              {file.reason}
              {file.start_line ? ` · lines ${file.start_line}–${file.end_line}` : ''}
            </p>
          </details>
        ))}
      </section>

      {run.patch && (
        <div className="reviewPrompt">
          <div>
            <strong>Reviewable patch prepared</strong>
            <span>Nothing has been written to GitHub.</span>
          </div>
          <button className="secondary" onClick={onChanges}>
            Review changes <ExternalLink size={14} />
          </button>
        </div>
      )}
    </>
  );
}

function PatchCard({
  run,
  test,
  onRunTests,
}: {
  run: Run;
  test: TestResult | null;
  onRunTests: () => void;
}) {
  const patch = run.patch!;

  return (
    <section className="card patch">
      <div className="patchHead">
        <div>
          <div className="sectionTitle">PROPOSED CHANGES</div>
          <h3>{patch.summary}</h3>
          <p>
            {patch.affected_files.length} file{patch.affected_files.length === 1 ? '' : 's'} changed
            {' · '}
            {patch.risk_level} risk · {Math.round(patch.confidence * 100)}% confidence
          </p>
        </div>

        <button className="secondary" onClick={onRunTests} disabled={test?.status === 'running'}>
          <TestTube2 size={16} />
          {test?.status === 'running' ? 'Running…' : 'Run tests'}
        </button>
      </div>

      <div className="patchFiles">
        {patch.affected_files.map((file) => (
          <span key={file}>
            <FileCode2 size={13} />
            {file}
          </span>
        ))}
      </div>

      <details>
        <summary>
          View proposed diff <ChevronDown size={15} />
        </summary>
        <pre>{patch.unified_diff}</pre>
      </details>

      {test && (
        <div className={`testResult ${test.status}`}>
          <strong>
            {test.status === 'running'
              ? 'Running tests…'
              : test.status === 'passed'
                ? 'Tests passed'
                : test.status === 'failed'
                  ? 'Tests failed'
                  : 'Test error'}
          </strong>
          {test.output_summary && <pre>{test.output_summary}</pre>}
        </div>
      )}
    </section>
  );
}
