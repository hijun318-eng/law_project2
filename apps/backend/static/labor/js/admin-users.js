function filterUsers() {
    const search = document.querySelector("[data-user-search]")?.value.trim().toLowerCase() || "";
    const status = document.querySelector("[data-user-status]")?.value || "all";
    document.querySelectorAll("[data-user-row]").forEach((row) => {
        const text = row.textContent.toLowerCase();
        row.hidden = !(text.includes(search) && (status === "all" || row.dataset.status === status));
    });
}

export function initAdminUsers() {
    document.querySelector("[data-user-search]")?.addEventListener("input", filterUsers);
    document.querySelector("[data-user-status]")?.addEventListener("change", filterUsers);
    document.querySelectorAll("[data-toggle-status]").forEach((button) => button.addEventListener("click", () => {
        const row = button.closest("[data-user-row]");
        const status = row.dataset.status === "active" ? "suspended" : "active";
        row.dataset.status = status;
        row.querySelector(".status").className = `status ${status}`;
        row.querySelector(".status").textContent = status === "active" ? "활성" : "정지";
        button.textContent = status === "active" ? "계정 정지" : "정지 해제";
    }));
}