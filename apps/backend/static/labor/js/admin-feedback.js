export function initAdminFeedback() {
    document.querySelector("[data-feedback-tabs]")?.addEventListener("click", (event) => {
        const button = event.target.closest("[data-feedback-filter]");
        if (!button) return;
        document.querySelectorAll("[data-feedback-filter]").forEach((node) => node.classList.remove("active"));
        button.classList.add("active");
        document.querySelectorAll("[data-feedback-card]").forEach((card) => {
            card.hidden = button.dataset.feedbackFilter === "low" && card.dataset.low !== "true";
        });
    });
}