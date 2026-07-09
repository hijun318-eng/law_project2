import { escapeHtml, markdownToHtml, renderProgress, formatProgress, streamSSE } from "./utils.js?v=4";

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

    let requestToken = 0;

    const load = () => {
        const token = ++requestToken;
        const params = new URLSearchParams({ q: query.value.trim() });

        summary.innerHTML = renderProgress("뉴스 검색을 준비하고 있습니다...");
        const progressLabel = summary.querySelector(".progress-label");
        const progressTimer = summary.querySelector(".progress-timer");
        list.innerHTML = "";

        const startedAt = Date.now();
        const timerId = setInterval(() => {
            if (progressTimer) progressTimer.textContent = `${Math.floor((Date.now() - startedAt) / 1000)}초`;
        }, 1000);
        const stopTimer = () => clearInterval(timerId);

        streamSSE(`${newsSection.dataset.newsStreamApi}?${params}`, {
            onProgress: (data) => {
                if (token !== requestToken) return;
                if (progressLabel) progressLabel.textContent = formatProgress(data);
            },
            onDone: (data) => {
                if (token !== requestToken) return;
                stopTimer();
                const items = Array.isArray(data.items) ? data.items : [];
                summary.innerHTML = items.length ? markdownToHtml(data.summary || "") : "관련 뉴스를 찾지 못했습니다";
                list.innerHTML = items.length
                    ? items.map(renderNews).join("")
                    : `<div class="empty-state">관련 뉴스를 찾지 못했습니다</div>`;
            },
            onError: (err) => {
                if (token !== requestToken) return;
                stopTimer();
                console.error("뉴스 조회 실패:", err);
                summary.textContent = "";
                list.innerHTML = `<div class="empty-state">뉴스를 불러오지 못했습니다.</div>`;
            },
        });
    };

    form?.addEventListener("submit", (event) => {
        event.preventDefault();
        load();
    });
}
