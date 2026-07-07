import { initSidebar } from "./sidebar.js";
import { initAdvice } from "./advice.js?v=4";
import { initCalculator } from "./calculator.js";
import { initNews } from "./news.js?v=4";
import { markdownToHtml } from "./utils.js?v=2";

console.log("[app-main] module started");
initSidebar();
initAdvice();
initCalculator();
initNews();
console.log("[app-main] other inits done");

// mypage 초기화 (인라인 — 모듈 의존성 우회)
(function(){
    console.log("[mypage] IIFE entered");
    const historyPanel = document.querySelector("[data-tab-panel='history']");
    console.log("[mypage] historyPanel:", historyPanel);
    if (!historyPanel) return;
    console.log("[mypage] found historyPanel, registering events");

    console.log("[mypage] registering tab listener");
    // ------ 탭 전환 ------
    document.querySelector("[data-tabs]")?.addEventListener("click", (e) => {
        const btn = e.target.closest("[data-tab]");
        if (!btn) return;
        document.querySelectorAll("[data-tab]").forEach((n) => n.classList.remove("active"));
        btn.classList.add("active");
        document.querySelectorAll("[data-tab-panel]").forEach((p) => {
            p.hidden = p.dataset.tabPanel !== btn.dataset.tab;
        });
    });

    const historyCards = document.querySelectorAll("[data-history-id]");
    // ------ 아코디언 (historyPanel 위임) ------
    historyPanel.addEventListener("click", async (e) => {
        const card = e.target.closest("[data-history-id]");
        if (!card) return;
        if (e.target.closest("[data-action^='feedback_']")) return;

        const body = card.querySelector(".mypage-card-body");
        if (!body) return;

        // 이미 열려있으면 닫기
        if (!body.hidden) {
            body.hidden = true;
            card.classList.remove("open");
            return;
        }

        // 다른 열린 카드 모두 닫기
        historyPanel.querySelectorAll(".mypage-card.open").forEach((oc) => {
            oc.classList.remove("open");
            const ob = oc.querySelector(".mypage-card-body");
            if (ob) ob.hidden = true;
        });

        const chatWin = body.querySelector(".chat-window");
        if (!chatWin) return;

        // 데이터 로드
        body.hidden = false;
        card.classList.add("open");

        if (!chatWin.dataset.loaded) {
            chatWin.dataset.loaded = "loading";
            const msgUser = chatWin.querySelector(".message.user");
            const msgAi = chatWin.querySelector(".message.ai");
            if (msgUser) msgUser.innerHTML = "로딩 중...";

            try {
                const res = await fetch(card.dataset.historyApi);
                const data = await res.json();
                if (data.error) {
                    if (msgUser) msgUser.textContent = "데이터를 불러올 수 없습니다.";
                } else {
                    if (msgUser) msgUser.innerHTML = markdownToHtml(data.question);
                    if (msgAi) msgAi.innerHTML = markdownToHtml(data.answer || "(답변 없음)");
                    chatWin.dataset.loaded = "true";
                }
            } catch {
                if (msgUser) msgUser.textContent = "불러오기 실패";
            }
        }
    });

    // ------ 피드백 ------
    document.querySelectorAll("[data-action^='feedback_']").forEach((btn) => {
        btn.addEventListener("click", (e) => {
            e.stopPropagation();
            const card = e.target.closest("[data-history-id]");
            if (!card) return;
            const msgId = parseInt(card.dataset.historyId, 10);

            const csrf = (document.cookie.match(/csrftoken=([^;]+)/) || [])[1];
            fetch("/api/advice/feedback/", {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-CSRFToken": csrf ? decodeURIComponent(csrf) : "" },
                body: JSON.stringify({ message_id: msgId, action: btn.dataset.action === "feedback_like" ? "like" : "dislike" }),
            }).then((r) => r.json()).then((res) => {
                if (!res.ok) return;
                const parent = btn.closest(".message-actions");
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
})();