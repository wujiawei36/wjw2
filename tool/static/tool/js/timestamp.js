window.__tool = {
  run: function (input) {
    var s = input.trim();
    if (!s) return '（空输入）';
    if (/^-?\d+$/.test(s)) {
      var n = parseInt(s, 10);
      var ms = (Math.abs(n) < 100000000000) ? n * 1000 : n;
      var d = new Date(ms);
      if (isNaN(d.getTime())) return '无效时间戳';
      var local = d.toLocaleString('zh-CN', { hour12: false });
      return '本地时间: ' + local + '\nUTC: ' + d.toISOString();
    }
    var d2 = new Date(s);
    if (isNaN(d2.getTime())) return '无效日期字符串（请用 YYYY-MM-DD HH:mm:ss 或 ISO 格式）';
    return '秒: ' + Math.floor(d2.getTime() / 1000) + '\n毫秒: ' + d2.getTime();
  }
};
