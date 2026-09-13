(function () {
  function pad(n) { return n < 10 ? '0' + n : String(n); }

  function buildClock() {
    var wrap = document.createElement('div');
    wrap.style.display = 'flex';
    wrap.style.flexDirection = 'column';
    wrap.style.alignItems = 'center';
    wrap.style.justifyContent = 'center';
    wrap.style.minHeight = 'calc(100vh - 140px)';
    wrap.style.textAlign = 'center';

    var time = document.createElement('div');
    time.style.fontSize = 'min(16vw, 36vh)';
    time.style.fontWeight = '700';
    time.style.fontFamily = '"SF Mono", Menlo, Consolas, "Courier New", monospace';
    time.style.fontVariantNumeric = 'tabular-nums';
    time.style.letterSpacing = '0.04em';
    time.style.lineHeight = '1';
    time.style.color = '#000';

    var date = document.createElement('div');
    date.style.fontSize = 'min(4.5vw, 9vh)';
    date.style.color = '#000000b0';
    date.style.marginTop = '2vh';
    date.style.fontFamily = '"SF Mono", Menlo, Consolas, monospace';
    date.style.fontVariantNumeric = 'tabular-nums';

    var week = document.createElement('div');
    week.style.fontSize = 'min(3.5vw, 7vh)';
    week.style.color = '#00000090';
    week.style.marginTop = '1vh';

    wrap.appendChild(time);
    wrap.appendChild(date);
    wrap.appendChild(week);

    var weekNames = ['日', '一', '二', '三', '四', '五', '六'];
    function tick() {
      var now = new Date();
      time.textContent = pad(now.getHours()) + ':' + pad(now.getMinutes()) + ':' + pad(now.getSeconds());
      date.textContent = now.getFullYear() + '-' + pad(now.getMonth() + 1) + '-' + pad(now.getDate());
      week.textContent = '星期' + weekNames[now.getDay()];
    }
    tick();
    setInterval(tick, 1000);

    return wrap;
  }

  window.__tool = { render: buildClock };
})();
