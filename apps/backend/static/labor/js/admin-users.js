import { postJson } from "./utils.js";

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

        // 백엔드 API 호출
        const userId = parseInt(row.dataset.userId);
        postJson("/api/admin/users/toggle-status/", { user_id: userId, status: status })
            .then(() => {
                // 서버 응답 성공 시에만 UI 업데이트
                row.dataset.status = status;
                row.querySelector(".status").className = `status ${status}`;
                row.querySelector(".status").textContent = status === "active" ? "활성" : "정지";
                button.textContent = status === "active" ? "계정 정지" : "정지 해제";
            })
            .catch(() => {
                // 실패 시 아무것도 변경하지 않음 (롤백)
                console.error("계정 상태 변경 실패");
            })
            .finally(() => {
                button.disabled = false;
            });
    }));
}