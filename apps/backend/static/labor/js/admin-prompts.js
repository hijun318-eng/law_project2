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

    const selectTemplate = (id) => {
        selectedId = id;
        listButtons.forEach((btn) => btn.classList.toggle("active", btn.dataset.promptId === id));
        postJson(section.dataset.promptApi, { action: "get", id }).then((data) => {
            title.textContent = data.name;
            meta.textContent = `마지막 수정: ${data.updated_at} · ${data.updated_by}`;
            textarea.value = data.content;
            renderPlaceholders(data.placeholders, data.content);
            errorsBox.hidden = true;
            saveStatus.textContent = "";
            saveStatus.classList.remove("success");
            renderHistory(data.history || []);
        });
    };

    const renderPlaceholders = (list, content) => {
        placeholders.innerHTML = list.map((p) =>
            `<span class="placeholder-tag ${content.includes(p) ? "ok" : ""}">${escapeHtml(p)}</span>`
        ).join("");
    };

    const renderHistory = (history) => {
        historyBox.innerHTML = history.map((v, i) => `
            <article class="list-card">
                <span class="version-badge ${i === 0 ? "current" : ""}">v${v.version}${i === 0 ? " · 현재" : ""}</span>
                <strong>${escapeHtml(v.summary)}</strong>
                <time>${escapeHtml(v.updated_at)} · ${escapeHtml(v.updated_by)}</time>
                ${i !== 0 ? `<button type="button" class="mini-button" data-rollback="${v.version}">롤백</button>` : ""}
            </article>
        `).join("");
    };

    listButtons.forEach((btn) => btn.addEventListener("click", () => selectTemplate(btn.dataset.promptId)));
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
        postJson(section.dataset.promptApi, { action: "validate", id: selectedId, content: textarea.value }).then((data) => {
            if (data.errors && data.errors.length) {
                errorsBox.hidden = false;
                errorsBox.innerHTML = data.errors.map((e) => `<p>${escapeHtml(e)}</p>`).join("");
                return;
            }
            errorsBox.hidden = true;
            confirmModal.hidden = false;
        });
    });

    document.querySelectorAll("[data-close-confirm]").forEach((btn) =>
        btn.addEventListener("click", () => confirmModal.hidden = true));

    confirmBtn?.addEventListener("click", () => {
        postJson(section.dataset.promptApi, { action: "save", id: selectedId, content: textarea.value }).then(() => {
            confirmModal.hidden = true;
            saveStatus.textContent = "저장되었습니다";
            saveStatus.classList.add("success");
            selectTemplate(selectedId);
        });
    });

    historyBox?.addEventListener("click", (event) => {
        const btn = event.target.closest("[data-rollback]");
        if (!btn) return;
        postJson(section.dataset.promptApi, { action: "rollback", id: selectedId, version: btn.dataset.rollback })
            .then(() => selectTemplate(selectedId));
    });
}