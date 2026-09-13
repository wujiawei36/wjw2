window.__tool = {
  run: function (input) {
    var s = input.trim();
    var n;
    if (s === '') {
      n = 1;
    } else {
      if (!/^\d+$/.test(s)) return '请输入整数（1~1000）';
      n = parseInt(s, 10);
      if (n < 1 || n > 1000) return '数量需在 1~1000 之间';
    }
    var out = [];
    for (var i = 0; i < n; i++) {
      out.push(crypto.randomUUID());
    }
    return out.join('\n');
  }
};
