window.__tool = {
  panels: [
    {
      id: 'convert',
      placeholder: '输入数字（支持 0x / 0b / 0o 前缀）…',
      button: '转换',
      outputs: [
        { key: 'dec', label: '十进制' },
        { key: 'hex', label: '十六进制' },
        { key: 'oct', label: '八进制' },
        { key: 'bin', label: '二进制' }
      ],
      run: function (input) {
        var s = input.trim();
        if (!s) return '（空输入）';
        var n;
        if (/^0x[0-9a-f]+$/i.test(s)) n = parseInt(s, 16);
        else if (/^0b[01]+$/i.test(s)) n = parseInt(s.slice(2), 2);
        else if (/^0o[0-7]+$/i.test(s)) n = parseInt(s.slice(2), 8);
        else if (/^-?\d+$/.test(s)) n = parseInt(s, 10);
        else return '请输入十进制整数，或 0x / 0b / 0o 前缀的数';
        if (isNaN(n)) return '无效数字';
        return {
          dec: String(n),
          hex: '0x' + n.toString(16).toUpperCase(),
          oct: '0o' + n.toString(8),
          bin: '0b' + n.toString(2)
        };
      }
    }
  ]
};
