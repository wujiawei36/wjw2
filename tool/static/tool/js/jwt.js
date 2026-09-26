(function () {
  // base64url → UTF-8 字符串
  function b64urlDecode(str) {
    str = str.replace(/-/g, '+').replace(/_/g, '/');
    while (str.length % 4) str += '=';
    var bin = atob(str);
    var bytes = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    return new TextDecoder('utf-8').decode(bytes);
  }

  function fmtTime(n) {
    if (typeof n !== 'number' || !isFinite(n)) return null;
    return new Date(n * 1000).toLocaleString('zh-CN', { hour12: false });
  }

  function buildJwt() {
    var wrap = document.createElement('section');
    wrap.className = 'tool-panel';

    var input = document.createElement('textarea');
    input.className = 'tool-input';
    input.rows = 4;
    input.placeholder = '粘贴完整 JWT（header.payload.signature）…';
    wrap.appendChild(input);

    var btn = document.createElement('button');
    btn.className = 'tool-run';
    btn.textContent = '解码';
    wrap.appendChild(btn);

    var status = document.createElement('p');
    status.className = 'p-text';
    status.style.fontSize = '14px';
    wrap.appendChild(status);

    function addOutput(label) {
      var lab = document.createElement('div');
      lab.className = 'tool-output-label';
      lab.textContent = label;
      wrap.appendChild(lab);
      var ta = document.createElement('textarea');
      ta.className = 'tool-output';
      ta.rows = 6;
      ta.readOnly = true;
      wrap.appendChild(ta);
      return ta;
    }

    var headerOut = addOutput('Header（解码后）');
    var payloadOut = addOutput('Payload（解码后）');
    var sigOut = addOutput('Signature（原文，未验签）');

    var timeBox = document.createElement('div');
    timeBox.style.marginTop = '12px';
    wrap.appendChild(timeBox);

    btn.addEventListener('click', function () {
      var raw = input.value.trim();
      headerOut.value = '';
      payloadOut.value = '';
      sigOut.value = '';
      timeBox.innerHTML = '';

      if (!raw) {
        status.textContent = '请输入 JWT';
        return;
      }
      var parts = raw.split('.');
      if (parts.length !== 3) {
        status.textContent = 'JWT 应为 header.payload.signature 三段式';
        return;
      }

      var headerObj, payloadObj;
      try {
        headerObj = JSON.parse(b64urlDecode(parts[0]));
      } catch (e) {
        status.textContent = 'Header 解码失败：' + (e.message || String(e));
        return;
      }
      try {
        payloadObj = JSON.parse(b64urlDecode(parts[1]));
      } catch (e) {
        status.textContent = 'Payload 解码失败：' + (e.message || String(e));
        return;
      }

      status.textContent = '';
      headerOut.value = JSON.stringify(headerObj, null, 2);
      payloadOut.value = JSON.stringify(payloadObj, null, 2);
      sigOut.value = parts[2];

      // 时间字段换算为可读时间并提示是否过期
      var nowSec = Math.floor(Date.now() / 1000);
      [['exp', '过期时间'], ['nbf', '生效时间'], ['iat', '签发时间']].forEach(function (pair) {
        var key = pair[0], label = pair[1];
        if (typeof payloadObj[key] === 'number') {
          var t = fmtTime(payloadObj[key]);
          if (!t) return;
          var extra = '';
          if (key === 'exp') {
            extra = nowSec > payloadObj[key] ? '（已过期）' : '（未过期）';
          } else if (key === 'nbf') {
            extra = nowSec < payloadObj[key] ? '（尚未生效）' : '（已生效）';
          }
          var p = document.createElement('p');
          p.className = 'p-text';
          p.style.fontSize = '14px';
          p.textContent = label + '：' + t + extra;
          timeBox.appendChild(p);
        }
      });
    });

    return wrap;
  }

  window.__tool = { render: buildJwt };
})();
