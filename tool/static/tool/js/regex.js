window.__tool = {
  run: function (input) {
    if (!input.trim()) return '第一行输入正则表达式，其余行为测试文本';
    var parts = input.split('\n');
    var pattern = parts[0];
    var text = parts.slice(1).join('\n');
    var re;
    try {
      re = new RegExp(pattern, 'g');
    } catch (e) {
      return '正则语法错误：' + e.message;
    }
    var matches = text.match(re);
    if (!matches) return '无匹配';
    return '匹配 ' + matches.length + ' 处：\n' + matches.join('\n');
  }
};
