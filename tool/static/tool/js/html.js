window.__tool = {
  panels: [
    {
      id: 'escape',
      title: '转义（文本 → HTML 实体）',
      placeholder: '输入文本…',
      button: '转义',
      run: function (input) {
        if (!input) return '（空输入）';
        return input.replace(/[&<>"']/g, function (c) {
          return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
        });
      }
    },
    {
      id: 'unescape',
      title: '反转义（HTML 实体 → 文本）',
      placeholder: '输入 HTML 实体…',
      button: '反转义',
      run: function (input) {
        if (!input) return '（空输入）';
        return input.replace(/&(amp|lt|gt|quot|#39|#x27|apos);/g, function (m, e) {
          return { amp: '&', lt: '<', gt: '>', quot: '"', '#39': "'", '#x27': "'", apos: "'" }[e];
        });
      }
    }
  ]
};
