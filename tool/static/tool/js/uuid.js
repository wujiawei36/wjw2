window.__tool = {
  run: function (input) {
    var n = parseInt(input.trim(), 10);
    if (isNaN(n) || n < 1) n = 1;
    if (n > 1000) n = 1000;
    var out = [];
    for (var i = 0; i < n; i++) {
      out.push(crypto.randomUUID());
    }
    return out.join('\n');
  }
};
