function getCookie(name) {
    const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
    return match ? decodeURIComponent(match[1]) : "";
}

export const csrf = () => getCookie("csrftoken");

export const postJson = (url, payload) => fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRFToken": csrf() },
    body: JSON.stringify(payload),
}).then((response) => response.json());

// LLM-006: AI가 생성하는 모든 응답(상담/계산/뉴스)에 공통으로 붙이는 법률 자문 고지 문구
export const LEGAL_DISCLAIMER_HTML = `<p class="answer-disclaimer">※ 이 답변은 AI가 제공하는 참고 정보이며 법적 효력이 있는 자문이 아닙니다. 구체적인 사안은 노무사·변호사 등 전문가와 상담하세요.</p>`;

export function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, (char) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;",
    }[char]));
}

export function markdownToHtml(text) {
    let html = escapeHtml(text);
    // 연속된 빈 줄(2개 이상의 개행)을 하나로 축소해 문단/주제 사이 공백을 줄임
    html = html.replace(/\n{2,}/g, '\n');
    // 코드 블록 (```lang\n...```)
    html = html.replace(/```(\w*)\s*([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
    // 인라인 코드 (`code`)
    html = html.replace(/`([^`\n]+)`/g, '<code>$1</code>');
    // 볼드 (**text**)
    html = html.replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>');
    // 이탤릭 (*text*)
    html = html.replace(/\*([^*\n]+)\*/g, '<em>$1</em>');
    // 링크 ([text](url))
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
    // 리스트 아이템 (- item)
    html = html.replace(/^[\s]*[-*] (.+)$/gm, '<li>$1</li>');
    // 인용문 (> text)
    html = html.replace(/^&gt;\s(.+)$/gm, '<blockquote>$1</blockquote>');
    // 제목 (###, ##)
    html = html.replace(/^### (.+)$/gm, '<h4>$1</h4>');
    html = html.replace(/^## (.+)$/gm, '<h3>$1</h3>');
    // 연속된 <li>를 <ul>로 감싸고, 항목 사이 개행은 제거해 리스트 간격을 줄임
    html = html.replace(/(?:<li>.*?<\/li>\n?)+/g, (block) => `<ul>${block.replace(/\n/g, '')}</ul>`);
    // 연속된 <blockquote>를 그룹화
    html = html.replace(/((?:<blockquote>.*?<\/blockquote>(?:\s*<br>)?\s*)+)/g, '$1');
    // 제목 바로 다음 개행 제거 (제목 자체 여백으로 충분)
    html = html.replace(/(<\/h[34]>)\n/g, '$1');
    // 줄바꿈을 <br>로 변환 (pre 태그 내부는 제외)
    html = html.replace(/\n/g, '<br>');
    return html;
}

export function appendMessage(container, role, html, withActions, rawHtml, messageId) {
    const node = document.createElement("div");
    node.className = `message ${role}`;
    node.innerHTML = rawHtml ? html : markdownToHtml(html);
    if (withActions && messageId) {
        node.innerHTML += `<div class="message-actions"><button type="button" data-action="feedback_like" data-mid="${messageId}">도움됐어요</button><button type="button" data-action="feedback_dislike" data-mid="${messageId}">아쉬워요</button><button type="button" data-action="open-drawer" data-mid="${messageId}">법령 원문</button></div>`;
    }
    container.appendChild(node);
    container.scrollTop = container.scrollHeight;
}