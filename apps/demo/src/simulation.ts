export type Policy = 'aware' | 'priority' | 'fifo';
export type Task = {
  id: string; title: string; agent: string; session: string; zone: string;
  priority: number; queuedAt: number; duration: number; remaining: number;
  deadline: number; cpu: number; ram: number; status: 'queued' | 'running' | 'complete';
  startedAt?: number; finishedAt?: number; incidentId?: string;
};
export type IncidentKind = 'power' | 'cooling' | 'network';
export type Incident = { id: string; kind: IncidentKind; zone: string; createdAt: number; deadline: number };
export type Event = { id: number; at: number; text: string; tone: 'info' | 'warning' | 'success' };
export type Simulation = { now: number; policy: Policy; tasks: Task[]; incidents: Incident[]; events: Event[]; sequence: number };

export const scenarios: Record<IncidentKind, { name: string; detail: string; tasks: [string, string, string]; severity: string }> = {
  power: { name: 'Power interruption', detail: 'Simulated voltage loss in a fabrication zone.', tasks: ['Validate power telemetry', 'Assess affected wafer lots', 'Draft power recovery brief'], severity: 'Critical' },
  cooling: { name: 'Cooling excursion', detail: 'Simulated cooling telemetry outside the expected range.', tasks: ['Review cooling telemetry', 'Assess thermal exposure', 'Draft cooling recovery brief'], severity: 'High' },
  network: { name: 'Telemetry outage', detail: 'Simulated loss of equipment monitoring signals.', tasks: ['Check telemetry availability', 'Identify monitoring gaps', 'Draft monitoring recovery brief'], severity: 'High' },
};

const agentNames = ['Telemetry analyst', 'Lot impact analyst', 'Recovery planner'];
export const capacity = { cpu: 8, ram: 16 };

export function resourceUsage(state: Simulation) {
  return state.tasks.filter(task => task.status === 'running').reduce((used, task) => ({ cpu: used.cpu + task.cpu, ram: used.ram + task.ram }), { cpu: 0, ram: 0 });
}

function record(state: Simulation, text: string, tone: Event['tone'] = 'info'): Simulation {
  const sequence = state.sequence + 1;
  return { ...state, sequence, events: [{ id: sequence, at: state.now, text, tone }, ...state.events].slice(0, 40) };
}

export function initialState(): Simulation {
  const tasks: Task[] = [
    { id: 'BG-01', title: 'Compile shift handover', agent: 'Operations analyst', session: 'session-01', zone: 'All zones', priority: 25, queuedAt: 0, duration: 18, remaining: 18, deadline: 180, cpu: 8, ram: 12, status: 'running', startedAt: 0 },
    { id: 'BG-02', title: 'Summarize yield trends', agent: 'Yield analyst', session: 'session-02', zone: 'Zone A', priority: 35, queuedAt: 0, duration: 28, remaining: 28, deadline: 150, cpu: 6, ram: 12, status: 'queued' },
    { id: 'BG-03', title: 'Review asset inventory', agent: 'Asset analyst', session: 'session-03', zone: 'Zone C', priority: 20, queuedAt: 0, duration: 24, remaining: 24, deadline: 180, cpu: 4, ram: 8, status: 'queued' },
  ];
  return record({ now: 0, policy: 'aware', tasks, incidents: [], events: [], sequence: 0 }, 'Simulation ready. Simulated pool: 8 CPU cores, 16 GiB RAM. No live resource measurements.');
}

export function slack(task: Task, now: number): number {
  return task.deadline - now - task.remaining;
}

export function orderedQueue(state: Simulation): Task[] {
  return state.tasks.filter(task => task.status === 'queued').sort((first, second) => {
    if (state.policy === 'aware') {
      const slackDifference = slack(first, state.now) - slack(second, state.now);
      if (slackDifference !== 0) return slackDifference;
    }
    if (state.policy !== 'fifo' && first.priority !== second.priority) return second.priority - first.priority;
    return first.queuedAt - second.queuedAt || first.id.localeCompare(second.id);
  });
}

export function dispatch(state: Simulation): Simulation {
  let next = state;
  const used = resourceUsage(state);
  for (const task of orderedQueue(state)) {
    if (used.cpu + task.cpu > capacity.cpu || used.ram + task.ram > capacity.ram) break;
    used.cpu += task.cpu;
    used.ram += task.ram;
    const tasks = next.tasks.map(current => current.id === task.id ? { ...current, status: 'running' as const, startedAt: state.now } : current);
    next = record({ ...next, tasks }, `${task.id} started with ${task.cpu} CPU cores and ${task.ram} GiB RAM reserved.`);
  }
  return next;
}

export function tick(state: Simulation): Simulation {
  let next = { ...state, now: state.now + 1, tasks: state.tasks.map(task => task.status === 'running' ? { ...task, remaining: Math.max(0, task.remaining - 1) } : task) };
  for (const task of next.tasks) {
    if (task.status === 'running' && task.remaining === 0) {
      next = { ...next, tasks: next.tasks.map(current => current.id === task.id ? { ...current, status: 'complete' as const, finishedAt: next.now } : current) };
      next = record(next, `${task.id} completed${next.now > task.deadline ? ' after its deadline' : ' on time'}. CPU and RAM released.`, next.now > task.deadline ? 'warning' : 'success');
    } else if (task.status !== 'complete' && state.now <= task.deadline && next.now > task.deadline) {
      next = record(next, `${task.id} missed its deadline. Work remains in the queue or running.`, 'warning');
    }
  }
  return dispatch(next);
}

export function isActive(incident: Incident, tasks: Task[]): boolean {
  return tasks.some(task => task.incidentId === incident.id && task.status !== 'complete');
}

export function injectIncident(state: Simulation, kind: IncidentKind, zone: string, window: number): Simulation {
  if (!Number.isFinite(window) || window < 30 || window > 180) throw new Error('Response window must be 30 to 180 simulated seconds.');
  if (state.incidents.filter(incident => isActive(incident, state.tasks)).length >= 3 || state.incidents.length >= 12) return state;
  const id = `INC-${String(state.incidents.length + 1).padStart(3, '0')}`;
  const incident = { id, kind, zone, createdAt: state.now, deadline: state.now + window };
  const tasks = scenarios[kind].tasks.map((title, index): Task => ({
    id: `${id}-${index + 1}`, title, agent: agentNames[index], session: `${id}/agent-${index + 1}`, zone,
    priority: (kind === 'power' ? 98 : 90) - index * 5, queuedAt: state.now,
    duration: [12, 18, 14][index], remaining: [12, 18, 14][index], cpu: [4, 4, 2][index], ram: [6, 8, 4][index],
    deadline: state.now + Math.round(window * [0.5, 0.8, 1][index]), status: 'queued', incidentId: id,
  }));
  return dispatch(record({ ...state, tasks: [...state.tasks, ...tasks], incidents: [...state.incidents, incident] }, `${id}: ${scenarios[kind].name} in ${zone}. Three mock agents queued.`, 'warning'));
}

export function setPolicy(state: Simulation, policy: Policy): Simulation {
  return record({ ...state, policy }, `Policy changed to ${policy === 'aware' ? 'deadline + priority' : policy}. Running work is not preempted.`);
}

export function setPriority(state: Simulation, id: string, priority: number): Simulation {
  if (!Number.isFinite(priority) || priority < 0 || priority > 100) throw new Error('Priority must be between 0 and 100.');
  const task = state.tasks.find(current => current.id === id);
  if (!task || task.status !== 'queued') return state;
  return record({ ...state, tasks: state.tasks.map(current => current.id === id ? { ...current, priority } : current) }, `Operator changed ${id} importance to ${priority}. Manual mock score, not a BT fit.`);
}

export function metrics(state: Simulation) {
  const completed = state.tasks.filter(task => task.status === 'complete');
  const waiting = state.tasks.filter(task => task.status === 'queued');
  const missed = state.tasks.filter(task => (task.finishedAt ?? state.now) > task.deadline).length;
  const atRisk = state.tasks.filter(task => task.status !== 'complete' && slack(task, state.now) < 15).length;
  const backgroundWait = state.tasks.filter(task => !task.incidentId).map(task => (task.startedAt ?? state.now) - task.queuedAt);
  return { completed: completed.length, waiting: waiting.length, missed, atRisk, maxBackgroundWait: Math.max(0, ...backgroundWait) };
}

export function clock(seconds: number): string {
  const absolute = Math.abs(Math.floor(seconds));
  return `${seconds < 0 ? '−' : ''}${String(Math.floor(absolute / 60)).padStart(2, '0')}:${String(absolute % 60).padStart(2, '0')}`;
}
