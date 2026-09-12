use std::collections::HashMap;
use std::time::Duration;
use std::time::Instant;

use serde_json::Value;
use serde_json::json;

pub(crate) const CHEAP_TOOLS: [&str; 4] = ["read_file", "list_dir", "grep_files", "tool_search"];
const IO_THRESHOLD_MS: f64 = 250.0;
const MIN_SAMPLES: u32 = 3;
const WINDOW: Duration = Duration::from_secs(15);
const GROW_WAIT_MS: f64 = 1000.0;
const SHRINK_WAIT_MS: f64 = 100.0;

#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum ResourceClass {
    Io,
    Cpu,
    Network,
}

impl ResourceClass {
    pub fn name(self) -> &'static str {
        match self {
            Self::Io => "io",
            Self::Cpu => "cpu",
            Self::Network => "network",
        }
    }
}

#[derive(Default)]
struct ToolStats {
    ema_ms: f64,
    samples: u32,
}

#[derive(Default)]
struct WaitStats {
    sum_ms: f64,
    count: u32,
}

pub struct ResourcePools {
    base: usize,
    limits: HashMap<ResourceClass, usize>,
    running: HashMap<ResourceClass, usize>,
    tools: HashMap<String, ToolStats>,
    waits: HashMap<ResourceClass, WaitStats>,
    window_started: Instant,
}

impl ResourcePools {
    pub fn new(base: usize) -> Self {
        let base = base.max(1);
        Self {
            base,
            limits: HashMap::from([
                (ResourceClass::Cpu, base),
                (ResourceClass::Io, base * 4),
                (ResourceClass::Network, base),
            ]),
            running: HashMap::new(),
            tools: HashMap::new(),
            waits: HashMap::new(),
            window_started: Instant::now(),
        }
    }

    pub fn classify(&self, tool: &str) -> ResourceClass {
        if tool.contains("__") || tool.starts_with("web_search") || tool.starts_with("mcp") {
            return ResourceClass::Network;
        }
        if CHEAP_TOOLS.contains(&tool) {
            return ResourceClass::Io;
        }
        match self.tools.get(tool) {
            Some(stats) if stats.samples >= MIN_SAMPLES && stats.ema_ms < IO_THRESHOLD_MS => {
                ResourceClass::Io
            }
            _ => ResourceClass::Cpu,
        }
    }

    pub fn limit(&self, class: ResourceClass) -> usize {
        self.limits.get(&class).copied().unwrap_or(self.base)
    }

    pub fn running(&self, class: ResourceClass) -> usize {
        self.running.get(&class).copied().unwrap_or(0)
    }

    pub fn has_capacity(&self, class: ResourceClass) -> bool {
        self.running(class) < self.limit(class)
    }

    pub fn start(&mut self, class: ResourceClass) {
        *self.running.entry(class).or_insert(0) += 1;
    }

    pub fn finish(&mut self, class: ResourceClass) {
        if let Some(count) = self.running.get_mut(&class) {
            *count = count.saturating_sub(1);
        }
    }

    pub fn observe(&mut self, tool: &str, class: ResourceClass, run_ms: f64, wait_ms: f64) {
        let stats = self.tools.entry(tool.to_string()).or_default();
        stats.ema_ms = if stats.samples == 0 {
            run_ms
        } else {
            stats.ema_ms * 0.7 + run_ms * 0.3
        };
        stats.samples += 1;
        let waits = self.waits.entry(class).or_default();
        waits.sum_ms += wait_ms;
        waits.count += 1;
    }

    pub fn adapt(&mut self) -> Vec<Value> {
        if self.window_started.elapsed() < WINDOW {
            return Vec::new();
        }
        self.window_started = Instant::now();
        let mut events = Vec::new();
        for class in [
            ResourceClass::Cpu,
            ResourceClass::Io,
            ResourceClass::Network,
        ] {
            let Some(waits) = self.waits.remove(&class) else {
                continue;
            };
            if waits.count == 0 {
                continue;
            }
            let avg_wait = waits.sum_ms / f64::from(waits.count);
            let old = self.limit(class);
            let new = if avg_wait > GROW_WAIT_MS {
                (old + 1).min(self.base * 8)
            } else if avg_wait < SHRINK_WAIT_MS && self.running(class) < old {
                (old - 1).max(1)
            } else {
                old
            };
            if new != old {
                self.limits.insert(class, new);
                events.push(json!({
                    "event": "retune_pool",
                    "class": class.name(),
                    "avg_wait_ms": avg_wait,
                    "old_limit": old,
                    "new_limit": new,
                }));
            }
        }
        events
    }
}

#[cfg(test)]
#[path = "pools_tests.rs"]
mod tests;
