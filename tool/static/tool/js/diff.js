(function () {
  function buildDiff() {
    var wrap = document.createElement('section');
    wrap.className = 'tool-panel';

    var lab1 = document.createElement('div');
    lab1.className = 'tool-output-label';
    lab1.textContent = '原文';
    wrap.appendChild(lab1);
    var input1 = document.createElement('textarea');
    input1.className = 'tool-input';
    input1.rows = 6;
    input1.placeholder = '第一段文本…';
    wrap.appendChild(input1);

    var lab2 = document.createElement('div');
    lab2.className = 'tool-output-label';
    lab2.textContent = '对比';
    wrap.appendChild(lab2);
    var input2 = document.createElement('textarea');
    input2.className = 'tool-input';
    input2.rows = 6;
    input2.placeholder = '第二段文本…';
    wrap.appendChild(input2);

    var btn = document.createElement('button');
    btn.className = 'tool-run';
    btn.textContent = '对比';
    wrap.appendChild(btn);

    var out = document.createElement('textarea');
    out.className = 'tool-output';
    out.rows = 12;
    out.readOnly = true;
    out.placeholder = '差异结果…';
    wrap.appendChild(out);

    btn.addEventListener('click', function () {
      btn.disabled = true;
      out.value = '对比中…';
      fetch('/tools/api/diff/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ input: input1.value, compare: input2.value })
      }).then(function (resp) {
        return resp.json().then(function (data) { return { status: resp.status, data: data }; });
      }).then(function (r) {
        btn.disabled = false;
        if (r.data.ok) {
          out.value = r.data.data.diff || '（两段文本相同）';
        } else if (r.status === 429) {
          out.value = '请求过于频繁，请稍后再试';
        } else {
          out.value = r.data.error + (r.data.detail ? ': ' + r.data.detail : '');
        }
      }).catch(function (e) {
        btn.disabled = false;
        out.value = '错误：' + (e.message || String(e));
      });
    });

    return wrap;
  }

  window.__tool = { render: buildDiff };
})();
