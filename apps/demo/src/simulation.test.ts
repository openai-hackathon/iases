import assert from 'node:assert/strict';
import test from 'node:test';
import { capacity, dispatch, initialState, injectIncident, orderedQueue, resourceUsage, setPolicy, setPriority, tick, metrics } from './simulation.ts';

test('incident injection adds three agents without preempting a running task', () => {
  const state = injectIncident(initialState(), 'power', 'Zone B', 90);
  assert.equal(state.incidents.length, 1);
  assert.deepEqual(state.tasks.filter(task => task.status === 'running').map(task => task.id), ['BG-01']);
  assert.deepEqual(state.tasks.slice(3).map(task => [task.priority, task.deadline, task.incidentId]), [[98, 45, 'INC-001'], [93, 72, 'INC-001'], [88, 90, 'INC-001']]);
});

test('FIFO preserves arrival while deadline-aware scheduling dispatches incident work first', () => {
  const state = injectIncident(initialState(), 'power', 'Zone B', 90);
  assert.equal(orderedQueue(state)[0].id, 'INC-001-1');
  assert.equal(orderedQueue(setPolicy(state, 'fifo'))[0].id, 'BG-02');
});

test('manual priority changes queue order without mutating the previous state', () => {
  const state = setPolicy(injectIncident(initialState(), 'power', 'Zone B', 90), 'priority');
  const updated = setPriority(state, 'BG-03', 100);
  assert.equal(orderedQueue(updated)[0].id, 'BG-03');
  assert.equal(state.tasks[2].priority, 20);
  assert.equal(orderedQueue(setPolicy(updated, 'aware'))[0].id, 'INC-001-1');
});

test('completion releases resources and starts concurrent tasks that fit', () => {
  let state = injectIncident(initialState(), 'power', 'Zone B', 90);
  for (let step = 0; step < 18; step++) state = tick(state);
  assert.deepEqual(state.tasks.filter(task => task.status === 'running').map(task => [task.id, task.startedAt]), [['INC-001-1', 18], ['INC-001-2', 18]]);
  assert.deepEqual(resourceUsage(state), { cpu: 8, ram: 14 });
  assert.equal(state.tasks[0].finishedAt, 18);
  state = tick(state);
  assert.deepEqual(state.tasks.filter(task => task.status === 'running').map(task => task.remaining), [11, 17]);
});

test('deadline misses persist after task completion', () => {
  let state = initialState();
  state.tasks = [{ ...state.tasks[0], deadline: 1, duration: 2, remaining: 2 }];
  state = tick(state);
  assert.equal(metrics(state).missed, 0);
  state = tick(state);
  assert.equal(metrics(state).missed, 1);
  assert.equal(metrics(tick(state)).missed, 1);
});

test('same input scenario can compare policies with a fixed clock', () => {
  const replay = (policy: 'aware' | 'fifo') => {
    let state = setPolicy(injectIncident(initialState(), 'power', 'Zone B', 90), policy);
    for (let step = 0; step < 150; step++) state = tick(state);
    return metrics(state);
  };
  assert.equal(replay('aware').missed, 0);
  assert.ok(replay('fifo').missed > replay('aware').missed);
});

test('either CPU or RAM exhaustion blocks dispatch without skipping the head', () => {
  for (const demand of [{ cpu: 8, ram: 1 }, { cpu: 1, ram: 16 }]) {
    const state = initialState();
    state.tasks[0] = { ...state.tasks[0], ...demand };
    state.tasks[1] = { ...state.tasks[1], cpu: 2, ram: 2 };
    state.tasks[2] = { ...state.tasks[2], cpu: 1, ram: 1 };
    assert.deepEqual(dispatch(state), state);
  }
  const state = initialState();
  state.tasks[0] = { ...state.tasks[0], cpu: 4, ram: 8 };
  state.tasks[2] = { ...state.tasks[2], cpu: 1, ram: 1 };
  assert.deepEqual(dispatch(state), state);
});

test('replay stays within both budgets and releases all resources', () => {
  let state = injectIncident(initialState(), 'power', 'Zone B', 90);
  for (let step = 0; step < 150; step++) {
    state = tick(state);
    const used = resourceUsage(state);
    assert.ok(used.cpu <= capacity.cpu && used.ram <= capacity.ram);
  }
  assert.deepEqual(resourceUsage(state), { cpu: 0, ram: 0 });
  assert.ok(state.tasks.every(task => task.status === 'complete'));
});

test('incident and event history remain bounded', () => {
  let state = initialState();
  for (let index = 0; index < 8; index++) state = injectIncident(state, 'cooling', 'Zone A', 60);
  assert.equal(state.incidents.length, 3);
  for (let index = 0; index < 100; index++) state = setPolicy(state, 'fifo');
  assert.equal(state.events.length, 40);
});

test('invalid simulation inputs are rejected', () => {
  assert.throws(() => injectIncident(initialState(), 'power', 'Zone B', NaN));
  assert.throws(() => injectIncident(initialState(), 'power', 'Zone B', 10));
  assert.throws(() => setPriority(initialState(), 'BG-02', Infinity));
});
