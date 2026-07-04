const DONUT_PALETTE = ["#2563eb", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899", "#14b8a6", "#f97316"];

function initCategoryDonut() {
    const donut = document.querySelector("[data-donut]");
    if (!donut) return;

    const segments = [...donut.querySelectorAll(".donut-segment")];

    if (segments.length === 0) {
        donut.style.setProperty("--donut-gradient", "var(--border, #e5e7eb) 0deg 360deg");
        return;
    }

    let cursor = 0;
    const stops = segments.map((seg, i) => {
        const raw = Number(seg.dataset.value);
        const value = Number.isFinite(raw) && raw > 0 ? raw : 0;
        const color = DONUT_PALETTE[i % DONUT_PALETTE.length];
        const start = cursor;
        cursor += value;
        return `${color} ${start * 3.6}deg ${cursor * 3.6}deg`;
    });

    if (cursor < 100) {
        stops.push(`var(--border, #e5e7eb) ${cursor * 3.6}deg 360deg`);
    }

    donut.style.setProperty("--donut-gradient", stops.join(", "));

    document.querySelectorAll("[data-dot]").forEach((dot) => {
        const i = Number(dot.dataset.dot);
        if (!Number.isInteger(i)) return;
        dot.style.background = DONUT_PALETTE[i % DONUT_PALETTE.length];
    });
}

export function initAdminDashboard() {
    try {
        initCategoryDonut();
    } catch (err) {
        console.error("카테고리 분포 렌더링 실패:", err);
    }
}