import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { NavLink, Route, Routes, useNavigate } from "react-router-dom";
import { Activity, ArrowRight, BarChart3, CheckCircle2, ChevronDown, CircleAlert, FileCode2, GitPullRequest, Menu, Settings2, ShieldCheck, X } from "lucide-react";
import { getFixtures, getHealth, previewPullRequest } from "./api";
import type { ChangedFile, Fixture, Health, Preview } from "./types";

const navItems = [
  { to: "/", label: "Overview", icon: Activity },
  { to: "/review", label: "Review a PR", icon: GitPullRequest },
  { to: "/findings", label: "Findings", icon: ShieldCheck },
  { to: "/trace", label: "Agent trace", icon: Activity },
  { to: "/evaluation", label: "Evaluation", icon: BarChart3 },
  { to: "/configuration", label: "Configuration", icon: Settings2 },
];

function StatusPill({ health, compact = false }: { health?: Health; compact?: boolean }) {
  const state = health ? "online" : "offline";
  return <span className={`status-pill ${state}`} title={health ? `Backend connected in ${health.environment} mode` : "Backend unavailable. Check the API server."}>
    <span className="status-dot" /> {compact ? (health ? "API online" : "API offline") : (health ? "Backend connected" : "Backend unavailable")}
  </span>;
}

function AppShell({ health, children }: { health?: Health; children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return <div className="app-shell">
    <aside className={`sidebar ${open ? "open" : ""}`}>
      <div className="sidebar-heading"><span className="mark">AR</span><span>Agentic Review</span><button className="icon-button close-menu" onClick={() => setOpen(false)} aria-label="Close navigation"><X size={18} /></button></div>
      <div className="sidebar-kicker">Review workspace</div>
      <nav aria-label="Primary navigation">
        {navItems.map(({ to, label, icon: Icon }) => <NavLink key={to} to={to} end={to === "/"} onClick={() => setOpen(false)}><Icon size={17} strokeWidth={1.8} /><span>{label}</span></NavLink>)}
      </nav>
      <div className="sidebar-foot"><div className="demo-badge">DEMO MODE</div><p>No external credentials required.</p></div>
    </aside>
    {open && <button className="scrim" onClick={() => setOpen(false)} aria-label="Close navigation" />}
    <div className="workspace">
      <header className="topbar"><button className="icon-button menu-button" onClick={() => setOpen(true)} aria-label="Open navigation"><Menu size={21} /></button><div className="breadcrumb">Evidence workspace <span>/</span> {location.pathname === "/" ? "Overview" : "Review operations"}</div><StatusPill health={health} compact /></header>
      <main className="page-content">{children}</main>
    </div>
  </div>;
}

function PageHeader({ eyebrow, title, description, action }: { eyebrow: string; title: string; description: string; action?: React.ReactNode }) {
  return <div className="page-header"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{description}</p></div>{action}</div>;
}

function Overview({ health }: { health?: Health }) {
  const navigate = useNavigate();
  return <div className="content-stack"><PageHeader eyebrow="Workspace overview" title="See the signal clearly." description="A local-first review workspace for evidence, context, and decisions." />
    <section className="hero-strip"><div><span className="eyebrow">Next action</span><h2>Review a pull request</h2><p>Load a synthetic fixture to inspect changed files, line mapping, and repository context.</p></div><button className="primary-button" onClick={() => navigate("/review")}>Open review workspace <ArrowRight size={16} /></button></section>
    <div className="metric-grid"><Metric label="Backend" value={health ? "Connected" : "Unavailable"} detail={health ? `Environment: ${health.environment}` : "Start the API to continue"} tone={health ? "good" : "bad"} /><Metric label="Analysis mode" value={health?.demo_mode ? "Mock / offline" : "Configured"} detail="No live results are shown here" /><Metric label="Review runs" value="—" detail="Persistence arrives in a later milestone" /></div>
    <section className="section-band"><div><span className="eyebrow">Workspace state</span><h2>Ready for a fixture review</h2><p>There are no completed review runs yet. Fixture data is clearly labelled and remains local to this demo.</p></div><StatusPill health={health} /></section>
  </div>;
}

function Metric({ label, value, detail, tone }: { label: string; value: string; detail: string; tone?: string }) { return <div className="metric-card"><span className="label">{label}</span><strong className={tone}>{value}</strong><small>{detail}</small></div>; }

function validateReference(value: string) { return /^(?:[\w.-]+\/[\w.-]+#[1-9]\d*|https?:\/\/github\.com\/[\w.-]+\/[\w.-]+\/pull\/[1-9]\d*\/?$)/.test(value.trim()) ? null : "Use owner/repository#number or a GitHub pull-request URL."; }

function ReviewPage() {
  const [fixture, setFixture] = useState("small");
  const [reference, setReference] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const fixtures = useQuery({ queryKey: ["fixtures"], queryFn: getFixtures });
  const preview = useMutation({ mutationFn: previewPullRequest });
  const referenceError = reference ? validateReference(reference) : null;
  const load = () => { setSubmitted(true); if (!referenceError) preview.mutate(reference ? { reference: reference.trim() } : { fixture_id: fixture }); };
  return <div className="content-stack"><PageHeader eyebrow="Review operations" title="Inspect a pull request." description="Start with offline fixture data, then trace every line back to its source." action={<span className="demo-badge">SYNTHETIC DATA</span>} />
    <section className="review-controls panel"><div className="field-grid"><label>Fixture pull request<select value={fixture} onChange={(event) => setFixture(event.target.value)} disabled={preview.isPending}>{fixtures.data?.map((item) => <option key={item.fixture_id} value={item.fixture_id}>{item.title} · PR #{item.number}</option>)}</select></label><span className="or-divider">or</span><label>GitHub reference<input value={reference} onChange={(event) => setReference(event.target.value)} placeholder="owner/repository#42" aria-describedby="reference-help" disabled={preview.isPending} /><small id="reference-help">Demo mode accepts fixtures only. Live references require configured GitHub access.</small>{referenceError && <span className="field-error">{referenceError}</span>}</label></div><div className="control-footer"><span className="muted">{fixtures.isLoading ? "Loading fixtures…" : `${fixtures.data?.length ?? 0} offline fixtures available`}</span><button className="primary-button" onClick={load} disabled={preview.isPending || Boolean(referenceError)}>{preview.isPending ? "Loading…" : "Load pull request"} <ArrowRight size={16} /></button></div></section>
    {submitted && preview.isPending && <LoadingState />}
    {submitted && preview.isError && <ErrorState message={preview.error.message} onRetry={load} />}
    {submitted && preview.isSuccess && <PreviewView preview={preview.data} />}
    {!submitted && <div className="empty-state"><FileCode2 size={24} /><h2>No pull request loaded</h2><p>Choose a fixture or enter a valid reference to inspect metadata and changed code.</p></div>}
  </div>;
}

function LoadingState() { return <section className="panel loading-state" aria-label="Loading pull request"><span className="skeleton wide" /><span className="skeleton" /><span className="skeleton large" /></section>; }
function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) { return <section className="empty-state error-state"><CircleAlert size={24} /><h2>Could not load pull request</h2><p>{message}</p><button className="secondary-button" onClick={onRetry}>Retry</button></section>; }

function PreviewView({ preview }: { preview: Preview }) { return <div className="preview-stack"><section className="panel pr-summary"><div><span className="eyebrow">Pull request #{preview.metadata.number}</span><h2>{preview.metadata.title}</h2><p>{preview.metadata.user?.login ? `Opened by ${preview.metadata.user.login}` : "Synthetic fixture pull request"}</p></div><button className="secondary-button" disabled title="Analysis arrives in a later milestone">Start review <ArrowRight size={15} /></button><div className="sha-row"><span>BASE <code>{preview.metadata.base.sha}</code></span><span>HEAD <code>{preview.metadata.head.sha}</code></span></div></section>{preview.context.incomplete && <section className="notice"><CircleAlert size={19} /><div><strong>Context incomplete</strong><p>{preview.context.incomplete_reasons.join("; ")}</p></div></section>}<section className="panel chunk-panel"><div className="panel-heading"><div><span className="eyebrow">Repository context</span><h2>Chunk plan</h2></div><span className="muted">{preview.context.files_included}/{preview.context.files_considered} files included</span></div><div className="chunk-list">{preview.context.chunk_plan.map((chunk) => <span key={`${chunk.file_path}-${chunk.start_line}`}><FileCode2 size={14} /> {chunk.file_path} <b>lines {chunk.start_line}–{chunk.end_line}</b></span>)}</div></section><section><div className="panel-heading"><div><span className="eyebrow">Changed surface</span><h2>Diff viewer</h2></div><span className="muted">{preview.changed_files.length} files</span></div><div className="file-list">{preview.changed_files.map((file) => <DiffFile key={file.filename} file={file} />)}</div></section></div>; }

function DiffFile({ file }: { file: ChangedFile }) { return <article className="diff-file"><div className="file-heading"><span><FileCode2 size={16} />{file.filename}</span><span className="change-count"><i>+{file.additions}</i><em>−{file.deletions}</em></span></div><div className="diff-scroll">{file.hunks.length ? file.hunks.map((hunk, index) => <div className="hunk" key={`${file.filename}-${index}`}><div className="hunk-label">@@ -{hunk.old_start},{hunk.old_count} +{hunk.new_start},{hunk.new_count} @@</div>{hunk.lines.map((line, lineIndex) => <div className={`diff-line ${line.kind}`} key={`${lineIndex}-${line.content}`}><span>{line.old_line ?? ""}</span><span>{line.new_line ?? ""}</span><b>{line.kind === "added" ? "+" : line.kind === "removed" ? "−" : " "}</b><code>{line.content || " "}</code></div>)}</div>) : <p className="diff-empty">No patch available for this file.</p>}</div></article>; }

function Placeholder({ title, icon: Icon }: { title: string; icon: typeof Activity }) { return <div className="content-stack"><PageHeader eyebrow="Later milestone" title={title} description="This view is reserved for verified review results and execution evidence." /><div className="empty-state placeholder"><Icon size={28} /><h2>Coming in a later milestone</h2><p>This control is intentionally inactive until the review pipeline produces real data. No sample results are presented as live.</p><button className="secondary-button" disabled title="Available after the review pipeline is implemented">Unavailable</button></div></div>; }

function Configuration({ health }: { health?: Health }) { return <div className="content-stack"><PageHeader eyebrow="Runtime configuration" title="Configuration." description="Safe runtime information only. Secrets never leave the backend." /><section className="settings-grid panel"><Metric label="Environment" value={health?.environment ?? "Unavailable"} detail="Read from backend health" /><Metric label="Mode" value={health?.demo_mode ? "Demo / offline" : "Configured"} detail="No credentials exposed" /><Metric label="GitHub comments" value="Disabled" detail="Publication is off by default" /></section><section className="empty-state compact"><Settings2 size={23} /><h2>Unwired controls stay disabled</h2><p>Provider selection, thresholds, scanners, and retry settings will be connected after the review pipeline is implemented.</p></section></div>; }

export default function App() { const health = useQuery({ queryKey: ["health"], queryFn: getHealth, retry: false }); return <AppShell health={health.data}><Routes><Route path="/" element={<Overview health={health.data} />} /><Route path="/review" element={<ReviewPage />} /><Route path="/configuration" element={<Configuration health={health.data} />} /><Route path="/findings" element={<Placeholder title="Findings" icon={ShieldCheck} />} /><Route path="/trace" element={<Placeholder title="Agent trace" icon={Activity} />} /><Route path="/evaluation" element={<Placeholder title="Evaluation" icon={BarChart3} />} /></Routes></AppShell>; }
