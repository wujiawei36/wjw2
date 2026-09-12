window.__tool = {
  run: function (input) {
    var lines = input.split('\n');
    var seen = {};
    var out = [];
    for (var i = 0; i < lines.length; i++) {
      var line = lines[i];
      if (!(line in seen)) {
        seen[line] = true;
        out.push(line);
      }
    }
    return out.join('\n');
  }
};
