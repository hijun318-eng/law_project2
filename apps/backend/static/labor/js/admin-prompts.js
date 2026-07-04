import { postJson, escapeHtml } from "./utils.js";

export function initAdminPrompts() {
    const section = document.querySelector("[data-prompt-api]");
    if (!section) return;

    const listButtons = section.querySelectorAll("[data-prompt-id]");
    const title = document.querySelector("#promptTitle");
    const meta = document.querySelector("#promptMeta");
    const placeholders = document.querySelector("#promptPlaceholders");
    const textarea = document.querySelector("#promptContent");
    const errorsBox = document.querySelector("#promptErrors");
    const saveBtn = document.querySelector("#promptSaveBtn");
    const saveStatus = document.querySelector("#promptSaveStatus");
    const confirmModal = document.querySelector("#promptConfirm");
    const confirmBtn = document.querySelector("#promptConfirmBtn");
    const historyBox = document.querySelector("#promptHistory");

    let selectedId = null;
    let isBusy = false; 

    const showError = (message) => {
        errorsBox.hidden = false;
        errorsBox.innerHTML = `<p>${escapeHtml(message)}</p>`;
    };

    const setBusy = (busy, btn) => {
        isBusy = busy;
        if (btn) btn.disabled = busy;
    };

    const selectTemplate = (id) => {
        if (!id) return;
        selectedId = id;
        listButtons.forEach((btn) => btn.classList.toggle("active", btn.dataset.promptId === id));
        saveStatus.textContent = "";
        saveStatus.classList.remove("success");
        errorsBox.hidden = true;

        postJson(section.dataset.promptApi, { action: "get", id })
            .then((data) => {
                if (!data || data.error) {
                    showError(data?.error || "템플릿 정보를 불러오지 못했습니다.");
                    return;
                }
                title.textContent = data.name ?? "";
                meta.textContent = `마지막 수정: ${data.updated_at ?? "-"} · ${data.updated_by ?? "-"}`;
                textarea.value = data.content ?? "";
                renderPlaceholders(data.placeholders || [], data.content || "");
                renderHistory(data.history || []);
            })
            .catch((err) => {
                console.error("프롬프트 조회 실패:", err);
                showError("템플릿 정보를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.");
            });
    };

    const renderPlaceholders = (list, content) => {
        placeholders.innerHTML = list.map((p) =>
            `<span class="placeholder-tag ${content.includes(p) ? "ok" : ""}">${escapeHtml(p)}</span>`
        ).join("");
    };

    const renderHistory = (history) => {
        historyBox.innerHTML = history.length
            ? history.map((v, i) => `
                <article class="list-card">
                    <span class="version-badge ${i === 0 ? "current" : ""}">v${v.version}${i === 0 ? " · 현재" : ""}</span>
                    <strong>${escapeHtml(v.summary)}</strong>
                    <time>${escapeHtml(v.updated_at)} · ${escapeHtml(v.updated_by)}</time>
                    ${i !== 0 ? `<button type="button" class="mini-button" data-rollback="${v.version}">롤백</button>` : ""}
                </article>
            `).join("")
            : `<p class="perf-empty">버전 이력이 없습니다.</p>`;
    };

    listButtons.forEach((btn) => btn.addEventListener("click", () => {
        if (isBusy) return;
        selectTemplate(btn.dataset.promptId);
    }));
    if (listButtons.length) selectTemplate(listButtons[0].dataset.promptId);

    document.querySelector("[data-prompt-panel-tabs]")?.addEventListener("click", (event) => {
        const btn = event.target.closest("[data-prompt-panel]");
        if (!btn) return;
        document.querySelectorAll("[data-prompt-panel]").forEach((n) => n.classList.remove("active"));
        btn.classList.add("active");
        document.querySelectorAll("[data-prompt-view]").forEach((panel) =>
            panel.hidden = panel.dataset.promptView !== btn.dataset.promptPanel);
    });

    saveBtn?.addEventListener("click", () => {
        if (isBusy || !selectedId) return;
        if (!textarea.value.trim()) {
            showError("프롬프트 내용을 입력해주세요.");
            return;
        }
        setBusy(true, saveBtn);
        postJson(section.dataset.promptApi, { action: "validate", id: selectedId, content: textarea.value })
            .then((data) => {
                if (data.errors && data.errors.length) {
                    errorsBox.hidden = false;
                    errorsBox.innerHTML = data.errors.map((e) => `<p>${escapeHtml(e)}</p>`).join("");
                    return;
                }
                errorsBox.hidden = true;
                confirmModal.hidden = false;
            })
            .catch((err) => {
                console.error("프롬프트 검증 실패:", err);
                showError("프롬프트 검증 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.");
            })
            .finally(() => setBusy(false, saveBtn));
    });

    document.querySelectorAll("[data-close-confirm]").forEach((btn) =>
        btn.addEventListener("click", () => confirmModal.hidden = true));

    confirmBtn?.addEventListener("click", () => {
        if (isBusy || !selectedId) return;
        setBusy(true, confirmBtn);
        postJson(section.dataset.promptApi, { action: "save", id: selectedId, content: textarea.value })
            .then((data) => {
                if (data && data.error) {
                    confirmModal.hidden = true;
                    showError(data.error);
                    return;
                }
                confirmModal.hidden = true;
                saveStatus.textContent = "저장되었습니다";
                saveStatus.classList.add("success");
                selectTemplate(selectedId);
            })
            .catch((err) => {
                console.error("프롬프트 저장 실패:", err);
                confirmModal.hidden = true;
                showError("저장 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.");
            })
            .finally(() => setBusy(false, confirmBtn));
    });

    historyBox?.addEventListener("click", (event) => {
        const btn = event.target.closest("[data-rollback]");
        if (!btn || isBusy || !selectedId) return;
        setBusy(true, btn);
        postJson(section.dataset.promptApi, { action: "rollback", id: selectedId, version: btn.dataset.rollback })
            .then((data) => {
                if (data && data.error) {
                    showError(data.error);
                    return;
                }
                selectTemplate(selectedId);
            })
            .catch((err) => {
                console.error("프롬프트 롤백 실패:", err);
                showError("롤백 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.");
            })
            .finally(() => setBusy(false, btn));
    });
}