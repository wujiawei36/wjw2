window.__tool = {
  run: function (input) {
    var len = parseInt(input.trim(), 10);
    if (isNaN(len) || len < 4) len = 16;
    if (len > 256) len = 256;
    var upper = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
    var lower = 'abcdefghijklmnopqrstuvwxyz';
    var digit = '0123456789';
    var symbol = '!@#$%^&*()-_=+[]{};:,.<>?';
    var all = upper + lower + digit + symbol;
    var arr = new Uint32Array(len);
    crypto.getRandomValues(arr);
    var chars = [];
    chars.push(upper[arr[0] % upper.length]);
    chars.push(lower[arr[1] % lower.length]);
    chars.push(digit[arr[2] % digit.length]);
    chars.push(symbol[arr[3] % symbol.length]);
    for (var i = 4; i < len; i++) {
      chars.push(all[arr[i] % all.length]);
    }
    for (var j = chars.length - 1; j > 0; j--) {
      var k = arr[j] % (j + 1);
      var tmp = chars[j]; chars[j] = chars[k]; chars[k] = tmp;
    }
    return chars.join('');
  }
};
