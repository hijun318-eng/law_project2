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

function showUserError(message) {
    const box = document.querySelector("[data-user-error]");
    if (!box) return;
    box.hidden = false;
    box.textContent = message;
}

function hideUserError() {
    const box = document.querySelector("[data-user-error]");
    if (box) box.hidden = true;
}

export function initAdminUsers() {
    document.querySelector("[data-user-search]")?.addEventListener("input", filterUsers);
    document.querySelector("[data-user-status]")?.addEventListener("change", filterUsers);

    document.querySelectorAll("[data-toggle-status]").forEach((button) => button.addEventListener("click", () => {
        if (button.disabled) return;

        const row = button.closest("[data-user-row]");
        const userId = Number(row?.dataset.userId);

        // row나 user_id를 못 찾으면(DOM 구조 변경, 데이터 누락 등) API를 호출하지 않고 즉시 안내
        if (!row || !Number.isInteger(userId)) {
            showUserError("사용자 정보를 확인할 수 없습니다. 새로고침 후 다시 시도해주세요.");
            return;
        }

        const nextStatus = row.dataset.status === "active" ? "suspended" : "active";
        hideUserError();
        button.disabled = true; // 중복 클릭 방지

        postJson("/api/admin/users/toggle-status/", { user_id: userId, status: nextStatus })
            .then(() => {
                // 서버 응답 성공 시에만 UI 업데이트
                row.dataset.status = nextStatus;
                const badge = row.querySelector(".status");
                if (badge) {
                    badge.className = `status ${nextStatus}`;
                    badge.textContent = nextStatus === "active" ? "활성" : "정지";
                }
                button.textContent = nextStatus === "active" ? "계정 정지" : "정지 해제";
            })
            .catch((err) => {
                // 실패 시 UI는 그대로 두고(자동 롤백) 관리자에게 실패 사실을 알림
                console.error("계정 상태 변경 실패:", err);
                showUserError("계정 상태 변경에 실패했습니다. 잠시 후 다시 시도해주세요.");
            })
            .finally(() => {
                button.disabled = false;
            });
    }));
}