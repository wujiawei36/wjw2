window.__tool = {
  panels: [
    {
      id: 'encode',
      title: '转 Unicode（文本 → \\uXXXX）',
      placeholder: '输入文本…',
      button: '转 Unicode',
      run: function (input) {
        if (!input) return '（空输入）';
        return input.replace(/[\u007f-\uffff]/g, function (c) {
          return '\\u' + ('0000' + c.charCodeAt(0).toString(16)).slice(-4);
        });
      }
    },
    {
      id: 'decode',
      title: '转文本（\\uXXXX → 文本）',
      placeholder: '输入 \\uXXXX 转义序列…',
      button: '转文本',
      run: function (input) {
        if (!input) return '（空输入）';
        return input.replace(/\\u([0-9a-fA-F]{4})/g, function (m, hex) {
          return String.fromCharCode(parseInt(hex, 16));
        });
      }
    }
  ]
};
