window.__tool = {
  run: function (input) {
    var s = input.trim();
    if (!s) return '（空输入）';
    var n;
    if (/^0x[0-9a-f]+$/i.test(s)) n = parseInt(s, 16);
    else if (/^0b[01]+$/i.test(s)) n = parseInt(s.slice(2), 2);
    else if (/^0o[0-7]+$/i.test(s)) n = parseInt(s.slice(2), 8);
    else if (/^-?\d+$/.test(s)) n = parseInt(s, 10);
    else return '请输入十进制整数，或 0x/0b/0o 前缀的数';
    if (isNaN(n)) return '无效数字';
    return '十进制: ' + n +
      '\n十六进制: 0x' + n.toString(16).toUpperCase() +
      '\n八进制: 0o' + n.toString(8) +
      '\n二进制: 0b' + n.toString(2);
  }
};
