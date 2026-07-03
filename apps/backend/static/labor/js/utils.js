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

export function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, (char) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;",
    }[char]));
}

export function appendMessage(container, role, html, withActions, rawHtml, messageId) {
    const node = document.createElement("div");
    node.className = `message ${role}`;
    node.innerHTML = rawHtml ? html : escapeHtml(html);
    if (withActions && messageId) {
        node.innerHTML += `<div class="message-actions"><button type="button" data-action="feedback_like" data-mid="${messageId}">도움됐어요</button><button type="button" data-action="feedback_dislike" data-mid="${messageId}">아쉬워요</button><button type="button" data-action="open-drawer" data-mid="${messageId}">법령 원문</button></div>`;
    }
    container.appendChild(node);
    container.scrollTop = container.scrollHeight;
}