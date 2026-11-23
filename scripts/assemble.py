"""Inline data/geo.json and src/model.js into src/page.html -> index.html (single self-contained page)."""
from pathlib import Path
R = Path(__file__).resolve().parent.parent
p = (R/'src/page.html').read_text()
p = p.replace('<script>/*GEO*/</script>', '<script>const GEO=' + (R/'data/geo.json').read_text() + ';</script>')
p = p.replace('<script>/*WX*/</script>', '<script>const WXG=' + (R/'data/wx_grid.json').read_text() + ';</script>')
p = p.replace('<script>/*MODEL*/</script>', '<script>' + (R/'src/model.js').read_text() + '</script>')
(R/'index.html').write_text(p)
print('wrote index.html', len(p))
