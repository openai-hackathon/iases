use std::collections::HashMap;
use std::sync::Mutex;
use std::time::Duration;
use std::time::Instant;

use crate::CallKey;
use crate::scorer::Scorer;
use crate::scorer::TaskFeatures;

pub struct PreemptPolicy {
    preemptible: Vec<String>,
    min_run: Duration,
    cooldown: Duration,
    last_by_thread: Mutex<HashMap<String, Instant>>,
}

pub(crate) struct Candidate<'a> {
    pub key: &'a CallKey,
    pub features: &'a TaskFeatures,
    pub granted_at: Instant,
    pub cancellable: bool,
}

impl PreemptPolicy {
    pub fn new(preemptible: Vec<String>, min_run: Duration, cooldown: Duration) -> Self {
        Self {
            preemptible,
            min_run,
            cooldown,
            last_by_thread: Mutex::new(HashMap::new()),
        }
    }

    pub(crate) fn pick_victim<'a>(
        &self,
        scorer: &dyn Scorer,
        incoming: &TaskFeatures,
        candidates: impl Iterator<Item = Candidate<'a>>,
    ) -> Option<CallKey> {
        let now = Instant::now();
        let last = self
            .last_by_thread
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        let victim = candidates
            .filter(|candidate| candidate.cancellable)
            .filter(|candidate| self.preemptible.contains(&candidate.features.tool_name))
            .filter(|candidate| now.duration_since(candidate.granted_at) >= self.min_run)
            .filter(|candidate| {
                last.get(&candidate.key.thread_id)
                    .is_none_or(|at| now.duration_since(*at) >= self.cooldown)
            })
            .filter(|candidate| {
                let preference = scorer.score(incoming, candidate.features);
                preference.confidence >= 1.0 && preference.first_wins()
            })
            .max_by_key(|candidate| candidate.granted_at)?;
        Some(victim.key.clone())
    }

    pub fn mark(&self, thread_id: &str) {
        self.last_by_thread
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
            .insert(thread_id.to_string(), Instant::now());
    }
}

#[cfg(test)]
#[path = "preempt_tests.rs"]
mod tests;
