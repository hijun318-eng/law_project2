const PERIOD_LABELS = {
    day: "최근 30일",
    week: "최근 12주",
    month: "최근 12개월",
};

export function initAdminPerformance() {
    const section = document.querySelector("[data-perf-period]");
    if (!section) return;

    const toggle = section.querySelector("[data-perf-toggle]");
    const statusBox = section.querySelector("#perfStatus");
    const statusText = statusBox?.querySelector(".perf-status-text");
    const retryBtn = statusBox?.querySelector(".perf-retry-btn");
    const rangeLabel = section.querySelector("#perfRangeLabel");

    let currentPeriod = "day";
    let requestToken = 0;

    const showStatus = (message, { withRetry = false } = {}) => {
        if (!statusBox) return;
        statusBox.hidden = false;
        statusText.textContent = message;
        retryBtn.hidden = !withRetry;
    };

    const hideStatus = () => {
        if (!statusBox) return;
        statusBox.hidden = true;
    };

    const renderEmpty = (container, message) => {
        container.innerHTML = `<p class="perf-empty">${message}</p>`;
    };

    const renderNodeCards = (nodes) => {
        const grid = section.querySelector("#perfNodeGrid");
        if (!grid) return;
        if (!nodes || nodes.length === 0) {
            renderEmpty(grid, "표시할 노드 데이터가 없습니다.");
            return;
        }
        grid.innerHTML = nodes.map((node) => `
            <article class="stat-card blue">
                <p class="node-label">${node.label}</p>
                <p class="card-meta">${node.calls}회 호출</p>
                <div class="split-row"><span>평균</span><b>${node.avg_ms}ms</b></div>
                <div class="split-row"><span>최대</span><b class="bad">${node.max_ms}ms</b></div>
            </article>
        `).join("");
    };

    const renderStatGrid = (data) => {
        const cards = section.querySelectorAll("#perfStatGrid .stat-card strong");
        if (cards.length < 3) return;
        const calls = data.total_calls;
        cards[0].textContent = typeof calls === "number" ? calls.toLocaleString() : (calls ?? "0");
        cards[1].textContent = data.total_tokens ?? "0";
        cards[2].textContent = `$${data.total_cost ?? "0"}`;
    };

    const renderChart = (usage) => {
        const chart = section.querySelector("#perfCallsChart");
        if (!chart) return;
        if (!usage || usage.length === 0) {
            renderEmpty(chart, "표시할 호출 데이터가 없습니다.");
            return;
        }
        chart.innerHTML = usage.map((item) => `
            <div>
                <span class="bar q" style="height: ${item.calls_height}%"></span>
                <span class="bar u" style="height: ${item.emb_calls_height}%"></span>
                <small>${item.date}</small>
            </div>
        `).join("");
    };

    const renderBottleneck = (nodes) => {
        const box = section.querySelector("#perfBottleneck");
        if (!box) return;
        if (!nodes || nodes.length === 0) {
            renderEmpty(box, "표시할 병목 데이터가 없습니다.");
            return;
        }
        box.innerHTML = nodes.map((node) => `
            <div class="bottleneck-row"><span>${node.label}</span><i style="width: ${node.load_percent}%"></i><b>${node.calls}</b></div>
        `).join("");
    };

    const fetchData = async (period) => {
        const token = ++requestToken;
        currentPeriod = period;
        if (rangeLabel) rangeLabel.textContent = `(${PERIOD_LABELS[period] || ""})`;
        showStatus("데이터를 불러오는 중입니다...");

        try {
            const res = await fetch(`/api/admin/performance/?period=${period}`);
            if (!res.ok) {
                throw new Error(`요청 실패 (status ${res.status})`);
            }
            const data = await res.json();

            // 응답이 늦게 도착한 사이 사용자가 다른 기간을 눌렀다면 이 응답은 버림
            if (token !== requestToken) return;

            renderNodeCards(data.langgraph_nodes);
            renderStatGrid(data);
            renderChart(data.llm_usage);
            renderBottleneck(data.langgraph_nodes);
            hideStatus();
        } catch (err) {
            if (token !== requestToken) return;
            console.error("성능 데이터 조회 실패:", err);
            showStatus("성능 데이터를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.", { withRetry: true });
        }
    };

    toggle?.addEventListener("click", (event) => {
        const btn = event.target.closest("[data-period]");
        if (!btn || btn.classList.contains("active")) return;
        toggle.querySelectorAll("button").forEach((n) => n.classList.remove("active"));
        btn.classList.add("active");
        fetchData(btn.dataset.period);
    });

    retryBtn?.addEventListener("click", () => fetchData(currentPeriod));

    fetchData(currentPeriod);
}