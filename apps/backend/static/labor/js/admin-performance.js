export function initAdminPerformance() {
    const section = document.querySelector("[data-perf-period]");
    if (!section) return;

    const fetchData = (period) => {
        fetch(`/api/admin/performance/?period=${period}`)
            .then((res) => res.json())
            .then((data) => {
                // LangGraph 노드 카드 업데이트
                const statGrid = document.querySelector(".stat-grid");
                if (statGrid && data.langgraph_nodes) {
                    const cards = statGrid.querySelectorAll(".stat-card.blue");
                    data.langgraph_nodes.forEach((node, i) => {
                        if (cards[i]) {
                            cards[i].querySelector(".card-meta").textContent = `${node.calls}회 호출`;
                            const splitRows = cards[i].querySelectorAll(".split-row");
                            if (splitRows[0]) splitRows[0].querySelector("b").textContent = `${node.avg_ms}ms`;
                            if (splitRows[1]) splitRows[1].querySelector("b").textContent = `${node.max_ms}ms`;
                        }
                    });
                }

                // 통계 업데이트
                if (data.total_calls !== undefined) {
                    const statCards = document.querySelectorAll(".stat-card");
                    if (statCards.length >= 3) {
                        statCards[0].querySelector("strong").textContent = data.total_calls.toLocaleString ? data.total_calls.toLocaleString() : data.total_calls;
                        statCards[1].querySelector("strong").textContent = data.total_tokens || "0";
                        statCards[2].querySelector("strong").textContent = `$${data.total_cost || "0"}`;
                    }
                }

                // 차트 업데이트
                const chart = document.querySelector("#perfCallsChart");
                if (chart && data.llm_usage) {
                    chart.innerHTML = data.llm_usage.map((item) =>
                        `<div>
                            <span class="bar q" style="height: ${item.calls_height}%"></span>
                            <span class="bar u" style="height: ${item.emb_calls_height}%"></span>
                            <small>${item.date}</small>
                        </div>`
                    ).join("");
                }
            })
            .catch((err) => console.error("성능 데이터 조회 실패:", err));
    };

    section.addEventListener("click", (event) => {
        const btn = event.target.closest("[data-period]");
        if (!btn) return;
        section.querySelectorAll("button").forEach((n) => n.classList.remove("active"));
        btn.classList.add("active");
        fetchData(btn.dataset.period);
    });

    // 초기 로드 시 day 데이터 fetch
    fetchData("day");
}