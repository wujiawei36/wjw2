window.__tool = {
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
        return algo + ': ' + hex;
      });
    })).then(function (results) {
      return results.join('\n');
    });
  }
};
