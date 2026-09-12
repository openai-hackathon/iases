use std::path::PathBuf;
use std::time::Duration;
use std::time::Instant;

use pretty_assertions::assert_eq;

use super::Candidate;
use super::PreemptPolicy;
use crate::CallKey;
use crate::scorer::RuleScorer;
use crate::scorer::TaskFeatures;

fn task(cwd: &str, tool: &str) -> TaskFeatures {
    TaskFeatures {
        cwd: PathBuf::from(cwd),
        tool_name: tool.to_string(),
        waiting_since: Instant::now(),
    }
}

fn key(thread: &str) -> CallKey {
    CallKey {
        thread_id: thread.to_string(),
        turn_id: "turn".to_string(),
        call_id: "call".to_string(),
    }
}

fn scorer() -> RuleScorer {
    RuleScorer::new(
        vec![(PathBuf::from("/incident"), 0), (PathBuf::from("/oss"), 3)],
        Vec::new(),
    )
}

fn policy() -> PreemptPolicy {
    PreemptPolicy::new(
        vec!["exec_command".to_string()],
        Duration::ZERO,
        Duration::from_secs(30),
    )
}

#[test]
fn preempts_lower_tier_preemptible_running_call() {
    let policy = policy();
    let oss = key("oss");
    let running = task("/oss/a", "exec_command");
    let victim = policy.pick_victim(
        &scorer(),
        &task("/incident/x", "exec_command"),
        [Candidate {
            key: &oss,
            features: &running,
            granted_at: Instant::now(),
            cancellable: true,
        }]
        .into_iter(),
    );
    assert_eq!(victim, Some(oss));
}

#[test]
fn never_preempts_equal_tier_non_preemptible_or_uncancellable_calls() {
    let policy = policy();
    let incident = task("/incident/x", "exec_command");
    let oss_patch = task("/oss/a", "apply_patch");
    let oss_exec = task("/oss/b", "exec_command");
    let other_incident = task("/incident/y", "exec_command");
    let k1 = key("patch");
    let k2 = key("uncancellable");
    let k3 = key("peer");
    let victim = policy.pick_victim(
        &scorer(),
        &incident,
        [
            Candidate {
                key: &k1,
                features: &oss_patch,
                granted_at: Instant::now(),
                cancellable: true,
            },
            Candidate {
                key: &k2,
                features: &oss_exec,
                granted_at: Instant::now(),
                cancellable: false,
            },
            Candidate {
                key: &k3,
                features: &other_incident,
                granted_at: Instant::now(),
                cancellable: true,
            },
        ]
        .into_iter(),
    );
    assert_eq!(victim, None);
}

#[test]
fn cooldown_blocks_repeated_preemption_of_one_thread() {
    let policy = policy();
    let oss = key("oss");
    let running = task("/oss/a", "exec_command");
    policy.mark("oss");
    let victim = policy.pick_victim(
        &scorer(),
        &task("/incident/x", "exec_command"),
        [Candidate {
            key: &oss,
            features: &running,
            granted_at: Instant::now(),
            cancellable: true,
        }]
        .into_iter(),
    );
    assert_eq!(victim, None);
}
