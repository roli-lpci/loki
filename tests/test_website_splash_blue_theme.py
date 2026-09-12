from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPLASH = ROOT / "website" / "splash"


def test_splash_uses_blue_brand_theme_and_action_pitch():
    html = (SPLASH / "index.html").read_text()
    css = (SPLASH / "site.css").read_text()
    javascript = (SPLASH / "site.js").read_text()

    assert 'content="#030b1a"' in html
    assert 'The agent that&nbsp;</span><strong class="tagline-action"' in html
    assert '>evolves with you</strong>' in html
    assert "--blue-3: #60a5fa" in css
    assert "--green-" not in css
    assert "'works across your tools'" in javascript
    assert "'automates recurring work'" in javascript
    assert "'keeps context across sessions'" in javascript
    assert "'turns intent into action'" in javascript


def test_github_install_tab_exposes_a_real_link():
    html = (SPLASH / "index.html").read_text()
    javascript = (SPLASH / "site.js").read_text()

    assert 'class="install-command-link"' in html
    assert 'href="https://github.com/wundercorp/loki"' in html
    assert 'target="_blank"' in html
    assert "github: { value: 'https://github.com/wundercorp/loki', link: true }" in javascript
    assert "installLink.hidden = !config.link" in javascript
