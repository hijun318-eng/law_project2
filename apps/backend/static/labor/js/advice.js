import { postJson, appendMessage } from "./utils.js";

export function initAdvice() {
    const adviceSection = document.querySelector("[data-advice-api]");
    if (!adviceSection) return;

    const form = document.querySelector("#adviceForm");
    const input = document.querySelector("#adviceInput");
    const messages = document.querySelector("#adviceMessages");
    const quick = document.querySelector("[data-quick-questions]");
    const drawer = document.querySelector("#lawDrawer");

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
        const drawerBtn = event.target.closest("[data-open-drawer]");
        if (drawerBtn) { drawer.hidden = false; return; }

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

    const initialQuestion = adviceSection.dataset.initialQuestion?.trim();
    if (initialQuestion) {
        send(initialQuestion);
        const url = new URL(window.location.href);
        url.searchParams.delete("question");
        window.history.replaceState({}, "", url);
    }
}