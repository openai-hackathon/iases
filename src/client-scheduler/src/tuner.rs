use std::path::Path;
use std::path::PathBuf;
use std::sync::Arc;
use std::sync::Mutex;
use std::sync::atomic::AtomicU32;
use std::sync::atomic::Ordering;

use serde_json::Value;
use serde_json::json;

use crate::scorer::tier_of;

pub struct Knob(AtomicU32);

impl Knob {
    pub fn new(value: f32) -> Self {
        Self(AtomicU32::new(value.to_bits()))
    }

    pub fn get(&self) -> f32 {
        f32::from_bits(self.0.load(Ordering::Relaxed))
    }

    pub fn set(&self, value: f32) {
        self.0.store(value.to_bits(), Ordering::Relaxed);
    }
}

pub struct Tuner {
    knob: Arc<Knob>,
    fairness_grows_with_knob: bool,
    tiers: Vec<(PathBuf, u8)>,
    target_critical_ms: f64,
    target_background_ms: f64,
    window: usize,
    range: (f32, f32),
    samples: Mutex<Vec<(u8, f64)>>,
}

const STEP: f32 = 1.3;
const CRITICAL_TIER_MAX: u8 = 1;

impl Tuner {
    pub fn new(
        knob: Arc<Knob>,
        fairness_grows_with_knob: bool,
        tiers: Vec<(PathBuf, u8)>,
        target_critical_ms: f64,
        target_background_ms: f64,
        window: usize,
        range: (f32, f32),
    ) -> Self {
        Self {
            knob,
            fairness_grows_with_knob,
            tiers,
            target_critical_ms,
            target_background_ms,
            window: window.max(2),
            range,
            samples: Mutex::new(Vec::new()),
        }
    }

    pub fn observe(&self, cwd: &Path, wait_ms: f64) -> Option<Value> {
        let tier = tier_of(&self.tiers, cwd)?;
        let mut samples = self
            .samples
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        samples.push((tier, wait_ms));
        if samples.len() < self.window {
            return None;
        }
        let critical: Vec<f64> = samples
            .iter()
            .filter(|(tier, _)| *tier <= CRITICAL_TIER_MAX)
            .map(|(_, wait)| *wait)
            .collect();
        let background: Vec<f64> = samples
            .iter()
            .filter(|(tier, _)| *tier > CRITICAL_TIER_MAX)
            .map(|(_, wait)| *wait)
            .collect();
        samples.clear();
        if critical.is_empty() || background.is_empty() {
            return None;
        }
        let critical_mean = critical.iter().sum::<f64>() / critical.len() as f64;
        let background_max = background.iter().cloned().fold(0.0, f64::max);
        let old = self.knob.get();
        let more_fair = if critical_mean > self.target_critical_ms {
            false
        } else if background_max > self.target_background_ms {
            true
        } else {
            return None;
        };
        let grow = more_fair == self.fairness_grows_with_knob;
        let new = if grow { old * STEP } else { old / STEP };
        let new = new.clamp(self.range.0, self.range.1);
        if new == old {
            return None;
        }
        self.knob.set(new);
        Some(json!({
            "event": "retune",
            "critical_mean_wait_ms": critical_mean,
            "background_max_wait_ms": background_max,
            "old_knob": old,
            "new_knob": new,
        }))
    }
}

#[cfg(test)]
#[path = "tuner_tests.rs"]
mod tests;
