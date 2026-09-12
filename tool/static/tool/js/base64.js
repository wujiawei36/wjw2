window.__tool = {
  run: function (input) {
    if (!input) return '（空输入）';
    var trimmed = input.trim();
    var isB64 = /^[A-Za-z0-9+/]+={0,2}$/.test(trimmed) && trimmed.length % 4 === 0;
    if (isB64) {
      try {
        var binary = atob(trimmed);
        var bytes = new Uint8Array(binary.length);
        for (var i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
        return new TextDecoder('utf-8').decode(bytes);
      } catch (e) {
        // 解码失败则按普通文本编码
      }
    }
    var src = new TextEncoder().encode(input);
    var bin = '';
    for (var j = 0; j < src.length; j++) bin += String.fromCharCode(src[j]);
    return btoa(bin);
  }
};
