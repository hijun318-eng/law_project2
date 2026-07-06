import { initSidebar } from "./sidebar.js";
import { initAdminDashboard } from "./admin-dashboard.js?v=2";
import { initAdminUsers } from "./admin-users.js";
import { initAdminFeedback } from "./admin-feedback.js";
import { initAdminPrompts } from "./admin-prompts.js";
// import { initAdminVectorDB } from "./admin-vectordb.js";
import { initAdminPerformance } from "./admin-performance.js";

initSidebar();
initAdminDashboard();
initAdminUsers();
initAdminFeedback();
initAdminPrompts();
// initAdminVectorDB();
initAdminPerformance();