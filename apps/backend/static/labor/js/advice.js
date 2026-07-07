import { postJson, appendMessage, escapeHtml, markdownToHtml, csrf } from "./utils.js?v=2";

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

// case_based_answer 모드 답변(쉬운 요약/법적 근거/결론 구조)에서 "법적 근거" 섹션을 분리해
// 카드 앞면(요약+결론)/뒷면(법적 근거) 두 장으로 나누고, 앞면 오른쪽 버튼으로 뒷면을,
// 뒷면 왼쪽 버튼으로 다시 앞면을 보여주는 전환형 카드로 렌더링.
function renderAnswerWithLegalBasis(markdown) {
    const lines = String(markdown).split("\n");
    const before = [];
    const legal = [];
    const after = [];
    let section = "before";
    for (const line of lines) {
        const trimmed = line.trim();
        if (section === "before" && /^##\s+법적\s*근거\s*$/.test(trimmed)) {
            section = "legal";
            continue;
        }
        if (section === "legal" && /^##\s+/.test(trimmed)) {
            section = "after";
        }
        (section === "before" ? before : section === "legal" ? legal : after).push(line);
    }

    const beforeHtml = markdownToHtml(before.join("\n"));
    const afterHtml = markdownToHtml(after.join("\n"));
    if (legal.length === 0) {
        return `${beforeHtml}${afterHtml}`;
    }
    const legalHtml = markdownToHtml(legal.join("\n"));
    return `<div class="answer-flip">
        <div class="answer-card" data-answer-face="front">
            <button type="button" class="mini-button answer-flip-btn right" data-action="show-legal-basis">법적 근거 →</button>
            ${beforeHtml}${afterHtml}
        </div>
        <div class="answer-card" data-answer-face="back" hidden>
            <button type="button" class="mini-button answer-flip-btn left" data-action="show-summary">← 요약으로</button>
            ${legalHtml}
        </div>
    </div>`;
}

const ANSWER_DISCLAIMER = `<p class="answer-disclaimer">※ 이 답변은 AI가 제공하는 참고 정보이며 법적 효력이 있는 자문이 아닙니다. 구체적인 사안은 노무사·변호사 등 전문가와 상담하세요.</p>`;

function renderProgress(label) {
    return `<div class="progress-indicator"><span class="spinner" aria-hidden="true"></span><span class="progress-label">${escapeHtml(label)}</span><span class="progress-timer">0초</span></div>`;
}

// 노드 시작/종료 이벤트를 사람이 읽을 문장으로 변환.
// 시작: "🔍 판례 직접 검색 중..." / 종료: "🔍 판례 직접 검색 완료 (1.2초)" (+ 있으면 세부 사유)
function formatProgress(data) {
    const elapsedText = data.elapsed != null ? ` (${data.elapsed}초)` : "";
    const base = data.phase === "start" ? `${data.label} 중...` : `${data.label} 완료${elapsedText}`;
    return data.log ? `${base} · ${data.log}` : base;
}

// advice_api는 LangGraph 노드가 진행될 때마다 SSE(text/event-stream)로
// {"type": "progress", ...} 이벤트를 보내고, 마지막에 {"type": "done", ...}로 최종 답변을 보낸다.
// onProgress(label)과 onDone(data)을 호출하며 스트림을 끝까지 읽는다.
function streamAdvice(url, question, { onProgress, onDone, onError }) {
    fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrf() },
        body: JSON.stringify({ question }),
    }).then((response) => {
        if (!response.ok || !response.body) throw new Error(`요청 실패 (status ${response.status})`);
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        const pump = () => reader.read().then(({ done, value }) => {
            if (value) buffer += decoder.decode(value, { stream: true });
            const chunks = buffer.split("\n\n");
            buffer = done ? "" : chunks.pop();
            chunks.forEach((chunk) => {
                const line = chunk.split("\n").find((l) => l.startsWith("data: "));
                if (!line) return;
                const data = JSON.parse(line.slice(6));
                if (data.type === "progress") onProgress(data);
                else if (data.type === "done") onDone(data);
            });
            if (!done) return pump();
        });
        return pump();
    }).catch(onError);
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
        appendMessage(messages, "ai", renderProgress("답변을 준비하고 있습니다..."), false, true);
        const progressBubble = messages.lastElementChild;
        const progressLabel = progressBubble.querySelector(".progress-label");
        const progressTimer = progressBubble.querySelector(".progress-timer");

        const startedAt = Date.now();
        const timerId = setInterval(() => {
            if (progressTimer) progressTimer.textContent = `${Math.floor((Date.now() - startedAt) / 1000)}초`;
        }, 1000);
        const stopTimer = () => clearInterval(timerId);

        streamAdvice(adviceSection.dataset.adviceApi, question, {
            onProgress: (data) => {
                if (progressLabel) progressLabel.textContent = formatProgress(data);
            },
            onDone: (data) => {
                stopTimer();
                progressBubble.remove();
                // 답변에 "## 법적 근거" 섹션이 있으면 카드 전환 UI로, 없으면 그대로 렌더링
                appendMessage(messages, "ai", renderAnswerWithLegalBasis(data.answer) + ANSWER_DISCLAIMER, true, true, data.message_id);
            },
            onError: () => {
                stopTimer();
                progressBubble.remove();
                appendMessage(messages, "ai", "답변을 불러오지 못했습니다. 잠시 후 다시 시도해주세요.");
            },
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

        const flipBtn = event.target.closest("[data-action='show-legal-basis'], [data-action='show-summary']");
        if (flipBtn) {
            const flip = flipBtn.closest(".answer-flip");
            const front = flip?.querySelector("[data-answer-face='front']");
            const back = flip?.querySelector("[data-answer-face='back']");
            if (front && back) {
                const showBack = flipBtn.dataset.action === "show-legal-basis";
                front.hidden = showBack;
                back.hidden = !showBack;
            }
            return;
        }

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