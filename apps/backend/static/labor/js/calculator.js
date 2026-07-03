import { postJson, appendMessage, escapeHtml } from "./utils.js";

function renderResult(result) {
    if (!result) return "";
    const lines = result.lines.map((line) => `<p>${escapeHtml(line)}</p>`).join("");
    return `<div class="result-box ${result.tone}"><span>${escapeHtml(result.label)}</span><strong>${escapeHtml(result.amount_display)}</strong>${lines}${result.note ? `<p>${escapeHtml(result.note)}</p>` : ""}<p>※ 이 계산은 참고용이며 실제 금액과 다를 수 있습니다</p></div>`;
}

export function initCalculator() {
    const calcSection = document.querySelector("[data-calc-api]");
    if (!calcSection) return;

    let calcType = "severance";
    const result = document.querySelector("#calcResult");
    const modeButtons = document.querySelectorAll("[data-calc-mode]");
    const panels = document.querySelectorAll("[data-calc-panel]");
    const monthsField = document.querySelector("[data-months-field]");
    const hoursField = document.querySelector("[data-hours-field]");
    const salaryField = document.querySelector("[data-salary-field]");
    const minimumBox = document.querySelector("[data-minimum-box]");

    modeButtons.forEach((button) => button.addEventListener("click", () => {
        modeButtons.forEach((node) => node.classList.remove("active"));
        button.classList.add("active");
        panels.forEach((panel) => panel.hidden = panel.dataset.calcPanel !== button.dataset.calcMode);
    }));

    document.querySelectorAll("[data-calc-type]").forEach((button) => button.addEventListener("click", () => {
        calcType = button.dataset.calcType;
        document.querySelectorAll("[data-calc-type]").forEach((node) => node.classList.remove("active"));
        button.classList.add("active");
        monthsField.hidden = calcType !== "severance";
        hoursField.hidden = !["weekly", "minimum"].includes(calcType);
        salaryField.hidden = calcType === "minimum";
        minimumBox.hidden = calcType !== "minimum";
        result.innerHTML = "";
    }));

    document.querySelector("#calcForm")?.addEventListener("submit", (event) => {
        event.preventDefault();
        const form = new FormData(event.currentTarget);
        postJson(calcSection.dataset.calcApi, {
            mode: "form",
            calc_type: calcType,
            salary: form.get("salary"),
            months: form.get("months"),
            hours: form.get("hours"),
        }).then((data) => result.innerHTML = renderResult(data.result));
    });

    document.querySelector("#naturalCalcForm")?.addEventListener("submit", (event) => {
        event.preventDefault();
        const input = document.querySelector("#naturalCalcInput");
        const messages = document.querySelector("#calcMessages");
        const text = input.value.trim();
        if (!text) return;
        appendMessage(messages, "user", text);
        postJson(calcSection.dataset.calcApi, { mode: "chat", text }).then((data) => {
            appendMessage(messages, "ai", escapeHtml(data.message) + (data.result ? renderResult(data.result) : ""), false, true);
            input.value = "";
        });
    });
}