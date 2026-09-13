(function () {
  'use strict';

  // RFC 1321 MD5 实现，输入按 UTF-8 编码（与后端 hashlib.md5(text.encode('utf-8')) 一致）
  function md5Hex(input) {
    var K = [
      0xd76aa478, 0xe8c7b756, 0x242070db, 0xc1bdceee,
      0xf57c0faf, 0x4787c62a, 0xa8304613, 0xfd469501,
      0x698098d8, 0x8b44f7af, 0xffff5bb1, 0x895cd7be,
      0x6b901122, 0xfd987193, 0xa679438e, 0x49b40821,
      0xf61e2562, 0xc040b340, 0x265e5a51, 0xe9b6c7aa,
      0xd62f105d, 0x02441453, 0xd8a1e681, 0xe7d3fbc8,
      0x21e1cde6, 0xc33707d6, 0xf4d50d87, 0x455a14ed,
      0xa9e3e905, 0xfcefa3f8, 0x676f02d9, 0x8d2a4c8a,
      0xfffa3942, 0x8771f681, 0x6d9d6122, 0xfde5380c,
      0xa4beea44, 0x4bdecfa9, 0xf6bb4b60, 0xbebfbc70,
      0x289b7ec6, 0xeaa127fa, 0xd4ef3085, 0x04881d05,
      0xd9d4d039, 0xe6db99e5, 0x1fa27cf8, 0xc4ac5665,
      0xf4292244, 0x432aff97, 0xab9423a7, 0xfc93a039,
      0x655b59c3, 0x8f0ccc92, 0xffeff47d, 0x85845dd1,
      0x6fa87e4f, 0xfe2ce6e0, 0xa3014314, 0x4e0811a1,
      0xf7537e82, 0xbd3af235, 0x2ad7d2bb, 0xeb86d391
    ];
    var S = [
      7, 12, 17, 22, 7, 12, 17, 22, 7, 12, 17, 22, 7, 12, 17, 22,
      5, 9, 14, 20, 5, 9, 14, 20, 5, 9, 14, 20, 5, 9, 14, 20,
      4, 11, 16, 23, 4, 11, 16, 23, 4, 11, 16, 23, 4, 11, 16, 23,
      6, 10, 15, 21, 6, 10, 15, 21, 6, 10, 15, 21, 6, 10, 15, 21
    ];

    var msg = new TextEncoder().encode(input);
    var len = msg.length;
    var bitLen = len * 8;

    // 补位：追加 0x80 + 0 填充 + 64 位长度（小端）
    var paddedLen = (((len + 8) >> 6) + 1) << 6;
    var data = new Uint8Array(paddedLen);
    data.set(msg);
    data[len] = 0x80;
    var low = bitLen >>> 0;
    var high = Math.floor(bitLen / 0x100000000);
    data[paddedLen - 8] = low & 0xff;
    data[paddedLen - 7] = (low >>> 8) & 0xff;
    data[paddedLen - 6] = (low >>> 16) & 0xff;
    data[paddedLen - 5] = (low >>> 24) & 0xff;
    data[paddedLen - 4] = high & 0xff;
    data[paddedLen - 3] = (high >>> 8) & 0xff;
    data[paddedLen - 2] = (high >>> 16) & 0xff;
    data[paddedLen - 1] = (high >>> 24) & 0xff;

    var a0 = 0x67452301, b0 = 0xefcdab89, c0 = 0x98badcfe, d0 = 0x10325476;

    function rotl(x, c) { return (x << c) | (x >>> (32 - c)); }

    for (var i = 0; i < paddedLen; i += 64) {
      var M = new Array(16);
      for (var j = 0; j < 16; j++) {
        M[j] = data[i + j * 4] |
          (data[i + j * 4 + 1] << 8) |
          (data[i + j * 4 + 2] << 16) |
          (data[i + j * 4 + 3] << 24);
      }
      var A = a0, B = b0, C = c0, D = d0;
      for (var r = 0; r < 64; r++) {
        var F, g;
        if (r < 16) {
          F = (B & C) | (~B & D);
          g = r;
        } else if (r < 32) {
          F = (D & B) | (~D & C);
          g = (5 * r + 1) % 16;
        } else if (r < 48) {
          F = B ^ C ^ D;
          g = (3 * r + 5) % 16;
        } else {
          F = C ^ (B | ~D);
          g = (7 * r) % 16;
        }
        F = (F + A + K[r] + M[g]) | 0;
        A = D; D = C; C = B;
        B = (B + rotl(F, S[r])) | 0;
      }
      a0 = (a0 + A) | 0;
      b0 = (b0 + B) | 0;
      c0 = (c0 + C) | 0;
      d0 = (d0 + D) | 0;
    }

    function hex32(x) {
      var h = '';
      for (var k = 0; k < 4; k++) {
        h += ((x >>> (k * 8)) & 0xff).toString(16).padStart(2, '0');
      }
      return h;
    }
    return hex32(a0) + hex32(b0) + hex32(c0) + hex32(d0);
  }

  window.__tool = {
    panels: [
      {
        id: 'md5',
        placeholder: '输入文本…',
        button: '计算 MD5',
        run: function (input) {
          if (!input) return '（空输入）';
          return md5Hex(input);
        }
      }
    ]
  };
})();
