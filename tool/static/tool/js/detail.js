(function () {
  var slug = window.__TOOL_SLUG;
  var kind = window.__TOOL_KIND;
  var input = document.getElementById('tool-input');
  var output = document.getElementById('tool-output');
  var runBtn = document.getElementById('tool-run');

  function showError(msg) {
    output.value = '错误：' + msg;
  }

  function renderResult(d) {
    if (typeof d === 'string') return d;
    if (d && d.text !== undefined) return d.text;
    if (d && d.md5 !== undefined) return d.md5;
    return JSON.stringify(d, null, 2);
  }

  runBtn.addEventListener('click', function () {
    if (kind === 'frontend') {
      if (!window.__tool || typeof window.__tool.run !== 'function') {
        showError('工具脚本未加载');
        return;
      }
      try {
        var result = window.__tool.run(input.value);
        if (result && typeof result.then === 'function') {
          result.then(function (v) { output.value = v; },
                      function (e) { showError(e.message || String(e)); });
        } else {
          output.value = result;
        }
      } catch (e) {
        showError(e.message || String(e));
      }
      return;
    }

    var apiKey = document.getElementById('api-key').value.trim();
    fetch('/tools/api/' + slug + '/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': apiKey
      },
      body: JSON.stringify({ input: input.value })
    }).then(function (resp) {
      return resp.json().then(function (data) {
        return { status: resp.status, data: data };
      });
    }).then(function (r) {
      if (r.data.ok) {
        output.value = renderResult(r.data.data);
      } else {
        showError(r.data.error || ('HTTP ' + r.status));
      }
    }).catch(function (e) {
      showError('请求失败：' + (e.message || e));
    });
  });
})();
