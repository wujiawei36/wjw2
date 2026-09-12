window.__tool = {
  panels: [
    {
      id: 'to-date',
      title: '时间戳 → 日期时间',
      placeholder: '输入时间戳（秒或毫秒）…',
      button: '转换',
      run: function (input) {
        var s = input.trim();
        if (!s) return '（空输入）';
        if (!/^-?\d+$/.test(s)) return '请输入纯数字时间戳';
        var n = parseInt(s, 10);
        var ms = (Math.abs(n) < 100000000000) ? n * 1000 : n;
        var d = new Date(ms);
        if (isNaN(d.getTime())) return '无效时间戳';
        return '本地: ' + d.toLocaleString('zh-CN', { hour12: false }) +
               '\nUTC: ' + d.toISOString();
      }
    },
    {
      id: 'to-ts',
      title: '日期时间 → 时间戳',
      placeholder: '输入日期（如 2026-09-12 18:00:00）…',
      button: '转换',
      run: function (input) {
        var s = input.trim();
        if (!s) return '（空输入）';
        var d = new Date(s);
        if (isNaN(d.getTime())) return '无效日期（请用 YYYY-MM-DD HH:mm:ss 或 ISO 格式）';
        return '秒: ' + Math.floor(d.getTime() / 1000) +
               '\n毫秒: ' + d.getTime();
      }
    }
  ]
};
