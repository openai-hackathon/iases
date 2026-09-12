import { useEffect, useRef, useState } from 'react';
import { Check, Clock3, Info, Pause, Play, Plus, Radio, RotateCcw, ShieldCheck, SlidersHorizontal, SquareArrowOutUpRight, TriangleAlert, Waves, X, Zap } from 'lucide-react';
import { clock, initialState, injectIncident, isActive, metrics, orderedQueue, scenarios, setPolicy, setPriority, slack, tick } from './simulation';
import RecoveryFlow from './RecoveryFlow';
import type { IncidentKind, Policy } from './simulation';

const policyLabels: Record<Policy, string> = { aware: 'Deadline + priority', priority: 'Priority first', fifo: 'First in, first out' };
const scenarioIcons = { power: Zap, cooling: Waves, network: Radio };

export default function App() {
  const [state, setState] = useState(initialState);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [kind, setKind] = useState<IncidentKind>('power');
  const [zone, setZone] = useState('Zone B');
  const [windowSeconds, setWindowSeconds] = useState(90);
  const [selectedId, setSelectedId] = useState('BG-02');
  const [priorityDraft, setPriorityDraft] = useState(35);
  const dialog = useRef<HTMLDialogElement>(null);
  const inspector = useRef<HTMLDialogElement>(null);
  const summary = metrics(state);
  const activeIncidents = state.incidents.filter(incident => isActive(incident, state.tasks));
  const running = state.tasks.filter(task => task.status === 'running');
  const selected = state.tasks.find(task => task.id === selectedId);
  const queue = orderedQueue(state);
  const incidentLimit = activeIncidents.length >= 3 || state.incidents.length >= 12;

  useEffect(() => {
    if (!playing) return;
    const interval = window.setInterval(() => setState(current => tick(current)), 1000 / speed);
    return () => window.clearInterval(interval);
  }, [playing, speed]);

  useEffect(() => {
    if (state.tasks.every(task => task.status === 'complete')) setPlaying(false);
  }, [state.tasks]);

  useEffect(() => { if (selected) setPriorityDraft(selected.priority); }, [selected?.id, selected?.priority]);

  function triggerIncident(event: React.SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    setState(current => injectIncident(current, kind, zone, windowSeconds));
    setPlaying(true);
    dialog.current?.close();
  }

  function reset() {
    setState(initialState());
    setPlaying(false);
    setSelectedId('BG-02');
    setSpeed(1);
  }

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">Skip to recovery console</a>
      <div className="workspace simple-workspace">
        <main id="main">
          <div className="page-heading"><div><h1>Fab Relay <span className="mock-tag">Simulation</span></h1><p>Trigger an incident. See which agents run first.</p></div><button className="button primary" onClick={() => dialog.current?.showModal()} disabled={incidentLimit}><Plus size={18} />Trigger incident</button></div>

          <section className="simulation-bar" aria-label="Simulation controls"><div className="clock-label"><Clock3 size={18} /><span>Simulation time<strong>T+{clock(state.now)}</strong></span><span className={`play-status ${playing ? 'is-playing' : ''}`}>{playing ? 'Running' : 'Paused'}</span></div><div className="simulation-controls"><button className="button compact" onClick={() => setPlaying(!playing)} disabled={!running.length && !queue.length}>{playing ? <Pause size={15} /> : <Play size={15} />}{playing ? 'Pause' : 'Play'}</button><label className="speed-control"><span className="sr-only">Simulation speed</span><select value={speed} onChange={event => setSpeed(Number(event.target.value))}><option value={1}>1× speed</option><option value={4}>4× speed</option></select></label><span className="control-divider" /><button className="text-button" onClick={reset}><RotateCcw size={15} />Reset</button></div></section>

          <div className="simple-status" aria-label="Simulation results">
            <span><b>{activeIncidents.length}</b> active incidents</span>
            <span className={summary.missed ? 'text-red' : ''}><b>{summary.missed}</b> deadlines missed</span>
            <span><b>{summary.maxBackgroundWait}s</b> longest routine wait</span>
          </div>
          {incidentLimit && <p className="limit-note">{activeIncidents.length >= 3 ? 'Three incidents are active. Let tasks finish before adding another.' : 'Incident history is full. Reset to start again.'}</p>}
          <div className="simple-content">
            <section className="panel dispatch-panel" id="dispatch">              <div className="policy-toolbar"><span><SlidersHorizontal size={16} />Run first</span><label><span className="sr-only">Scheduling policy</span><select value={state.policy} onChange={event => setState(current => setPolicy(current, event.target.value as Policy))}>{Object.entries(policyLabels).map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label></div>
              <RecoveryFlow state={state} selectedId={selectedId} onSelect={id => { setSelectedId(id); inspector.current?.showModal(); }} />
              <div className="policy-note"><Info size={15} /><span>{state.policy === 'aware' ? 'Lowest slack first; importance breaks ties. Slack = deadline − now − remaining work.' : state.policy === 'priority' ? 'Highest importance first; arrival order breaks ties.' : 'Arrival order only. Importance and deadlines do not change the queue.'}</span></div>
            </section>

          </div>

          <details className="simple-details"><summary>Activity log</summary><section className="panel activity-panel" id="activity"><ol className="event-list">{state.events.slice(0, 8).map(event => <li key={event.id}><time>T+{clock(event.at)}</time><span className={`event-dot ${event.tone}`} /><p>{event.text}</p></li>)}</ol></section></details>
          <details className="simple-details"><summary>About this demo</summary><p>Independent TSMC-inspired demo. No TSMC affiliation or live equipment connection. CPU, RAM, agents and priorities are simulated. No Codex, LM or BT fit is connected.</p></details>
          <footer><span><ShieldCheck size={14} />Simulation only. No live fab, Codex or equipment connection.</span><a href="https://github.com/openai-hackathon/fab-recovery-demo" target="_blank" rel="noreferrer">Demo repository<SquareArrowOutUpRight size={13} /></a></footer>
        </main>
      </div>

      <dialog ref={inspector} className="incident-dialog task-dialog" aria-label="Task details">{selected && <section className="panel inspector"><div className="panel-heading"><h2>Task details</h2><button className="icon-button" onClick={() => inspector.current?.close()} aria-label="Close task details"><X size={20} /></button></div><div className="inspector-body"><span className="task-id">{selected.id} · {selected.zone}</span><h3>{selected.title}</h3><dl className="task-facts"><div><dt>Session</dt><dd>{selected.session}</dd></div><div><dt>Estimated work</dt><dd>{selected.duration}s</dd></div><div><dt>Queue wait</dt><dd>{(selected.startedAt ?? state.now) - selected.queuedAt}s</dd></div><div><dt>{selected.status === 'complete' ? 'Finished at' : 'Current slack'}</dt><dd className={selected.status !== 'complete' && slack(selected, state.now) < 0 ? 'text-red' : ''}>{selected.status === 'complete' ? `T+${clock(selected.finishedAt ?? 0)}` : `${slack(selected, state.now)}s`}</dd></div></dl><div className="override-heading"><label htmlFor="importance">Operator importance</label><output htmlFor="importance">{priorityDraft}<span>/100</span></output></div><input id="importance" type="range" min="0" max="100" value={priorityDraft} disabled={selected.status !== 'queued'} onChange={event => setPriorityDraft(Number(event.target.value))} /><div className="range-labels"><span>Routine</span><span>Critical</span></div><button className="button override-button" disabled={selected.status !== 'queued' || priorityDraft === selected.priority} onClick={() => setState(current => setPriority(current, selected.id, priorityDraft))}>Apply priority override<Check size={15} /></button><p className="fine-print">Manual mock score, not a BT fit. Overrides affect queued tasks only. Deadline mode still favors lower slack.</p></div></section>}</dialog>
      <dialog ref={dialog} className="incident-dialog" aria-labelledby="incident-title"><form onSubmit={triggerIncident}><div className="dialog-top"><span className="dialog-icon"><TriangleAlert size={23} /></span><button type="button" className="icon-button" onClick={() => dialog.current?.close()} aria-label="Close incident form"><X size={20} /></button></div><h2 id="incident-title">Trigger a simulated incident</h2><p>Inject a scenario. Three mock agents will enter the shared queue. Running work keeps its CPU and RAM reservations.</p><fieldset><legend>Incident scenario</legend><div className="scenario-options">{(Object.keys(scenarios) as IncidentKind[]).map(value => { const Icon = scenarioIcons[value]; return <label key={value} className={`scenario-option ${kind === value ? 'chosen' : ''}`}><input type="radio" name="scenario" value={value} checked={kind === value} onChange={() => setKind(value)} /><Icon size={21} /><span><strong>{scenarios[value].name}</strong><small>{scenarios[value].detail}</small></span><span className="radio-mark">{kind === value && <Check size={12} />}</span></label>; })}</div></fieldset><div className="form-grid"><label>Impacted zone<select value={zone} onChange={event => setZone(event.target.value)}><option>Zone A</option><option>Zone B</option><option>Zone C</option></select></label><label>Response window (simulated s)<input type="number" required min="30" max="180" step="1" value={windowSeconds} onChange={event => setWindowSeconds(Number(event.target.value))} /></label></div><div className="dialog-note"><Info size={17} /><span>Task deadlines use 50%, 80% and 100% of this window. Values are fictional, not operational guidance.</span></div><div className="dialog-actions"><button className="button" type="button" onClick={() => dialog.current?.close()}>Cancel</button><button className="button danger" type="submit" disabled={incidentLimit}><Zap size={17} />Trigger incident &amp; run</button></div></form></dialog>
    </div>
  );
}
