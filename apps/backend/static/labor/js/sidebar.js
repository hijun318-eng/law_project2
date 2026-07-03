export function initSidebar() {
    document.querySelector("[data-open-sidebar]")?.addEventListener("click", () =>
        document.querySelector("#sidebar")?.classList.add("open"));
    document.querySelector("[data-close-sidebar]")?.addEventListener("click", () =>
        document.querySelector("#sidebar")?.classList.remove("open"));
}