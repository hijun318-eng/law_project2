const DONUT_PALETTE = ["#2563eb", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899", "#14b8a6", "#f97316"];

function initCategoryDonut() {
    const donut = document.querySelector("[data-donut]");
    if (!donut) return;

    const segments = [...donut.querySelectorAll(".donut-segment")];
    let cursor = 0;
    const stops = segments.map((seg, i) => {
        const value = parseFloat(seg.dataset.value) || 0;
        const color = DONUT_PALETTE[i % DONUT_PALETTE.length];
        const start = cursor;
        cursor += value;
        return `${color} ${start * 3.6}deg ${cursor * 3.6}deg`;
    });
    donut.style.setProperty("--donut-gradient", stops.join(", "));

    document.querySelectorAll("[data-dot]").forEach((dot) => {
        const i = Number(dot.dataset.dot);
        dot.style.background = DONUT_PALETTE[i % DONUT_PALETTE.length];
    });
}

export function initAdminDashboard() {
    initCategoryDonut();
}