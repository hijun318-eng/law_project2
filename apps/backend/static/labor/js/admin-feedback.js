export function initAdminFeedback() {
    document.querySelector("[data-feedback-tabs]")?.addEventListener("click", (event) => {
        const button = event.target.closest("[data-feedback-filter]");
        if (!button) return;
        document.querySelectorAll("[data-feedback-filter]").forEach((node) => node.classList.remove("active"));
        button.classList.add("active");
        document.querySelectorAll("[data-feedback-group]").forEach((group) => {
            group.hidden = button.dataset.feedbackFilter === "low" && group.dataset.low !== "true";
        });
    });

    document.querySelectorAll("[data-toggle-group]").forEach((head) => head.addEventListener("click", () => {
        const group = head.closest("[data-feedback-group]");
        const body = group?.querySelector("[data-group-body]");
        const chevron = head.querySelector("[data-chevron]");
        if (!body || !chevron) return;
        body.hidden = !body.hidden;
        chevron.classList.toggle("open", !body.hidden);
    }));
}