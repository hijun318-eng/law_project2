import { postJson, appendMessage, escapeHtml } from "./utils.js?v=2";

function renderLawSources(sources) {
    if (!sources || sources.length === 0) {
        return `<p class="empty-state">이 답변에 참고한 법령 원문이 없습니다.</p>`;
    }
    return sources.map((src) => {
        const heading = [src.law_name, src.article_no].filter(Boolean).join(" ")
            + (src.article_title ? ` (${src.article_title})` : "");
        return `<article><strong>${escapeHtml(heading)}</strong><p>${escapeHtml(src.page_content || "")}</p></article>`;
    }).join("");
}

function renderPrecedents(precedents) {
    if (!precedents || precedents.length === 0) {
        return `<p class="empty-state">이 답변에 참고한 판례가 없습니다.</p>`;
    }
    return precedents.map((prec) => {
        const heading = [prec.case_no, prec.category].filter(Boolean).join(" · ");
        return `<article><strong>${escapeHtml(heading)}</strong><p>${escapeHtml(prec.content || "")}</p></article>`;
    }).join("");
}

export function initAdvice() {
    const adviceSection = document.querySelector("[data-advice-api]");
    if (!adviceSection) return;

    const form = document.querySelector("#adviceForm");
    const input = document.querySelector("#adviceInput");
    const messages = document.querySelector("#adviceMessages");
    const quick = document.querySelector("[data-quick-questions]");
    const drawer = document.querySelector("#lawDrawer");
    const lawDrawerBody = document.querySelector("[data-drawer-panel='law']");
    const precedentDrawerBody = document.querySelector("[data-drawer-panel='precedent']");
    const drawerTabs = document.querySelector("[data-drawer-tabs]");
    const historyApiBase = adviceSection.dataset.adviceHistoryApi?.replace(/0\/?$/, "");

    const openLawDrawer = (messageId) => {
        if (!lawDrawerBody || !precedentDrawerBody) return;
        lawDrawerBody.innerHTML = `<p class="empty-state">불러오는 중...</p>`;
        precedentDrawerBody.innerHTML = "";
        drawerTabs?.querySelectorAll("[data-drawer-tab]").forEach((btn) => btn.classList.toggle("active", btn.dataset.drawerTab === "law"));
        lawDrawerBody.hidden = false;
        precedentDrawerBody.hidden = true;
        drawer.hidden = false;
        fetch(`${historyApiBase}${messageId}/`)
            .then((response) => response.json())
            .then((data) => {
                lawDrawerBody.innerHTML = renderLawSources(data.sources?.law);
                precedentDrawerBody.innerHTML = renderPrecedents(data.sources?.precedent);
            })
            .catch(() => {
                lawDrawerBody.innerHTML = `<p class="empty-state">법령·판례를 불러오지 못했습니다.</p>`;
            });
    };

    const send = (text) => {
        const question = text.trim();
        if (!question) return;
        quick.hidden = true;
        appendMessage(messages, "user", question);
        appendMessage(messages, "ai", "답변을 준비하고 있습니다...");
        postJson(adviceSection.dataset.adviceApi, { question }).then((data) => {
            messages.lastElementChild.remove();
            appendMessage(messages, "ai", data.answer, true, false, data.message_id);
        });
    };

    quick?.addEventListener("click", (event) => {
        const button = event.target.closest("[data-question]");
        if (button) send(button.dataset.question);
    });
    form?.addEventListener("submit", (event) => {
        event.preventDefault();
        send(input.value);
        input.value = "";
    });
    messages?.addEventListener("click", (event) => {
        const drawerBtn = event.target.closest("[data-action='open-drawer']");
        if (drawerBtn) { openLawDrawer(drawerBtn.dataset.mid); return; }

        const fbBtn = event.target.closest("[data-action^='feedback_']");
        if (!fbBtn) return;
        const messageId = fbBtn.dataset.mid;
        const action = fbBtn.dataset.action === "feedback_like" ? "like" : "dislike";
        postJson(adviceSection.dataset.adviceFeedbackApi, { message_id: parseInt(messageId), action }).then((res) => {
            if (!res.ok) return;
            const parent = fbBtn.closest(".message-actions");
            if (parent) {
                parent.querySelectorAll("[data-action^='feedback_']").forEach((b) => {
                    b.classList.remove("active");
                    b.textContent = b.textContent.replace("✓ ", "");
                });
            }
            if (res.feedback === true) {
                const likeBtn = parent?.querySelector("[data-action='feedback_like']");
                if (likeBtn) { likeBtn.classList.add("active"); likeBtn.textContent = "✓ " + likeBtn.textContent; }
            } else if (res.feedback === false) {
                const dislikeBtn = parent?.querySelector("[data-action='feedback_dislike']");
                if (dislikeBtn) { dislikeBtn.classList.add("active"); dislikeBtn.textContent = "✓ " + dislikeBtn.textContent; }
            }
        });
    });
    document.querySelectorAll("[data-close-drawer]").forEach((node) =>
        node.addEventListener("click", () => drawer.hidden = true));
    drawerTabs?.addEventListener("click", (event) => {
        const tabBtn = event.target.closest("[data-drawer-tab]");
        if (!tabBtn) return;
        drawerTabs.querySelectorAll("[data-drawer-tab]").forEach((btn) => btn.classList.toggle("active", btn === tabBtn));
        const tab = tabBtn.dataset.drawerTab;
        lawDrawerBody.hidden = tab !== "law";
        precedentDrawerBody.hidden = tab !== "precedent";
    });

    const initialQuestion = adviceSection.dataset.initialQuestion?.trim();
    if (initialQuestion) {
        send(initialQuestion);
        const url = new URL(window.location.href);
        url.searchParams.delete("question");
        window.history.replaceState({}, "", url);
    }
}