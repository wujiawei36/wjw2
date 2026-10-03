// 密码强度检测：核心打分逻辑（页面与工具站共用）+ 工具站渲染。
// 打分规则与 utils/password_strength.py 严格一致，前后端结果对齐。
//
// 对外暴露：
//   window.passwordStrengthScore(password, username) -> {score, level, label, color, ...}
//   window.renderStrengthBar(container, result)      -> 渲染强度条
//   window.__tool                                     -> 工具站渲染入口（detail.js 调用）

(function (global) {
  'use strict';

  var COMMON = [
    '123456', 'password', '12345678', 'qwerty', 'abc123', '123456789',
    '111111', '1234567', 'password1', '1234567890', '123123', '000000',
    'iloveyou', '1234', '1q2w3e4r', 'qwertyuiop', '12345678900', '666666',
    '888888', 'abc123456', 'letmein', 'welcome', 'monkey', 'dragon',
    'master', 'login', 'admin', 'passw0rd', 'aa123456', '123456789a',
    '654321', '123321', '11111111', '112233', 'qwerty123', '1qaz2wsx',
    'sunshine', 'princess', 'football', 'baseball', 'superman'
  ];

  var LEVELS = [
    { label: '很弱', color: '#e74c3c' },
    { label: '弱', color: '#e67e22' },
    { label: '中', color: '#f1c40f' },
    { label: '强', color: '#2ecc71' },
    { label: '很强', color: '#27ae60' }
  ];

  function hasSequence(s) {
    var inc = 1, dec = 1;
    for (var i = 1; i < s.length; i++) {
      var d = s.charCodeAt(i) - s.charCodeAt(i - 1);
      if (d === 1) { inc++; dec = 1; }
      else if (d === -1) { dec++; inc = 1; }
      else { inc = 1; dec = 1; }
      if (inc >= 3 || dec >= 3) return true;
    }
    return false;
  }

  function hasRepeat(s) {
    var run = 1;
    for (var i = 1; i < s.length; i++) {
      if (s[i] === s[i - 1]) run++;
      else run = 1;
      if (run >= 3) return true;
    }
    return false;
  }

  function levelOf(score) {
    if (score < 20) return 0;
    if (score < 40) return 1;
    if (score < 60) return 2;
    if (score < 80) return 3;
    return 4;
  }

  function scorePassword(password, username) {
    var pw = String(password == null ? '' : password);
    var isCommon = COMMON.indexOf(pw.toLowerCase()) !== -1;
    var hasLower = /[a-z]/.test(pw);
    var hasUpper = /[A-Z]/.test(pw);
    var hasDigit = /[0-9]/.test(pw);
    var hasSymbol = /[^a-zA-Z0-9]/.test(pw);

    var score = 0;
    if (!isCommon) {
      score += Math.min(pw.length, 20) * 3;
      if (hasLower) score += 8;
      if (hasUpper) score += 8;
      if (hasDigit) score += 8;
      if (hasSymbol) score += 12;
      var classes = (hasLower ? 1 : 0) + (hasUpper ? 1 : 0) + (hasDigit ? 1 : 0) + (hasSymbol ? 1 : 0);
      if (classes <= 1) score -= 10;
      if (hasSequence(pw)) score -= 10;
      if (hasRepeat(pw)) score -= 8;
      if (typeof username === 'string' && username.length >= 3) {
        var u = username.toLowerCase();
        var p = pw.toLowerCase();
        if (p === u) score -= 20;
        else if (p.indexOf(u) !== -1) score -= 15;
      }
      if (score < 0) score = 0;
      if (score > 100) score = 100;
    }

    var level = levelOf(score);
    return {
      score: score,
      level: level,
      label: LEVELS[level].label,
      color: LEVELS[level].color,
      length: pw.length,
      has_lower: hasLower,
      has_upper: hasUpper,
      has_digit: hasDigit,
      has_symbol: hasSymbol,
      is_common: isCommon
    };
  }

  function renderStrengthBar(container, r) {
    container.innerHTML = '';
    container.style.marginTop = '8px';

    var barWrap = document.createElement('div');
    barWrap.style.height = '8px';
    barWrap.style.background = '#e9ecef';
    barWrap.style.borderRadius = '4px';
    barWrap.style.overflow = 'hidden';
    barWrap.style.maxWidth = '320px';
    var fill = document.createElement('div');
    fill.style.height = '100%';
    fill.style.width = Math.max(4, r.score) + '%';
    fill.style.background = r.color;
    fill.style.transition = 'width .2s, background-color .2s';
    barWrap.appendChild(fill);
    container.appendChild(barWrap);

    var text = document.createElement('div');
    text.style.marginTop = '4px';
    text.style.color = r.color;
    text.style.fontSize = '14px';
    text.textContent = r.label + '（' + r.score + ' 分）';
    container.appendChild(text);

    if (r.is_common) {
      var warn = document.createElement('div');
      warn.style.marginTop = '2px';
      warn.style.color = '#c0392b';
      warn.style.fontSize = '12px';
      warn.textContent = '命中常见弱密码，极易被暴力破解';
      container.appendChild(warn);
    }
    return container;
  }

  global.passwordStrengthScore = scorePassword;
  global.passwordStrengthLevels = LEVELS;
  global.renderStrengthBar = renderStrengthBar;

  // 工具站渲染入口（detail.js 检测到 window.__tool.render 即调用）
  global.__tool = {
    render: function () {
      var section = document.createElement('section');
      section.className = 'tool-panel';

      function label(text) {
        var l = document.createElement('div');
        l.className = 'tool-output-label';
        l.textContent = text;
        return l;
      }

      section.appendChild(label('密码'));
      var pwInput = document.createElement('input');
      pwInput.type = 'text';
      pwInput.className = 'tool-input';
      pwInput.placeholder = '输入要检测的密码…';
      section.appendChild(pwInput);

      section.appendChild(label('用户名（可选，用于相似度检测）'));
      var userInput = document.createElement('input');
      userInput.type = 'text';
      userInput.className = 'tool-input';
      userInput.placeholder = '可选：检测密码是否包含该用户名';
      section.appendChild(userInput);

      var bar = document.createElement('div');
      section.appendChild(bar);

      function update() {
        renderStrengthBar(bar, scorePassword(pwInput.value, userInput.value));
      }
      pwInput.addEventListener('input', update);
      userInput.addEventListener('input', update);
      update();

      return section;
    }
  };
})(window);
