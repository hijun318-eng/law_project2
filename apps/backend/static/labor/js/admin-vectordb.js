import { postJson } from "./utils.js";

export function initAdminVectorDB() {
    const grid = document.querySelector("#vectorDbGrid");
    if (!grid) return;

    grid.querySelectorAll("[data-rebuild-db]").forEach((btn) => btn.addEventListener("click", () => {
        const card = btn.closest("[data-db-id]");
        const progressRow = card.querySelector("[data-progress-row]");
        const fill = card.querySelector("[data-progress-fill]");
        const label = card.querySelector("[data-progress-label]");
        const statusLabel = card.querySelector("[data-db-status-label]");

        btn.disabled = true;
        progressRow.hidden = false;
        statusLabel.textContent = "재구축 중";
        statusLabel.className = "status suspended";

        let pct = 0;
        const timer = setInterval(() => {
            pct = Math.min(pct + 4, 100);
            fill.style.width = `${pct}%`;
            label.textContent = `${pct}%`;
            if (pct >= 100) {
                clearInterval(timer);
                postJson("/api/admin/vectordb/rebuild/", { id: card.dataset.dbId })
                    .catch(() => {})
                    .finally(() => {
                        statusLabel.textContent = "정상";
                        statusLabel.className = "status active";
                        btn.disabled = false;
                        progressRow.hidden = true;
                    });
            }
        }, 120);
    }));

    document.querySelector("[data-vectordb-tabs]")?.addEventListener("click", (event) => {
        const btn = event.target.closest("[data-vectordb-tab]");
        if (!btn) return;
        document.querySelectorAll("[data-vectordb-tab]").forEach((n) => n.classList.remove("active"));
        btn.classList.add("active");
        document.querySelectorAll("[data-vectordb-panel]").forEach((panel) =>
            panel.hidden = panel.dataset.vectordbPanel !== btn.dataset.vectordbTab);
    });

    document.querySelectorAll("[data-reprocess]").forEach((btn) => btn.addEventListener("click", () => {
        const card = btn.closest("[data-failed-id]");
        btn.disabled = true;
        btn.textContent = "처리 중...";
        postJson("/api/admin/vectordb/reprocess/", { id: parseInt(card.dataset.failedId) })
            .catch(() => {})
            .finally(() => card.remove());
    }));
}