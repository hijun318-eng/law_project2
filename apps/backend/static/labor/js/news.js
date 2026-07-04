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

    let requestToken = 0;

    const load = () => {
        const token = ++requestToken;
        const params = new URLSearchParams({ q: query.value.trim() });

        summary.textContent = "뉴스를 불러오는 중입니다...";
        list.innerHTML = "";

        fetch(`${newsSection.dataset.newsApi}?${params}`)
            .then((response) => {
                if (!response.ok) throw new Error(`요청 실패 (status ${response.status})`);
                return response.json();
            })
            .then((data) => {
                if (token !== requestToken) return;

                const items = Array.isArray(data.items) ? data.items : [];
                summary.textContent = items.length ? (data.summary || "") : "관련 뉴스를 찾지 못했습니다";
                list.innerHTML = items.length
                    ? items.map(renderNews).join("")
                    : `<div class="empty-state">관련 뉴스를 찾지 못했습니다</div>`;
            })
            .catch((err) => {
                if (token !== requestToken) return;
                console.error("뉴스 조회 실패:", err);
                summary.textContent = "";
                list.innerHTML = `<div class="empty-state">뉴스를 불러오지 못했습니다.</div>`;
            });
    };

    form?.addEventListener("submit", (event) => {
        event.preventDefault();
        load();
    });
}