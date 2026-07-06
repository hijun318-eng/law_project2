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

    const renderBottleneck = (items) => {
        const box = section.querySelector("#perfBottleneck");
        if (!box) return;
        if (!items || items.length === 0) {
            renderEmpty(box, "표시할 병목 데이터가 없습니다.");
            return;
        }
        box.innerHTML = items.map((item) => `
            <div class="bottleneck-row"><span>${item.bottleneck_label}</span><i style="width: ${item.load_percent}%"></i><b>${item.duration_sec}s</b></div>
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
            renderBottleneck(data.slow_queries);
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

    // --- 가격 설정 ---
    const fetchPriceConfig = async () => {
        try {
            const res = await fetch("/api/admin/performance/price-config/");
            if (!res.ok) return;
            const configs = await res.json();
            renderPriceConfig(configs);
        } catch (err) {
            console.error("가격 설정 로드 실패:", err);
        }
    };

    const renderPriceConfig = (configs) => {
        const tbody = document.getElementById("priceConfigBody");
        if (!tbody) return;
        if (!configs || configs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;padding:16px;color:var(--text-muted);">설정된 가격 정보가 없습니다.</td></tr>';
            return;
        }
        tbody.innerHTML = configs.map((cfg) => `
            <tr style="border-bottom:1px solid var(--border);">
                <td style="padding:10px 8px;font-weight:600;">${cfg.model_name}</td>
                <td style="padding:10px 8px;text-align:right;">
                    <input type="number" step="0.01" min="0" value="${cfg.prompt_token_price}"
                        class="price-input" data-model="${cfg.model_name}" data-type="prompt"
                        style="width:90px;text-align:right;padding:4px 8px;border:1px solid var(--border);border-radius:4px;">
                </td>
                <td style="padding:10px 8px;text-align:right;">
                    <input type="number" step="0.01" min="0" value="${cfg.completion_token_price}"
                        class="price-input" data-model="${cfg.model_name}" data-type="completion"
                        style="width:90px;text-align:right;padding:4px 8px;border:1px solid var(--border);border-radius:4px;">
                </td>
                <td style="padding:10px 8px;text-align:center;">
                    <button type="button" class="btn-save-price" data-model="${cfg.model_name}"
                        style="padding:4px 16px;border:1px solid var(--accent);border-radius:4px;background:var(--accent);color:#fff;cursor:pointer;">
                        저장
                    </button>
                </td>
            </tr>
        `).join("");

        // 저장 버튼 이벤트
        tbody.querySelectorAll(".btn-save-price").forEach((btn) => {
            btn.addEventListener("click", () => {
                const model = btn.dataset.model;
                const promptInput = tbody.querySelector(`.price-input[data-model="${model}"][data-type="prompt"]`);
                const completionInput = tbody.querySelector(`.price-input[data-model="${model}"][data-type="completion"]`);
                const promptPrice = promptInput ? parseFloat(promptInput.value) : 0;
                const completionPrice = completionInput ? parseFloat(completionInput.value) : 0;
                savePriceConfig(model, promptPrice, completionPrice, btn);
            });
        });
    };

    const savePriceConfig = async (modelName, promptPrice, completionPrice, btn) => {
        const originalText = btn.textContent;
        btn.textContent = "저장 중...";
        btn.disabled = true;
        try {
            const res = await fetch("/api/admin/performance/price-config/", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    model_name: modelName,
                    prompt_token_price: promptPrice,
                    completion_token_price: completionPrice,
                }),
            });
            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                throw new Error(errData.error || `요청 실패 (${res.status})`);
            }
            btn.textContent = "✓ 저장됨";
            btn.style.background = "var(--green, #2e7d32)";
            setTimeout(() => {
                btn.textContent = originalText;
                btn.style.background = "";
                btn.disabled = false;
            }, 2000);
        } catch (err) {
            console.error("가격 저장 실패:", err);
            btn.textContent = "✗ 실패";
            btn.style.background = "var(--red, #c62828)";
            setTimeout(() => {
                btn.textContent = originalText;
                btn.style.background = "";
                btn.disabled = false;
            }, 2000);
        }
    };

    fetchPriceConfig();
}