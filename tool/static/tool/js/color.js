window.__tool = {
  run: function (input) {
    var s = input.trim();
    if (!s) return '（空输入）';
    if (s.charAt(0) === '#') {
      var hex = s.slice(1);
      if (hex.length === 3) {
        hex = hex.split('').map(function (c) { return c + c; }).join('');
      }
      if (!/^[0-9a-fA-F]{6}$/.test(hex)) return '无效 HEX（请用 #RRGGBB 或 #RGB）';
      var r = parseInt(hex.slice(0, 2), 16);
      var g = parseInt(hex.slice(2, 4), 16);
      var b = parseInt(hex.slice(4, 6), 16);
      return 'RGB: rgb(' + r + ', ' + g + ', ' + b + ')';
    }
    var m = s.match(/rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*/i);
    if (m) {
      var toHex = function (n) {
        n = Math.max(0, Math.min(255, parseInt(n, 10)));
        return n.toString(16).padStart(2, '0');
      };
      return 'HEX: #' + (toHex(m[1]) + toHex(m[2]) + toHex(m[3])).toUpperCase();
    }
    return '请输入 #RRGGBB 或 rgb(r,g,b)';
  }
};
