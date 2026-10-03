window.__tool = {
  run: function (input) {
    var s = input.trim();
    if (s === '') return '请输入一个整数（2 ~ 10^15）';
    if (!/^\d+$/.test(s)) return '请输入正整数（2 ~ 10^15）';
    if (s.length > 16) return '数字过大（上限 10^15），请缩小';
    var n = Number(s);
    if (n < 2) return '请输入大于 1 的整数';
    if (n > 1000000000000000) return '数字过大（上限 10^15），请缩小';

    // 试除法求最小因子（6k±1 优化，最坏 O(√n)，n≤10^15 时毫秒级）
    function smallestFactor(x) {
      if (x % 2 === 0) return 2;
      if (x % 3 === 0) return 3;
      for (var i = 5; i * i <= x; i += 6) {
        if (x % i === 0) return i;
        if (x % (i + 2) === 0) return i + 2;
      }
      return x;
    }

    var f = smallestFactor(n);
    if (f === n) return n + ' 是质数';
    return n + ' 不是质数（可被 ' + f + ' 整除）';
  }
};
