export function initHeroSearch() {
    const form = document.querySelector("[data-hero-search]");
    if (!form) return;

    const input = form.querySelector("[data-question-input]");
    const error = document.querySelector("[data-question-error]");

    form.addEventListener("submit", (event) => {
        const value = input.value.trim();
        if (!value) {
            event.preventDefault();
            error.hidden = false;
            input.focus();
            return;
        }
        error.hidden = true;
    });

    input?.addEventListener("input", () => {
        if (!error.hidden && input.value.trim()) {
            error.hidden = true;
        }
    });
}

initHeroSearch();