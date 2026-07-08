import { postJson, appendMessage, escapeHtml, markdownToHtml, LEGAL_DISCLAIMER_HTML } from "./utils.js?v=3";

const FIELD_LABELS = { salary: "월 기본급", months: "근무 기간", hours: "주 소정근로시간" };

function isFieldVisible(input) {
    const label = input.closest("label");
    return !!label && !label.hidden;
}

function validateField(input) {
    const errorEl = input.parentElement.querySelector(".field-error");
    const label = FIELD_LABELS[input.dataset.validate] || "값";
    const raw = input.value.trim();
    const min = input.min !== "" ? Number(input.min) : -Infinity;
    const max = input.max !== "" ? Number(input.max) : Infinity;
    let message = "";
    if (raw === "") {
        message = `${label}을(를) 입력해주세요.`;
    } else {
        const value = Number(raw);
        if (Number.isNaN(value)) {
            message = `${label}에 숫자를 입력해주세요.`;
        } else if (value <= min) {
            message = `${label}은(는) ${min}보다 커야 합니다.`;
        } else if (value > max) {
            message = `${label}은(는) ${max} 이하여야 합니다.`;
        }
    }
    const isValid = !message;
    input.classList.toggle("invalid", !isValid);
    if (errorEl) {
        errorEl.textContent = message;
        errorEl.hidden = isValid;
    }
    return isValid;
}

function updateCalcFormValidity() {
    const submitBtn = document.querySelector("#calcForm button[type='submit']");
    const inputs = document.querySelectorAll("#calcForm [data-validate]");
    let allValid = true;
    inputs.forEach((input) => {
        if (!isFieldVisible(input)) {
            const errorEl = input.parentElement.querySelector(".field-error");
            if (errorEl) errorEl.hidden = true;
            input.classList.remove("invalid");
            return;
        }
        if (!validateField(input)) allValid = false;
    });
    if (submitBtn) submitBtn.disabled = !allValid;
    return allValid;
}

function renderResult(result) {
    if (!result) return "";
    const lines = result.lines.map((line) => `<p>${escapeHtml(line)}</p>`).join("");
    return `<div class="result-box ${result.tone}"><span>${escapeHtml(result.label)}</span><strong>${escapeHtml(result.amount_display)}</strong>${lines}${result.note ? `<p>${escapeHtml(result.note)}</p>` : ""}<p>※ 이 계산은 참고용이며 실제 금액과 다를 수 있습니다</p>${LEGAL_DISCLAIMER_HTML}</div>`;
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
        updateCalcFormValidity();
    }));

    document.querySelectorAll("#calcForm [data-validate]").forEach((input) => {
        input.addEventListener("input", updateCalcFormValidity);
    });
    updateCalcFormValidity();

    document.querySelector("#calcForm")?.addEventListener("submit", (event) => {
        event.preventDefault();
        if (!updateCalcFormValidity()) return;
        const form = new FormData(event.currentTarget);
        postJson(calcSection.dataset.calcApi, {
            mode: "form",
            calc_type: calcType,
            salary: form.get("salary"),
            months: form.get("months"),
            hours: form.get("hours"),
        }).then((data) => result.innerHTML = renderResult(data.result));
    });

    // ReAct 에이전트가 "월급이 얼마였나요?" 처럼 되물었을 때, 사용자가 답만 입력해도
    // 이전에 말한 근속연수 등을 잊지 않도록 대화 기록을 유지해 매 요청마다 함께 보낸다.
    const naturalCalcHistory = [];

    document.querySelector("#naturalCalcForm")?.addEventListener("submit", (event) => {
        event.preventDefault();
        const input = document.querySelector("#naturalCalcInput");
        const messages = document.querySelector("#calcMessages");
        const text = input.value.trim();
        if (!text) return;
        appendMessage(messages, "user", text);
        postJson(calcSection.dataset.calcApi, { mode: "chat", text, history: naturalCalcHistory }).then((data) => {
            if (data.result) {
                appendMessage(messages, "ai", renderResult(data.result), false, true);
            } else {
                appendMessage(messages, "ai", markdownToHtml(data.message) + LEGAL_DISCLAIMER_HTML, false, true);
            }
            naturalCalcHistory.push({ role: "user", content: text });
            naturalCalcHistory.push({ role: "assistant", content: data.message });
            input.value = "";
        });
    });
}