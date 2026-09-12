window.__tool = {
  panels: [
    {
      id: 'hash',
      placeholder: '输入文本…',
      button: '计算',
      outputs: [
        { key: 'SHA-1', label: 'SHA-1' },
        { key: 'SHA-256', label: 'SHA-256' },
        { key: 'SHA-384', label: 'SHA-384' },
        { key: 'SHA-512', label: 'SHA-512' }
      ],
      run: function (input) {
        if (!input) return '（空输入）';
        var data = new TextEncoder().encode(input);
        var algos = ['SHA-1', 'SHA-256', 'SHA-384', 'SHA-512'];
        return Promise.all(algos.map(function (algo) {
          return crypto.subtle.digest(algo, data).then(function (buf) {
            var bytes = new Uint8Array(buf);
            var hex = '';
            for (var i = 0; i < bytes.length; i++) {
              hex += bytes[i].toString(16).padStart(2, '0');
            }
            return { algo: algo, hex: hex };
          });
        })).then(function (results) {
          var out = {};
          results.forEach(function (r) { out[r.algo] = r.hex; });
          return out;
        });
      }
    }
  ]
};
