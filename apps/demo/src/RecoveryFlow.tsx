import { ArrowRight, CheckCheck, Cpu, TriangleAlert } from 'lucide-react';
import { capacity, clock, isActive, orderedQueue, resourceUsage, scenarios } from './simulation';
import type { Simulation, Task } from './simulation';
import './recovery-flow.css';

type Props = {
  state: Simulation;
  selectedId: string;
  onSelect: (id: string) => void;
};

export default function RecoveryFlow({ state, selectedId, onSelect }: Props) {
  const queue = orderedQueue(state);
  const running = state.tasks.filter(task => task.status === 'running');
  const used = resourceUsage(state);
  const head = queue[0];
  const blocked = head && (head.cpu > capacity.cpu - used.cpu || head.ram > capacity.ram - used.ram);
  const completed = state.tasks.filter(task => task.status === 'complete');
  const incidents = state.incidents.filter(incident => isActive(incident, state.tasks));

  function taskCard(task: Task, position?: number) {
    const remainingWindow = task.deadline - state.now;
    return <button key={task.id} className={`flow-task ${task.incidentId ? 'recovery-task' : 'routine-task'} ${selectedId === task.id ? 'flow-selected' : ''}`} onClick={() => onSelect(task.id)} aria-pressed={selectedId === task.id}>
      <span className="flow-task-top"><span>{position !== undefined ? `#${position} ${position === 1 ? 'UP NEXT' : 'WAITING'}` : 'RUNNING NOW'}</span><b>Priority {task.priority}</b></span>
      <strong>{task.title}</strong>
      <span className="flow-agent">{task.agent} · {task.zone}</span>
      <span className="flow-agent"><b>{task.cpu} CPU cores · {task.ram} GiB RAM</b></span>
      <span className="flow-task-meta"><span>{task.remaining}s work</span><span className={remainingWindow < task.remaining ? 'text-red' : ''}>{remainingWindow < 0 ? `${clock(-remainingWindow)} overdue` : `Due in ${clock(remainingWindow)}`}</span></span>
    </button>;
  }

  return <div className="recovery-flow">
    <div className="flow-stages">
      <section className="flow-stage source-stage" aria-label="Incident sources"><h3><span>01</span> Incident <ArrowRight size={16} /></h3>
        <div className={`fab-visual ${incidents.length ? 'fab-alert' : ''}`}><div className="fab-roof">Fab zones</div><div className="fab-zones">{['Zone A', 'Zone B', 'Zone C'].map(zone => <div key={zone} className={incidents.some(incident => incident.zone === zone) ? 'affected-zone' : ''}><span /><span /><span /><strong>{zone}</strong></div>)}</div><p>{incidents.length ? `${incidents.length} active incident${incidents.length > 1 ? 's' : ''}` : 'All zones normal'}</p></div>
        {incidents.map(incident => <div className="flow-incident" key={incident.id}><TriangleAlert size={18} /><div><strong>{scenarios[incident.kind].name}</strong><span>{incident.zone} · 3 recovery agents</span></div></div>)}
        <div className="flow-legend"><span><i className="recovery-key" />Recovery work</span><span><i className="routine-key" />Routine work</span></div>
      </section>
      <section className="flow-stage queue-stage" aria-label="Ordered agent queue"><h3><span>02</span> Waiting <b>{queue.length}</b><ArrowRight size={16} /></h3><p className="stage-caption">First in line runs when CPU and RAM are available.</p><div className="flow-queue">{queue.map((task, index) => taskCard(task, index + 1))}{!queue.length && <div className="flow-empty">No agents waiting.</div>}</div></section>
      <section className="flow-stage resource-stage" aria-label="CPU and RAM pool"><h3><span>03</span> CPU / RAM pool</h3>
        <div className="resource-gate"><Cpu size={27} /><strong>Diagnostic workers</strong><span>Simulated CPU and RAM</span>
          <label className="resource-meter">CPU <b>{used.cpu} / {capacity.cpu} cores</b><progress aria-label="CPU cores reserved" max={capacity.cpu} value={used.cpu} /></label>
          <label className="resource-meter">RAM <b>{used.ram} / {capacity.ram} GiB</b><progress aria-label="RAM reserved" max={capacity.ram} value={used.ram} /></label>
          <span>{running.length} tool calls running</span>
        </div>
        {blocked && <p className="resource-blocked">Queue head needs {head.cpu} cores / {head.ram} GiB. Free: {capacity.cpu - used.cpu} cores / {capacity.ram - used.ram} GiB. Waiting for {head.cpu > capacity.cpu - used.cpu ? 'CPU' : ''}{head.cpu > capacity.cpu - used.cpu && head.ram > capacity.ram - used.ram ? ' + ' : ''}{head.ram > capacity.ram - used.ram ? 'RAM' : ''}.</p>}
        {running.length ? running.map(task => <div className="running-resource-task" key={task.id}>{taskCard(task)}<div className="execution-progress"><span>Execution progress<b>{Math.round((1 - task.remaining / task.duration) * 100)}%</b></span><progress aria-label={`Execution progress: ${task.title}`} max={task.duration} value={task.duration - task.remaining} /></div></div>) : <div className="flow-empty">Resources available.</div>}
        <div className="resource-rule">Both CPU and RAM must fit.<br />Completion releases reservations.<br />Running work is not interrupted.</div>
      </section>
    </div>
    <details className="flow-completions"><summary><CheckCheck size={18} />{completed.length} tasks completed <span>View outcomes</span></summary><div>{completed.length ? [...completed].reverse().map(task => <button key={task.id} onClick={() => onSelect(task.id)}><span>{task.title}</span><b className={(task.finishedAt ?? 0) > task.deadline ? 'text-red' : 'text-green'}>{(task.finishedAt ?? 0) > task.deadline ? 'Late' : 'On time'}</b></button>) : <p>Press Play to watch agents finish.</p>}</div></details>
  </div>;
}
