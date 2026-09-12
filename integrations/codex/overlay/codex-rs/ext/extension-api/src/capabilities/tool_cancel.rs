use std::collections::HashMap;
use std::sync::Mutex;

use tokio_util::sync::CancellationToken;

#[derive(Default)]
pub struct ToolCancelRegistry {
    tokens: Mutex<HashMap<String, CancellationToken>>,
}

impl ToolCancelRegistry {
    pub fn register(&self, call_id: &str, token: CancellationToken) {
        self.lock().insert(call_id.to_string(), token);
    }

    pub fn unregister(&self, call_id: &str) {
        self.lock().remove(call_id);
    }

    pub fn token(&self, call_id: &str) -> Option<CancellationToken> {
        self.lock().get(call_id).cloned()
    }

    fn lock(&self) -> std::sync::MutexGuard<'_, HashMap<String, CancellationToken>> {
        self.tokens
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
    }
}
