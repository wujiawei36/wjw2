window.__tool = {
  panels: [
    {
      id: 'encode',
      title: '编码（文本 → URL 编码）',
      placeholder: '输入文本…',
      button: '编码',
      run: function (input) {
        if (!input) return '（空输入）';
        return encodeURIComponent(input);
      }
    },
    {
      id: 'decode',
      title: '解码（URL 编码 → 文本）',
      placeholder: '输入 URL 编码…',
      button: '解码',
      run: function (input) {
        var s = input.trim();
        if (!s) return '（空输入）';
        try {
          return decodeURIComponent(s);
        } catch (e) {
          return '解码失败：' + e.message;
        }
      }
    }
  ]
};
