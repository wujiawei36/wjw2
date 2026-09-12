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

  // 后端工具：无前端交互（浏览器无法直算，如服务器时间/访客 IP/MD5），
  // API 调用示例由服务端模板直接渲染，无需在此挂载面板
  if (kind === 'backend') {
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
