import { useEffect, useMemo, useState } from "react";
import {
  ArrowUpRight, Check, ChevronRight, CircleAlert, Clock3, Command,
  Database, Globe2, LayoutDashboard, Link2, Search, Send, Settings2,
  Sparkles, X,
} from "lucide-react";

type Connector = {
  provider: string;
  display_name: string;
  auth_family?: string;
  capabilities: string[];
  status: string;
  setup_mode: "oauth" | "api_key" | "bot_token";
  note: string;
  last_sync_at?: string | null;
};

type SessionUser = {
  user_id: string;
  workspace_id: string;
  email?: string | null;
  name?: string | null;
};

type Source = {
  title: string;
  source?: string;
  date?: string;
  person?: string;
  url?: string;
  drive_link?: string;
};

type RagResponse = { answer: string; sources: Source[] };

async function getSession(): Promise<SessionUser | null> {
  const response = await fetch("/auth/me", { credentials: "include" });
  if (response.status === 401) return null;
  if (!response.ok) throw new Error("Could not load session");
  return response.json();
}

async function getConnectors(): Promise<Connector[]> {
  const response = await fetch("/auth/connectors", { credentials: "include" });
  if (!response.ok) throw new Error("Could not load connectors");
  const data = await response.json();
  return data.connectors;
}

function App() {
  const [session, setSession] = useState<SessionUser | null>(null);
  const [catalog, setCatalog] = useState<Connector[]>([]);
  const [authLoading, setAuthLoading] = useState(true);
  const [activeSection, setActiveSection] = useState("overview");
  const [search, setSearch] = useState("");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<RagResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState("");

  useEffect(() => {
    Promise.resolve()
      .then(async () => {
        const current = await getSession();
        setSession(current);
        if (current) setCatalog(await getConnectors());
      })
      .catch(() => showToastMessage(setToast, "Could not load the authenticated workspace."))
      .finally(() => setAuthLoading(false));
  }, []);

  const filtered = useMemo(
    () => catalog.filter((item) => item.display_name.toLowerCase().includes(search.toLowerCase())),
    [catalog, search],
  );
  const connectedCount = catalog.filter((item) => item.status === "connected").length;

  const submitQuery = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!question.trim()) return;
    setLoading(true);
    setAnswer(null);
    try {
      const response = await fetch("/auth/rag/query", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      if (response.status === 401) {
        setSession(null);
        throw new Error("Your session expired");
      }
      if (!response.ok) throw new Error("Memory search failed");
      setAnswer(await response.json());
    } catch (error) {
      showToastMessage(setToast, error instanceof Error ? error.message : "Memory search failed");
    } finally {
      setLoading(false);
    }
  };

  const setup = (item: Connector) => {
    if (item.setup_mode === "api_key") {
      showToastMessage(setToast, `${item.display_name} is configured by the server administrator.`);
      return;
    }
    if (item.status === "catalog_foundation") {
      showToastMessage(setToast, `${item.display_name} needs provider-specific app approval before setup.`);
      return;
    }
    window.location.assign(`/auth/connectors/${encodeURIComponent(item.provider)}/start`);
  };

  if (authLoading) return <div className="login-screen"><div className="brand"><div className="brand-mark"><Sparkles size={17} /></div><span>SERA</span></div><p>Loading your secure workspace…</p></div>;
  if (!session) return <LoginScreen />;

  const initials = (session.name || session.email || "S").split(/\s+/).map((part) => part[0]).slice(0, 2).join("").toUpperCase();
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><div className="brand-mark"><Sparkles size={17} /></div><span>SERA</span></div>
        <div className="workspace-switcher"><div className="workspace-avatar">{initials.slice(0, 1)}</div><div><strong>{session.name || session.email || "My workspace"}</strong><span>Personal command center</span></div><ChevronRight size={15} /></div>
        <p className="eyebrow nav-label">Workspace</p>
        <nav>
          <NavItem active={activeSection === "overview"} icon={<LayoutDashboard size={17} />} label="Overview" onClick={() => setActiveSection("overview")} />
          <NavItem active={activeSection === "connections"} icon={<Link2 size={17} />} label="Connections" onClick={() => setActiveSection("connections")} />
          <NavItem active={activeSection === "memory"} icon={<Database size={17} />} label="Memory search" onClick={() => setActiveSection("memory")} />
          <NavItem active={activeSection === "detective"} icon={<CircleAlert size={17} />} label="Work detective" onClick={() => setActiveSection("detective")} />
        </nav>
        <p className="eyebrow nav-label">Manage</p>
        <nav><NavItem icon={<Settings2 size={17} />} label="Settings" onClick={() => showToastMessage(setToast, "Settings will be available in the next dashboard slice.")} /></nav>
        <div className="sidebar-bottom"><div className="status-dot" /> <span>Authenticated workspace</span></div>
      </aside>

      <main className="main-content">
        <header className="topbar"><div className="breadcrumbs"><span>Workspace</span><ChevronRight size={14} /><strong>{activeSection === "overview" ? "Overview" : activeSection[0].toUpperCase() + activeSection.slice(1)}</strong></div><div className="topbar-actions"><button className="icon-button"><Command size={17} /></button><div className="profile">{initials}</div></div></header>
        <section className="hero-section"><div><p className="eyebrow">Secure workspace</p><h1>Your work, understood.</h1><p className="hero-subtitle">Sera remembers what happened across your tools and helps you decide what to do next.</p></div><button className="primary-button" onClick={() => setActiveSection("memory")}><Sparkles size={16} /> Ask Sera</button></section>
        <section className="metric-grid"><Metric label="Connected sources" value={connectedCount.toString()} detail={`of ${catalog.length} available`} icon={<Link2 size={17} />} tone="violet" /><Metric label="Indexed context" value="—" detail="live workspace count coming next" icon={<Database size={17} />} tone="blue" /><Metric label="Time recovered" value="—" detail="work detective sync pending" icon={<Clock3 size={17} />} tone="green" /><Metric label="Open patterns" value="—" detail="work detective sync pending" icon={<Sparkles size={17} />} tone="orange" /></section>

        {activeSection === "memory" ? <MemoryPanel question={question} setQuestion={setQuestion} submitQuery={submitQuery} loading={loading} answer={answer} /> : activeSection === "detective" ? <DetectivePanel /> : <>
          <section className="section-heading"><div><p className="eyebrow">Your context layer</p><h2>Connected sources</h2></div><button className="secondary-button" onClick={() => setActiveSection("connections")}>Manage connections <ArrowUpRight size={15} /></button></section>
          <div className="connector-toolbar"><div className="search-box"><Search size={16} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search integrations" /></div><div className="filter-pill"><Globe2 size={15} /> All providers</div></div>
          <section className="connector-grid">{filtered.map((item) => <ConnectorCard key={item.provider} item={item} connected={item.status === "connected"} onSetup={setup} />)}</section>
        </>}
      </main>
      {toast && <div className="toast"><Check size={16} />{toast}<button onClick={() => setToast("")}><X size={14} /></button></div>}
    </div>
  );
}

function LoginScreen() { return <div className="login-screen"><div className="login-card"><div className="brand login-brand"><div className="brand-mark"><Sparkles size={17} /></div><span>SERA</span></div><p className="eyebrow">Your context layer</p><h1>Remember more. Repeat less.</h1><p>Sign in with Google to securely connect your workspace sources and ask Sera about your work.</p><a className="primary-button login-button" href="/auth/google/start"><Globe2 size={16} /> Continue with Google</a><small>Access is scoped to your authenticated Sera workspace.</small></div></div>; }
function showToastMessage(setToast: (value: string) => void, message: string) { setToast(message); window.setTimeout(() => setToast(""), 3500); }
function NavItem({ icon, label, active = false, onClick }: { icon: React.ReactNode; label: string; active?: boolean; onClick: () => void }) { return <button className={`nav-item ${active ? "active" : ""}`} onClick={onClick}>{icon}<span>{label}</span>{active && <div className="active-bar" />}</button>; }
function Metric({ label, value, detail, icon, tone }: { label: string; value: string; detail: string; icon: React.ReactNode; tone: string }) { return <div className="metric-card"><div className={`metric-icon ${tone}`}>{icon}</div><div><p>{label}</p><div className="metric-value">{value}</div><span>{detail}</span></div></div>; }
function StatusBadge({ connected, status }: { connected: boolean; status: string }) { const label = connected ? "Connected" : status === "catalog_foundation" ? "Foundation" : "Setup needed"; return <span className={`status-badge ${connected ? "connected" : "pending"}`}><span className="status-badge-dot" />{label}</span>; }
function ConnectorCard({ item, connected, onSetup }: { item: Connector; connected: boolean; onSetup: (item: Connector) => void }) { return <article className="connector-card"><div className="connector-card-top"><div className={`provider-logo ${item.auth_family || item.setup_mode}`}>{providerInitial(item.display_name)}</div><StatusBadge connected={connected} status={item.status} /></div><h3>{item.display_name}</h3><p>{item.note}</p><div className="capability-row">{item.capabilities.slice(0, 3).map((capability) => <span key={capability}>{capability.replace(/_/g, " ")}</span>)}</div><button className={`card-action ${item.status === "catalog_foundation" ? "muted" : ""}`} onClick={() => onSetup(item)}>{item.status === "catalog_foundation" ? "View requirements" : connected ? "Manage connection" : "Continue setup"}<ChevronRight size={15} /></button></article>; }
function providerInitial(name: string) { return name.split(" ").map((word) => word[0]).slice(0, 2).join(""); }
function MemoryPanel({ question, setQuestion, submitQuery, loading, answer }: { question: string; setQuestion: (value: string) => void; submitQuery: (event: React.FormEvent) => void; loading: boolean; answer: RagResponse | null }) { return <section className="memory-layout"><div className="memory-intro"><div className="memory-orb"><Sparkles size={23} /></div><p className="eyebrow">Sera memory</p><h2>Ask across your connected work.</h2><p>Search Gmail, Drive, Slack, Teams, Calendar, Meet, and Notes through one authenticated Gemini query.</p><div className="memory-source-list"><span><Check size={13} /> Workspace-scoped</span><span><Check size={13} /> Source citations</span><span><Check size={13} /> Server-side proxy</span></div></div><div className="query-card"><form onSubmit={submitQuery}><label htmlFor="question">What do you want to remember?</label><textarea id="question" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="What did we decide about Project Alpha?" rows={4} /><div className="query-footer"><span><Database size={14} /> Connected workspace sources</span><button className="primary-button" type="submit" disabled={loading}>{loading ? "Searching…" : "Ask Sera"}<Send size={15} /></button></div></form>{answer && <div className="answer-block"><div className="answer-label">Answer</div><p>{answer.answer}</p><div className="source-list">{answer.sources.map((source, index) => <a href={source.url || source.drive_link || "#"} key={`${source.title}-${index}`} target="_blank" rel="noreferrer"><span>{source.source || "Source"}</span><strong>{source.title}</strong><small>{source.date || ""}</small></a>)}</div></div>}</div></section>; }
function DetectivePanel() { return <section className="detective-panel"><div className="detective-heading"><div className="memory-orb orange"><Sparkles size={21} /></div><div><p className="eyebrow">Work detective</p><h2>Patterns worth your attention</h2><p>Sera watches for repeated, deterministic work and surfaces automation opportunities for your approval.</p></div></div><div className="pattern-list"><Pattern title="Weekly sales report" frequency="Sync work events to see frequency" time="pending" tone="orange" /><Pattern title="Customer CSV processing" frequency="Sync work events to see frequency" time="pending" tone="blue" /><Pattern title="Meeting follow-up emails" frequency="Sync work events to see frequency" time="pending" tone="violet" /></div></section>; }
function Pattern({ title, frequency, time, tone }: { title: string; frequency: string; time: string; tone: string }) { return <div className="pattern-row"><div className={`pattern-icon ${tone}`}><Sparkles size={17} /></div><div className="pattern-main"><strong>{title}</strong><span>{frequency} · {time}</span></div><button className="text-button">Analyze <ArrowUpRight size={14} /></button></div>; }

export default App;
