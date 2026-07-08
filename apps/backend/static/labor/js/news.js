import { escapeHtml, markdownToHtml } from "./utils.js?v=3";

function renderNews(item) {
    return `<article class="news-card"><a href="${escapeHtml(item.link)}" target="_blank" rel="noopener"><header><time>${escapeHtml(item.date)}</time></header><h2>${escapeHtml(item.title)}</h2><p>${escapeHtml(item.summary)}</p></a></article>`;
}

export function initNews() {
    const newsSection = document.querySelector("[data-news-api]");
    if (!newsSection) return;

    const form = document.querySelector("#newsForm");
    const query = document.querySelector("#newsQuery");
    const list = document.querySelector("#newsList");
    const summary = document.querySelector("#newsSummary");

    // 서버 렌더링 시 삽입된 마크다운 원문(요약)을 HTML로 변환
    if (summary?.textContent.trim()) {
        summary.innerHTML = markdownToHtml(summary.textContent);
    }

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
                summary.innerHTML = items.length ? markdownToHtml(data.summary || "") : "관련 뉴스를 찾지 못했습니다";
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