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
            appendMessage(messages, "ai", data.answer, true);
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
        if (event.target.closest("[data-open-drawer]")) drawer.hidden = false;
    });
    document.querySelectorAll("[data-close-drawer]").forEach((node) =>
        node.addEventListener("click", () => drawer.hidden = true));
}