export function initAdminPerformance() {
    const section = document.querySelector("[data-perf-period]");
    if (!section) return;

    section.addEventListener("click", (event) => {
        const btn = event.target.closest("[data-period]");
        if (!btn) return;
        section.querySelectorAll("button").forEach((n) => n.classList.remove("active"));
        btn.classList.add("active");
        // 기간별 데이터가 필요하면 여기서 fetch 후 #perfCallsChart 다시 그리기
    });
}