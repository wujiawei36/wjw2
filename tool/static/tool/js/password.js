window.__tool = {
  render: function () {
    var CHARSETS = [
      { v: 'all',         label: '字母 + 数字 + 符号' },
      { v: 'alnum',       label: '字母 + 数字（无符号）' },
      { v: 'lower_digit', label: '小写字母 + 数字' },
      { v: 'digits',      label: '纯数字' }
    ];
    var GROUPS = {
      'all': ['ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz',
              '0123456789', '!@#$%^&*()-_=+[]{};:,.<>?'],
      'alnum': ['ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz',
                '0123456789'],
      'lower_digit': ['abcdefghijklmnopqrstuvwxyz', '0123456789'],
      'digits': ['0123456789']
    };

    var section = document.createElement('section');
    section.className = 'tool-panel';

    function label(text) {
      var l = document.createElement('div');
      l.className = 'tool-output-label';
      l.textContent = text;
      return l;
    }
    function field(value, width) {
      var i = document.createElement('input');
      i.type = 'text';
      i.className = 'tool-input';
      i.style.maxWidth = width || '120px';
      i.value = value;
      return i;
    }

    section.appendChild(label('长度（4~256，默认 16）'));
    var lenInput = field('16');
    section.appendChild(lenInput);

    section.appendChild(label('数量（1~100，默认 1）'));
    var cntInput = field('1');
    section.appendChild(cntInput);

    section.appendChild(label('字符集'));
    var csSelect = document.createElement('select');
    csSelect.className = 'tool-input';
    csSelect.style.maxWidth = '280px';
    CHARSETS.forEach(function (c) {
      var o = document.createElement('option');
      o.value = c.v;
      o.textContent = c.label;
      csSelect.appendChild(o);
    });
    section.appendChild(csSelect);

    var btn = document.createElement('button');
    btn.className = 'tool-run';
    btn.textContent = '生成';
    section.appendChild(btn);

    var out = document.createElement('textarea');
    out.className = 'tool-output';
    out.rows = 8;
    out.readOnly = true;
    out.placeholder = '生成的密码…';
    section.appendChild(out);

    function genOne(len, cs) {
      var groups = GROUPS[cs];
      var pool = groups.join('');
      var arr = new Uint32Array(len);
      crypto.getRandomValues(arr);
      var chars = [];
      for (var gi = 0; gi < groups.length; gi++) {
        chars.push(groups[gi][arr[gi] % groups[gi].length]);
      }
      for (var i = groups.length; i < len; i++) {
        chars.push(pool[arr[i] % pool.length]);
      }
      for (var j = len - 1; j > 0; j--) {
        var k = arr[j] % (j + 1);
        var tmp = chars[j]; chars[j] = chars[k]; chars[k] = tmp;
      }
      return chars.join('');
    }

    btn.addEventListener('click', function () {
      var s = lenInput.value.trim();
      var len;
      if (s === '') {
        len = 16;
      } else {
        if (!/^\d+$/.test(s)) { out.value = '长度需为整数（4~256）'; return; }
        len = parseInt(s, 10);
        if (len < 4 || len > 256) { out.value = '长度需在 4~256 之间'; return; }
      }

      var cs = cntInput.value.trim();
      var cnt;
      if (cs === '') {
        cnt = 1;
      } else {
        if (!/^\d+$/.test(cs)) { out.value = '数量需为整数（1~100）'; return; }
        cnt = parseInt(cs, 10);
        if (cnt < 1 || cnt > 100) { out.value = '数量需在 1~100 之间'; return; }
      }

      var charset = csSelect.value;
      var results = [];
      for (var i = 0; i < cnt; i++) {
        results.push(genOne(len, charset));
      }
      out.value = results.join('\n');
    });

    return section;
  }
};
