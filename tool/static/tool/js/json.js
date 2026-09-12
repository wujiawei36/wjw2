window.__tool = {
  run: function (input) {
    if (!input.trim()) {
      return '（空输入）';
    }
    var obj;
    try {
      obj = JSON.parse(input);
    } catch (e) {
      return 'JSON 解析失败：' + e.message;
    }
    return JSON.stringify(obj, null, 2);
  }
};
