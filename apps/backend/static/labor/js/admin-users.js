function filterUsers() {
    const search = document.querySelector("[data-user-search]")?.value.trim().toLowerCase() || "";
    const status = document.querySelector("[data-user-status]")?.value || "all";
    const rows = document.querySelectorAll("[data-user-row]");
    let visibleCount = 0;

    rows.forEach((row) => {
        const text = row.textContent.toLowerCase();
        const match = text.includes(search) && (status === "all" || row.dataset.status === status);
        row.hidden = !match;
        if (match) visibleCount += 1;
    });

    const emptyRow = document.querySelector("[data-user-empty]");
    if (emptyRow) emptyRow.hidden = visibleCount > 0;
}

export function initAdminUsers() {
    document.querySelector("[data-user-search]")?.addEventListener("input", filterUsers);
    document.querySelector("[data-user-status]")?.addEventListener("change", filterUsers);
    document.querySelectorAll("[data-toggle-status]").forEach((button) => button.addEventListener("click", () => {
        if (button.disabled) return;
        button.disabled = true;

        const row = button.closest("[data-user-row]");
        const status = row.dataset.status === "active" ? "suspended" : "active";

        row.dataset.status = status;
        row.querySelector(".status").className = `status ${status}`;
        row.querySelector(".status").textContent = status === "active" ? "활성" : "정지";
        button.textContent = status === "active" ? "계정 정지" : "정지 해제";

        button.disabled = false;
    }));
}