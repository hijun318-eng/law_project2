(function () {
    'use strict';

    const greeting = document.getElementById('greeting');
    const counterEl = document.getElementById('counterDisplay');
    const btn = document.getElementById('clickBtn');
    let count = 0;

    const hour = new Date().getHours();
    let msg;
    if (hour < 12) {
        msg = '좋은 아침입니다!';
    } else if (hour < 18) {
        msg = '좋은 오후입니다!';
    } else {
        msg = '좋은 저녁입니다!';
    }
    greeting.textContent = msg + ' Django 백엔드에 오신 것을 환영합니다.';

    btn.addEventListener('click', function () {
        count += 1;
        counterEl.textContent = '클릭 횟수: ' + count;
    });

    console.log('[Django Example] 페이지 로드 완료');
})();
