use std::path::Path;
use std::path::PathBuf;
use std::sync::Arc;

use pretty_assertions::assert_eq;

use super::Knob;
use super::Tuner;

fn tuner(knob: Arc<Knob>, fairness_grows_with_knob: bool) -> Tuner {
    Tuner::new(
        knob,
        fairness_grows_with_knob,
        vec![(PathBuf::from("/incident"), 0), (PathBuf::from("/oss"), 3)],
        2000.0,
        8000.0,
        4,
        (0.1, 100.0),
    )
}

#[test]
fn slow_critical_calls_make_linear_rate_less_fair() {
    let knob = Arc::new(Knob::new(1.0));
    let tuner = tuner(Arc::clone(&knob), true);
    assert!(tuner.observe(Path::new("/incident/a"), 5000.0).is_none());
    assert!(tuner.observe(Path::new("/incident/b"), 5000.0).is_none());
    assert!(tuner.observe(Path::new("/oss/a"), 100.0).is_none());
    let event = tuner
        .observe(Path::new("/oss/b"), 100.0)
        .expect("window closes");
    assert_eq!(event["event"], "retune");
    assert!(knob.get() < 1.0);
}

#[test]
fn starving_background_calls_raise_aging_fairness() {
    let knob = Arc::new(Knob::new(4000.0));
    let tuner = tuner(Arc::clone(&knob), false);
    for cwd in ["/incident/a", "/incident/b", "/oss/a"] {
        assert!(tuner.observe(Path::new(cwd), 100.0).is_none());
    }
    tuner
        .observe(Path::new("/oss/b"), 20000.0)
        .expect("window closes");
    assert!(knob.get() < 4000.0);
}

#[test]
fn within_targets_leaves_knob_alone_and_ignores_unknown_cwd() {
    let knob = Arc::new(Knob::new(1.0));
    let tuner = tuner(Arc::clone(&knob), true);
    assert!(tuner.observe(Path::new("/elsewhere"), 99999.0).is_none());
    for cwd in ["/incident/a", "/incident/b", "/oss/a", "/oss/b"] {
        assert!(tuner.observe(Path::new(cwd), 100.0).is_none());
    }
    assert_eq!(knob.get(), 1.0);
}
