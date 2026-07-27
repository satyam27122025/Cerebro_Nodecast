const LISTENER_SESSION_KEY = "listener_id";

export function getListenerSessionId() {
  const existing = window.sessionStorage.getItem(LISTENER_SESSION_KEY);
  if (existing) {
    return existing;
  }

  const generated = crypto.randomUUID();
  window.sessionStorage.setItem(LISTENER_SESSION_KEY, generated);
  return generated;
}

export function setListenerSessionId(id) {
  if (id) {
    window.sessionStorage.setItem(LISTENER_SESSION_KEY, id);
  }
}
