use pretty_assertions::assert_eq;

use super::ResourceClass;
use super::ResourcePools;

#[test]
fn classifies_by_name_then_learned_latency() {
    let mut pools = ResourcePools::new(1);
    assert_eq!(pools.classify("read_file"), ResourceClass::Io);
    assert_eq!(
        pools.classify("mcp__github__search"),
        ResourceClass::Network
    );
    assert_eq!(pools.classify("exec_command"), ResourceClass::Cpu);
    for _ in 0..3 {
        pools.observe("git_status", ResourceClass::Cpu, 40.0, 0.0);
    }
    assert_eq!(pools.classify("git_status"), ResourceClass::Io);
}

#[test]
fn pools_have_independent_capacity() {
    let mut pools = ResourcePools::new(1);
    pools.start(ResourceClass::Cpu);
    assert!(!pools.has_capacity(ResourceClass::Cpu));
    assert!(pools.has_capacity(ResourceClass::Io));
    assert_eq!(pools.limit(ResourceClass::Io), 4);
    pools.finish(ResourceClass::Cpu);
    assert!(pools.has_capacity(ResourceClass::Cpu));
    assert_eq!(pools.limit(ResourceClass::Network), 1);
}

#[test]
fn adapt_grows_a_pool_under_sustained_waiting() {
    let mut pools = ResourcePools::new(1);
    pools.window_started = std::time::Instant::now() - super::WINDOW;
    pools.observe("exec_command", ResourceClass::Cpu, 500.0, 3000.0);
    let events = pools.adapt();
    assert_eq!(events.len(), 1);
    assert_eq!(events[0]["event"], "retune_pool");
    assert_eq!(events[0]["new_limit"], 2);
    assert_eq!(pools.limit(ResourceClass::Cpu), 2);
    assert!(pools.adapt().is_empty());
}
