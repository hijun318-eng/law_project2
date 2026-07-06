export function initMypage() {
    // ----- 탭 전환 -----
    const tabsEl = document.querySelector("[data-tabs]");
    if (tabsEl) {
        tabsEl.addEventListener("click", (e) => {
            const btn = e.target.closest("[data-tab]");
            if (!btn) return;
            document.querySelectorAll("[data-tab]").forEach((n) => n.classList.remove("active"));
            btn.classList.add("active");
            document.querySelectorAll("[data-tab-panel]").forEach((p) => {
                p.hidden = p.dataset.tabPanel !== btn.dataset.tab;
            });
        });
    }

    // ----- 아코디언 (각 카드에 직접 이벤트 등록) -----
    document.querySelectorAll("[data-history-id]").forEach((card) => {
        card.addEventListener("click", (e) => {
            // 피드백 버튼 클릭은 제외
            if (e.target.closest("[data-action^='feedback_']")) return;
            const body = card.querySelector(".mypage-card-body");
            if (!body) return;
            body.hidden = !body.hidden;
            card.classList.toggle("open", !body.hidden);
        });
    });

    // ----- 피드백 토글 -----
    document.querySelectorAll("[data-action^='feedback_']").forEach((btn) => {
        btn.addEventListener("click", (e) => {
            e.stopPropagation();
            const card = e.target.closest("[data-history-id]");
            if (!card) return;
            const msgId = parseInt(card.dataset.historyId, 10);
            const action = e.target.dataset.action === "feedback_like" ? "like" : "dislike";

            fetch("/api/advice/feedback/", {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-CSRFToken": (() => {
                    const m = document.cookie.match(/csrftoken=([^;]+)/);
                    return m ? decodeURIComponent(m[1]) : "";
                })() },
                body: JSON.stringify({ message_id: msgId, action }),
            }).then((r) => r.json()).then((res) => {
                if (!res.ok) return;
                const parent = e.target.closest(".message-actions");
                if (!parent) return;
                parent.querySelectorAll("[data-action^='feedback_']").forEach((b) => {
                    b.classList.remove("active");
                    b.textContent = b.textContent.replace("✓ ", "");
                });
                if (res.feedback === true) {
                    const lb = parent.querySelector("[data-action='feedback_like']");
                    if (lb) { lb.classList.add("active"); lb.textContent = "✓ " + lb.textContent; }
                } else if (res.feedback === false) {
                    const db = parent.querySelector("[data-action='feedback_dislike']");
                    if (db) { db.classList.add("active"); db.textContent = "✓ " + db.textContent; }
                }
            });
        });
    });
}