export function initMypage() {
    document.querySelector("[data-tabs]")?.addEventListener("click", (event) => {
        const button = event.target.closest("[data-tab]");
        if (!button) return;
        document.querySelectorAll("[data-tab]").forEach((node) => node.classList.remove("active"));
        button.classList.add("active");
        document.querySelectorAll("[data-tab-panel]").forEach((panel) =>
            panel.hidden = panel.dataset.tabPanel !== button.dataset.tab);
    });
}