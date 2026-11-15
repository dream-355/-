// Dependency registry breaks import cycles between feature modules.
// app.js installs the wiring once at bootstrap time.
export const deps = {
  renderView: null,
  renderChat: null,
  renderHealth: null,
  renderDashboard: null,
  openConversation: null,
  startNewChat: null,
  openRecordModal: null,
  openProfileModal: null,
  openGraphInspector: null,
};

export function installDeps(values) {
  Object.assign(deps, values);
}
