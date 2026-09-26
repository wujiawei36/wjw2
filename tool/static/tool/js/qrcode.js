(function () {
  function buildQrcode() {
    var wrap = document.createElement('section');
    wrap.className = 'tool-panel';

    var input = document.createElement('textarea');
    input.className = 'tool-input';
    input.rows = 4;
    input.placeholder = '输入要编码的文本或网址…';
    wrap.appendChild(input);

    var btn = document.createElement('button');
    btn.className = 'tool-run';
    btn.textContent = '生成二维码';
    wrap.appendChild(btn);

    var status = document.createElement('p');
    status.className = 'p-text';
    wrap.appendChild(status);

    var img = document.createElement('img');
    img.alt = '二维码';
    img.style.display = 'none';
    img.style.maxWidth = '280px';
    img.style.marginTop = '12px';
    wrap.appendChild(img);

    var dl = document.createElement('a');
    dl.className = 'a-text';
    dl.textContent = '下载 PNG';
    dl.style.display = 'none';
    dl.style.marginTop = '8px';
    wrap.appendChild(dl);

    btn.addEventListener('click', function () {
      var text = input.value;
      if (!text.trim()) {
        status.textContent = '请输入内容';
        img.style.display = 'none';
        dl.style.display = 'none';
        return;
      }
      btn.disabled = true;
      status.textContent = '生成中…';
      img.style.display = 'none';
      dl.style.display = 'none';
      fetch('/tools/api/qrcode/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ input: text })
      }).then(function (resp) {
        return resp.json().then(function (data) { return { status: resp.status, data: data }; });
      }).then(function (r) {
        btn.disabled = false;
        if (r.data.ok) {
          status.textContent = '';
          img.src = r.data.data.png;
          img.style.display = 'block';
          dl.href = r.data.data.png;
          dl.download = 'qrcode.png';
          dl.style.display = 'inline-block';
        } else if (r.status === 429) {
          status.textContent = '请求过于频繁，请稍后再试';
        } else {
          status.textContent = r.data.error + (r.data.detail ? ': ' + r.data.detail : '');
        }
      }).catch(function (e) {
        btn.disabled = false;
        status.textContent = '错误：' + (e.message || String(e));
      });
    });

    return wrap;
  }

  window.__tool = { render: buildQrcode };
})();
