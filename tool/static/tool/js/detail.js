(function () {
  var slug = window.__TOOL_SLUG;
  var kind = window.__TOOL_KIND;
  var container = document.getElementById('tool-container');

  function renderResult(d) {
    if (typeof d === 'string') return d;
    if (d && d.text !== undefined) return d.text;
    if (d && d.md5 !== undefined) return d.md5;
    return JSON.stringify(d, null, 2);
  }

  // 渲染一个面板：{ id, title, placeholder, button, outputs, run }
  function makePanel(panel) {
    var section = document.createElement('section');
    section.className = 'tool-panel';

    if (panel.title) {
      var h = document.createElement('h3');
      h.className = 'h3-text';
      h.textContent = panel.title;
      section.appendChild(h);
    }

    var input = document.createElement('textarea');
    input.className = 'tool-input';
    input.rows = 6;
    input.placeholder = panel.placeholder || '输入内容…';
    section.appendChild(input);

    var btn = document.createElement('button');
    btn.className = 'tool-run';
    btn.textContent = panel.button || '执行';
    section.appendChild(btn);

    var outputs = panel.outputs && panel.outputs.length
      ? panel.outputs
      : [{ key: null, label: null, placeholder: '结果…' }];
    var outputEls = [];
    outputs.forEach(function (o) {
      if (o.label) {
        var lab = document.createElement('div');
        lab.className = 'tool-output-label';
        lab.textContent = o.label;
        section.appendChild(lab);
      }
      var ta = document.createElement('textarea');
      ta.className = 'tool-output';
      ta.rows = o.rows || 4;
      ta.readOnly = true;
      ta.placeholder = o.placeholder || '结果…';
      section.appendChild(ta);
      outputEls.push({ key: o.key, el: ta });
    });

    function writeResult(result) {
      if (result && typeof result === 'object' && !Array.isArray(result)) {
        var anyMatched = false;
        outputEls.forEach(function (o) {
          if (o.key && result[o.key] !== undefined) {
            o.el.value = result[o.key];
            anyMatched = true;
          }
        });
        if (!anyMatched) {
          outputEls[0].el.value = renderResult(result);
        }
      } else {
        outputEls[0].el.value = renderResult(result);
      }
    }

    btn.addEventListener('click', function () {
      var result;
      try {
        result = panel.run(input.value);
      } catch (e) {
        outputEls[0].el.value = '错误：' + (e.message || String(e));
        return;
      }
      if (result && typeof result.then === 'function') {
        result.then(writeResult, function (e) {
          outputEls[0].el.value = '错误：' + (e.message || String(e));
        });
      } else {
        writeResult(result);
      }
    });

    return section;
  }

  // 免 Key「获取」面板（服务器侧信息工具）：POST 到 /tools/api/<slug>/（无 Key），后端按 IP 限频
  function makeFetchPanel(slug) {
    var section = document.createElement('section');
    section.className = 'tool-panel';

    var btn = document.createElement('button');
    btn.className = 'tool-run';
    btn.textContent = '获取';
    section.appendChild(btn);

    var ta = document.createElement('textarea');
    ta.className = 'tool-output';
    ta.rows = 6;
    ta.readOnly = true;
    ta.placeholder = '结果…';
    section.appendChild(ta);

    function format(data) {
      if (slug === 'servertime') {
        return 'UTC: ' + data.utc + '\n' +
               '本地: ' + data.local + ' (' + data.timezone + ')\n' +
               'Unix 时间戳(秒): ' + data.unix;
      }
      if (slug === 'ipinfo') {
        return 'IP: ' + data.ip + '\n' +
               'User-Agent: ' + data.user_agent;
      }
      return JSON.stringify(data, null, 2);
    }

    btn.addEventListener('click', function () {
      btn.disabled = true;
      ta.value = '获取中…';
      fetch('/tools/api/' + slug + '/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: '{}'
      }).then(function (resp) {
        return resp.json().then(function (data) {
          return { status: resp.status, data: data };
        });
      }).then(function (r) {
        btn.disabled = false;
        if (r.data.ok) {
          ta.value = format(r.data.data);
        } else if (r.status === 429) {
          ta.value = '请求过于频繁，请稍后再试';
        } else {
          ta.value = r.data.error + (r.data.detail ? ': ' + r.data.detail : '');
        }
      }).catch(function (e) {
        btn.disabled = false;
        ta.value = '错误：' + (e.message || String(e));
      });
    });

    return section;
  }

  // 后端工具：浏览器无法直算（服务器时间/真实 IP 等）
  // 若允许匿名（allow_anonymous），渲染「获取」按钮（免 Key，后端按 IP 限频）
  if (kind === 'backend') {
    if (window.__TOOL_ANON) {
      container.appendChild(makeFetchPanel(slug));
    }
    return;
  }

  // 前端工具：声明式多面板，或默认单面板（run）
  var tool = window.__tool;
  if (tool && tool.panels) {
    tool.panels.forEach(function (p) {
      container.appendChild(makePanel(p));
    });
  } else if (tool && typeof tool.run === 'function') {
    container.appendChild(makePanel({
      id: slug,
      placeholder: '输入内容…',
      run: tool.run
    }));
  } else {
    container.textContent = '工具脚本未加载';
  }
})();
