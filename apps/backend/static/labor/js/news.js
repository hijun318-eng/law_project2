import { escapeHtml } from "./utils.js";

function renderNews(item) {
    return `<article class="news-card"><header><time>${escapeHtml(item.date)}</time></header><h2>${escapeHtml(item.title)}</h2><p>${escapeHtml(item.summary)}</p></article>`;
}

export function initNews() {
    const newsSection = document.querySelector("[data-news-api]");
    if (!newsSection) return;

    const form = document.querySelector("#newsForm");
    const query = document.querySelector("#newsQuery");
    const list = document.querySelector("#newsList");
    const summary = document.querySelector("#newsSummary");

    const load = () => {
        const params = new URLSearchParams({ q: query.value.trim() });
        fetch(`${newsSection.dataset.newsApi}?${params}`).then((response) => response.json()).then((data) => {
            summary.textContent = data.summary || "관련 뉴스를 찾지 못했습니다.";
            list.innerHTML = data.items.length ? data.items.map(renderNews).join("") : `<div class="empty-state">관련 뉴스를 찾지 못했습니다</div>`;
        });
    };

    form?.addEventListener("submit", (event) => { event.preventDefault(); load(); });
}