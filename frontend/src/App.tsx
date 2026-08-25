import { useEffect, useMemo, useState } from "react";
import {
  ArrowUpRight,
  Check,
  ChevronRight,
  CircleAlert,
  Clock3,
  Command,
  Database,
  Globe2,
  LayoutDashboard,
  Link2,
  Search,
  Send,
  Settings2,
  Sparkles,
  Users,
  X,
} from "lucide-react";

const fallbackCatalog: Connector[] = [
  { provider: "google_drive", display_name: "Google Drive", auth_family: "google", capabilities: ["read", "search", "index"], status: "implemented", setup_mode: "oauth", note: "Documents, files, and shared context." },
  { provider: "google_gmail", display_name: "Gmail", auth_family: "google", capabilities: ["read", "search", "index"], status: "implemented", setup_mode: "oauth", note: "Email context for decisions and follow-ups." },
  { provider: "google_calendar", display_name: "Google Calendar", auth_family: "google", capabilities: ["read", "search", "sync_meetings"], status: "implemented", setup_mode: "oauth", note: "Events, attendees, and meeting context." },
  { provider: "google_meet", display_name: "Google Meet", auth_family: "google", capabilities: ["read", "index_transcripts"], status: "implemented", setup_mode: "oauth", note: "Conference records and available transcripts." },
  { provider: "google_maps", display_name: "Google Maps", auth_family: "google_api_key", capabilities: ["search_places", "place_details"], status: "implemented_foundation", setup_mode: "api_key", note: "Places lookup through a restricted API key." },
  { provider: "google_keep", display_name: "Google Notes", auth_family: "google_workspace_admin", capabilities: ["read", "index"], status: "implemented_foundation", setup_mode: "oauth", note: "Workspace-admin-approved Keep access." },
  { provider: "slack", display_name: "Slack", auth_family: "slack", capabilities: ["read", "search", "index"], status: "implemented", setup_mode: "oauth", note: "Read-only channel history and context." },
  { provider: "microsoft_teams", display_name: "Microsoft Teams", auth_family: "microsoft", capabilities: ["read", "sync_meetings"], status: "implemented", setup_mode: "oauth", note: "Calendar-backed meetings and transcripts." },
  { provider: "discord", display_name: "Discord", auth_family: "discord", capabilities: ["read", "index"], status: "catalog_foundation", setup_mode: "oauth", note: "Requires bot installation and guild permissions." },
  { provider: "linkedin", display_name: "LinkedIn", auth_family: "linkedin", capabilities: ["read_profile"], status: "catalog_foundation", setup_mode: "oauth", note: "Capabilities depend on product approval." },
  { provider: "reddit", display_name: "Reddit", auth_family: "reddit", capabilities: ["read", "search"], status: "catalog_foundation", setup_mode: "oauth", note: "Requires a Reddit developer application." },
  { provider: "twitter_x", display_name: "X / Twitter", auth_family: "twitter_x", capabilities: ["read", "search"], status: "catalog_foundation", setup_mode: "oauth", note: "Requires an X developer project and quota." },
  { provider: "facebook", display_name: "Facebook", auth_family: "meta", capabilities: ["read_pages"], status: "catalog_foundation", setup_mode: "oauth", note: "Meta permissions and app review apply." },
];

type Connector = {
  provider: string;
  display_name: string;
  auth_family: string;
  capabilities: string[];
  status: string;
  setup_mode: "oauth" | "api_key" | "bot_token";
  note: string;
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

const connectedProviders = new Set(["google_drive", "google_gmail", "google_calendar", "slack"]);

async function loadCatalog(): Promise<Connector[]> {
  try {
    const response = await fetch("/connectors/catalog");
    if (!response.ok) throw new Error("catalog unavailable");
    return await response.json();
  } catch {
    return fallbackCatalog;
  }
}

function App() {
  const [catalog, setCatalog] = useState<Connector[]>(fallbackCatalog);
  const [activeSection, setActiveSection] = useState("overview");
  const [search, setSearch] = useState("");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<RagResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState("");

  useEffect(() => {
    loadCatalog().then(setCatalog);
  }, []);

  const filtered = useMemo(
    () => catalog.filter((item) => item.display_name.toLowerCase().includes(search.toLowerCase())),
    [catalog, search],
  );

  const showToast = (message: string) => {
    setToast(message);
    window.setTimeout(() => setToast(""), 3500);
  };

  const submitQuery = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!question.trim()) return;
    setLoading(true);
    setAnswer(null);
    try {
      const response = await fetch("/rag/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ workspace_id: "replace-with-session-workspace", question }),
      });
      if (!response.ok) throw new Error("RAG endpoint requires authenticated dashboard proxy");
      setAnswer(await response.json());
    } catch {
      showToast("Connect the dashboard’s authenticated server proxy before querying memory.");
    } finally {
      setLoading(false);
    }
  };

  const setup = (item: Connector) => {
    if (item.status === "catalog_foundation") {
      showToast(`${item.display_name} is cataloged; provider OAuth/app approval is still required.`);
      return;
    }
    showToast(`Use /connect_${item.provider.replace("google_", "")} in Telegram to continue setup.`);
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><div className="brand-mark"><Sparkles size={17} /></div><span>SERA</span></div>
        <div className="workspace-switcher"><div className="workspace-avatar">A</div><div><strong>Acme workspace</strong><span>Personal command center</span></div><ChevronRight size={15} /></div>
        <p className="eyebrow nav-label">Workspace</p>
        <nav>
          <NavItem active={activeSection === "overview"} icon={<LayoutDashboard size={17} />} label="Overview" onClick={() => setActiveSection("overview")} />
          <NavItem active={activeSection === "connections"} icon={<Link2 size={17} />} label="Connections" onClick={() => setActiveSection("connections")} />
          <NavItem active={activeSection === "memory"} icon={<Database size={17} />} label="Memory search" onClick={() => setActiveSection("memory")} />
          <NavItem active={activeSection === "detective"} icon={<CircleAlert size={17} />} label="Work detective" onClick={() => setActiveSection("detective")} />
        </nav>
        <p className="eyebrow nav-label">Manage</p>
        <nav><NavItem icon={<Settings2 size={17} />} label="Settings" onClick={() => showToast("Settings will be available after web session auth is connected.")} /></nav>
        <div className="sidebar-bottom"><div className="status-dot" /> <span>All systems operational</span></div>
      </aside>

      <main className="main-content">
        <header className="topbar"><div className="breadcrumbs"><span>Workspace</span><ChevronRight size={14} /><strong>{activeSection === "overview" ? "Overview" : activeSection[0].toUpperCase() + activeSection.slice(1)}</strong></div><div className="topbar-actions"><button className="icon-button"><Command size={17} /></button><div className="profile">AK</div></div></header>

        <section className="hero-section"><div><p className="eyebrow">Tuesday, August 25, 2026</p><h1>Your work, understood.</h1><p className="hero-subtitle">Sera remembers what happened across your tools and helps you decide what to do next.</p></div><button className="primary-button" onClick={() => setActiveSection("memory")}><Sparkles size={16} /> Ask Sera</button></section>

        <section className="metric-grid"><Metric label="Connected sources" value={connectedProviders.size.toString()} detail="of 13 available" icon={<Link2 size={17} />} tone="violet" /><Metric label="Indexed context" value="2,481" detail="documents & messages" icon={<Database size={17} />} tone="blue" /><Metric label="Time recovered" value="6.4h" detail="this month" icon={<Clock3 size={17} />} tone="green" /><Metric label="Open patterns" value="3" detail="ready to automate" icon={<Sparkles size={17} />} tone="orange" /></section>

        {activeSection === "memory" ? <MemoryPanel question={question} setQuestion={setQuestion} submitQuery={submitQuery} loading={loading} answer={answer} /> : activeSection === "detective" ? <DetectivePanel /> : <>
          <section className="section-heading"><div><p className="eyebrow">Your context layer</p><h2>Connected sources</h2></div><button className="secondary-button" onClick={() => setActiveSection("connections")}>Manage connections <ArrowUpRight size={15} /></button></section>
          <div className="connector-toolbar"><div className="search-box"><Search size={16} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search integrations" /></div><div className="filter-pill"><Globe2 size={15} /> All providers</div></div>
          <section className="connector-grid">{filtered.map((item) => <ConnectorCard key={item.provider} item={item} connected={connectedProviders.has(item.provider)} onSetup={setup} />)}</section>
        </>}
      </main>
      {toast && <div className="toast"><Check size={16} />{toast}<button onClick={() => setToast("")}><X size={14} /></button></div>}
    </div>
  );
}

function NavItem({ icon, label, active = false, onClick }: { icon: React.ReactNode; label: string; active?: boolean; onClick: () => void }) { return <button className={`nav-item ${active ? "active" : ""}`} onClick={onClick}>{icon}<span>{label}</span>{active && <div className="active-bar" />}</button>; }
function Metric({ label, value, detail, icon, tone }: { label: string; value: string; detail: string; icon: React.ReactNode; tone: string }) { return <div className="metric-card"><div className={`metric-icon ${tone}`}>{icon}</div><div><p>{label}</p><div className="metric-value">{value}</div><span>{detail}</span></div></div>; }
function StatusBadge({ connected, status }: { connected: boolean; status: string }) { const label = connected ? "Connected" : status === "catalog_foundation" ? "Foundation" : "Setup needed"; return <span className={`status-badge ${connected ? "connected" : "pending"}`}><span className="status-badge-dot" />{label}</span>; }
function ConnectorCard({ item, connected, onSetup }: { item: Connector; connected: boolean; onSetup: (item: Connector) => void }) { return <article className="connector-card"><div className="connector-card-top"><div className={`provider-logo ${item.auth_family}`}>{providerInitial(item.display_name)}</div><StatusBadge connected={connected} status={item.status} /></div><h3>{item.display_name}</h3><p>{item.note}</p><div className="capability-row">{item.capabilities.slice(0, 3).map((capability) => <span key={capability}>{capability.replace(/_/g, " ")}</span>)}</div><button className={`card-action ${item.status === "catalog_foundation" ? "muted" : ""}`} onClick={() => onSetup(item)}>{item.status === "catalog_foundation" ? "View requirements" : connected ? "Manage connection" : "Continue setup"}<ChevronRight size={15} /></button></article>; }
function providerInitial(name: string) { return name.split(" ").map((word) => word[0]).slice(0, 2).join(""); }
function MemoryPanel({ question, setQuestion, submitQuery, loading, answer }: { question: string; setQuestion: (value: string) => void; submitQuery: (event: React.FormEvent) => void; loading: boolean; answer: RagResponse | null }) { return <section className="memory-layout"><div className="memory-intro"><div className="memory-orb"><Sparkles size={23} /></div><p className="eyebrow">Sera memory</p><h2>Ask across your connected work.</h2><p>Search Gmail, Drive, Slack, Teams, Calendar, Meet, and Notes through one workspace-scoped Gemini query.</p><div className="memory-source-list"><span><Check size={13} /> Workspace-scoped</span><span><Check size={13} /> Source citations</span><span><Check size={13} /> Read-only context</span></div></div><div className="query-card"><form onSubmit={submitQuery}><label htmlFor="question">What do you want to remember?</label><textarea id="question" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="What did we decide about Project Alpha?" rows={4} /><div className="query-footer"><span><Database size={14} /> All connected sources</span><button className="primary-button" type="submit" disabled={loading}>{loading ? "Searching…" : "Ask Sera"}<Send size={15} /></button></div></form>{answer && <div className="answer-block"><div className="answer-label">Answer</div><p>{answer.answer}</p><div className="source-list">{answer.sources.map((source, index) => <a href={source.url || source.drive_link || "#"} key={`${source.title}-${index}`} target="_blank" rel="noreferrer"><span>{source.source || "Source"}</span><strong>{source.title}</strong><small>{source.date || ""}</small></a>)}</div></div>}</div></section>; }
function DetectivePanel() { return <section className="detective-panel"><div className="detective-heading"><div className="memory-orb orange"><Sparkles size={21} /></div><div><p className="eyebrow">Work detective</p><h2>Patterns worth your attention</h2><p>Sera watches for repeated, deterministic work and surfaces automation opportunities for your approval.</p></div></div><div className="pattern-list"><Pattern title="Weekly sales report" frequency="12 times" time="9.2 hours" tone="orange" /><Pattern title="Customer CSV processing" frequency="18 times" time="6.7 hours" tone="blue" /><Pattern title="Meeting follow-up emails" frequency="23 times" time="4.1 hours" tone="violet" /></div></section>; }
function Pattern({ title, frequency, time, tone }: { title: string; frequency: string; time: string; tone: string }) { return <div className="pattern-row"><div className={`pattern-icon ${tone}`}><Sparkles size={17} /></div><div className="pattern-main"><strong>{title}</strong><span>{frequency} · {time} total</span></div><button className="text-button">Analyze <ArrowUpRight size={14} /></button></div>; }

export default App;
