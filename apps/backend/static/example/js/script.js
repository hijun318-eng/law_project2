(function () {
    'use strict';

    const greeting = document.getElementById('greeting');
    const counterEl = document.getElementById('counter');
    const btn = document.getElementById('clickBtn');
    let count = 0;

    const hour = new Date().getHours();
    if (hour < 12) {
        greeting.textContent = '좋은 아침입니다!';
    } else if (hour < 18) {
        greeting.textContent = '좋은 오후입니다!';
    } else {
        greeting.textContent = '좋은 저녁입니다!';
    }

    btn.addEventListener('click', function () {
        count += 1;
        counterEl.textContent = count;
    });

    console.log('Django Example — script loaded');
})();
