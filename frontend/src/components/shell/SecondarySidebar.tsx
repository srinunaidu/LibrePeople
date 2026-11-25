/**
 * SecondarySidebar — thin re-export wrapper.
 *
 * The shell was unified into a single 220px sidebar (WorkspaceRail). This
 * file remains as a re-export so existing imports (e.g. e2e helpers) do not
 * break. It does not render a second sidebar.
 */
export { WorkspaceRail as SecondarySidebar } from "./WorkspaceRail"
export { WorkspaceRail as default } from "./WorkspaceRail"
