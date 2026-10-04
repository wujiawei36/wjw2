// 密码强度检测：核心打分逻辑（页面与工具站共用）+ 工具站渲染。
// 基于「熵估算」的科学模型，与 utils/password_strength.py 严格一致，前后端结果对齐。
//
// 对外暴露：
//   window.passwordStrengthScore(password, username) -> {score, level, label, color, ...}
//   window.renderStrengthBar(container, result)      -> 渲染强度条
//   window.__tool                                     -> 工具站渲染入口（detail.js 调用）

(function (global) {
  'use strict';

  // ---- 常见弱密码黑名单（命中即 0 熵）----
  var COMMON = [
    '123456', 'password', '12345678', 'qwerty', 'abc123', '123456789',
    '111111', '1234567', 'password1', '1234567890', '123123', '000000',
    'iloveyou', '1234', '1q2w3e4r', 'qwertyuiop', '12345678900', '666666',
    '888888', 'abc123456', 'letmein', 'welcome', 'monkey', 'dragon',
    'master', 'login', 'admin', 'passw0rd', 'aa123456', '123456789a',
    '654321', '123321', '11111111', '112233', 'qwerty123', '1qaz2wsx',
    'sunshine', 'princess', 'football', 'baseball', 'superman'
  ];

  // ---- 词典（小写）：英文常见词 + 中文常见词 + 项目相关词 ----
  var DICTIONARY = [
    'password', 'welcome', 'admin', 'administrator', 'login', 'letmein',
    'monkey', 'dragon', 'master', 'sunshine', 'princess', 'football',
    'baseball', 'superman', 'iloveyou', 'hello', 'google', 'facebook',
    'twitter', 'instagram', 'computer', 'internet', 'secret', 'this',
    'not', 'safe', 'that', 'what', 'world', 'test', 'demo', 'user',
    'guest', 'root', 'system', 'pass', 'pwd',
    '密码', '管理员', '测试', '验证', '安全', '我爱你', '你好', '用户名',
    '登录', '注册', '修改', '长度', '字符', '数字', '符号', '连续',
    '重复', '序列', '弱密码', '黑名单', '相似度', '评级', '提示',
    '校验', '策略', '评估', '强度', '错误',
    'wujiawei', 'pythonanywhere', 'python', 'django', 'curl', 'https',
    'http', 'www', 'com', 'missing_key', 'invalid_key', 'key_disabled',
    'key_expired', 'quota_exceeded', 'slug_not_allowed', 'rate_limited',
    'bad_param', 'unsupported_slug', 'apikey', 'token', 'jwt'
  ];

  // ---- l33t 替换映射 ----
  var LEET_MAP = {
    '0': 'o', '1': 'l', '3': 'e', '4': 'a', '5': 's', '7': 't',
    '8': 'b', '@': 'a', '$': 's', '!': 'i', '+': 't'
  };

  // ---- 键盘行（含逆序）----
  var KEYBOARD_ROWS = [
    'qwertyuiop', 'asdfghjkl', 'zxcvbnm',
    'poiuytrewq', 'lkjhgfdsa', 'mnbvcxz'
  ];

  // ---- 明确分隔符（低熵）----
  var SEPARATORS = ' /_.-:;,\\|';

  var LEVELS = [
    { label: '很弱', color: '#e74c3c' },
    { label: '弱', color: '#e67e22' },
    { label: '中', color: '#f1c40f' },
    { label: '强', color: '#2ecc71' },
    { label: '很强', color: '#27ae60' }
  ];

  var SORTED_WORDS = DICTIONARY.slice().sort(function (a, b) {
    return b.length - a.length;
  });
  var WORD_BITS = Math.log2(DICTIONARY.length);

  function unleet(s) {
    var out = '';
    for (var i = 0; i < s.length; i++) {
      var c = s[i];
      out += LEET_MAP[c] || c;
    }
    return out;
  }

  function sequenceLen(s, i) {
    if (i + 1 >= s.length) return 1;
    var inc = 1, dec = 1;
    var j = i + 1;
    while (j < s.length) {
      var d = s.charCodeAt(j) - s.charCodeAt(j - 1);
      if (d === 1 && dec === 1) inc++;
      else if (d === -1 && inc === 1) dec++;
      else break;
      j++;
    }
    return Math.max(inc, dec);
  }

  function keyboardLen(s, i) {
    var best = 0;
    for (var r = 0; r < KEYBOARD_ROWS.length; r++) {
      var row = KEYBOARD_ROWS[r];
      var pos = row.indexOf(s[i]);
      if (pos === -1) continue;
      var j = i, k = pos;
      while (j < s.length && k < row.length && s[j] === row[k]) { j++; k++; }
      if (j - i > best) best = j - i;
    }
    return best;
  }

  function matchWordLen(lower, unleeted, i) {
    var best = 0;
    for (var t = 0; t < 2; t++) {
      var text = t === 0 ? lower : unleeted;
      for (var w = 0; w < SORTED_WORDS.length; w++) {
        var word = SORTED_WORDS[w];
        if (word.length <= best) break;
        if (text.indexOf(word, i) === i) { best = word.length; break; }
      }
    }
    return best;
  }

  function estimateBits(pw) {
    var n = pw.length;
    if (n === 0) return 0;

    var lower = pw.toLowerCase();
    var unleeted = unleet(lower);

    if (COMMON.indexOf(lower) !== -1 || COMMON.indexOf(unleeted) !== -1) {
      return 0;
    }

    var hasLower = /[a-z]/.test(pw);
    var hasUpper = /[A-Z]/.test(pw);
    var hasDigit = /[0-9]/.test(pw);
    var hasSymbol = /[^a-zA-Z0-9]/.test(pw);

    var pool = 0;
    if (hasLower) pool += 26;
    if (hasUpper) pool += 26;
    if (hasDigit) pool += 10;
    if (hasSymbol) pool += 33;
    var perChar = pool > 0 ? Math.log2(pool) : 0;

    var bits = 0;
    var i = 0;
    while (i < n) {
      // 1) 重复字符
      var run = 1;
      while (i + run < n && pw[i + run] === pw[i]) run++;
      if (run >= 3) {
        bits += pool > 0 ? (Math.log2(pool) + Math.log2(run)) : Math.log2(run);
        i += run;
        continue;
      }

      // 2) 键盘序列
      var kb = keyboardLen(lower, i);
      if (kb >= 4) { bits += kb * 1.0; i += kb; continue; }

      // 3) 连续序列
      var seq = sequenceLen(pw, i);
      if (seq >= 3) { bits += seq * 1.0; i += seq; continue; }

      // 4) 词典词
      var wl = matchWordLen(lower, unleeted, i);
      if (wl >= 2) { bits += WORD_BITS; i += wl; continue; }

      // 5) 单字符
      var code = pw.charCodeAt(i);
      if (code >= 0x4e00 && code <= 0x9fff) bits += 3.5;
      else if (SEPARATORS.indexOf(pw[i]) !== -1) bits += 1.5;
      else bits += perChar;
      i++;
    }
    return bits;
  }

  function interp(x, loB, hiB, loS, hiS) {
    if (hiB <= loB) return loS;
    var t = (x - loB) / (hiB - loB);
    var v = Math.round(loS + t * (hiS - loS));
    return Math.max(loS, Math.min(hiS, v));
  }

  function bitsToScoreLevel(bits) {
    // 分数上限封顶 99（而非 100）：刻意保留缺口，暗示「没有绝对安全的密码」
    if (bits < 28) return [interp(bits, 0, 28, 0, 19), 0];
    if (bits < 36) return [interp(bits, 28, 36, 20, 39), 1];
    if (bits < 60) return [interp(bits, 36, 60, 40, 59), 2];
    if (bits < 128) return [interp(bits, 60, 128, 60, 79), 3];
    return [interp(bits, 128, 256, 80, 99), 4];
  }

  function scorePassword(password, username) {
    var pw = String(password == null ? '' : password);
    var lower = pw.toLowerCase();
    var unleeted = unleet(lower);
    var isCommon = COMMON.indexOf(lower) !== -1 || COMMON.indexOf(unleeted) !== -1;
    var hasLower = /[a-z]/.test(pw);
    var hasUpper = /[A-Z]/.test(pw);
    var hasDigit = /[0-9]/.test(pw);
    var hasSymbol = /[^a-zA-Z0-9]/.test(pw);

    var bits = estimateBits(pw);

    if (typeof username === 'string' && username.length >= 3) {
      var u = username.toLowerCase();
      if (lower === u || unleeted === u) {
        bits = Math.min(bits, 0);
      } else if (lower.indexOf(u) !== -1 || unleeted.indexOf(u) !== -1) {
        bits = Math.min(bits, bits * 0.5);
      }
    }

    var sl = bitsToScoreLevel(bits);
    var score = sl[0], level = sl[1];
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
