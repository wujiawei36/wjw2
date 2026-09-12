window.__tool = {
  panels: [
    {
      id: 'encode',
      title: '编码（文本 → Base64）',
      placeholder: '输入文本…',
      button: '编码',
      run: function (input) {
        if (!input) return '（空输入）';
        var src = new TextEncoder().encode(input);
        var bin = '';
        for (var j = 0; j < src.length; j++) bin += String.fromCharCode(src[j]);
        return btoa(bin);
      }
    },
    {
      id: 'decode',
      title: '解码（Base64 → 文本）',
      placeholder: '输入 Base64…',
      button: '解码',
      run: function (input) {
        var s = input.trim();
        if (!s) return '（空输入）';
        try {
          var binary = atob(s);
          var bytes = new Uint8Array(binary.length);
          for (var i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
          return new TextDecoder('utf-8').decode(bytes);
        } catch (e) {
          return '解码失败：' + e.message;
        }
      }
    }
  ]
};
