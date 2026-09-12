window.__tool = {
  run: function (input) {
    var text = input;
    var chars = text.length;
    var bytes = new TextEncoder().encode(text).length;
    var lines = text ? text.split('\n').length : 0;
    var noSpace = text.replace(/\s/g, '');
    var chinese = (text.match(/[\u4e00-\u9fa5]/g) || []).length;
    return '字符数: ' + chars +
           '\n字节数(UTF-8): ' + bytes +
           '\n行数: ' + lines +
           '\n不含空白字符数: ' + noSpace.length +
           '\n中文字符数: ' + chinese;
  }
};
