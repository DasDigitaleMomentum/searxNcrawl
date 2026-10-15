from __future__ import annotations

from crawler.config import build_discovery_run_config, build_markdown_run_config


def test_default_run_configs_disable_verbose_logging_for_mcp_stdio() -> None:
    """MCP stdio defaults should keep crawl runtime logs quiet."""
    markdown_config = build_markdown_run_config()
    discovery_config = build_discovery_run_config()

    assert markdown_config.verbose is False
    assert discovery_config.verbose is False


def test_markdown_generator_keeps_highlighted_code_punctuation() -> None:
    """Pruning must not drop Prism/highlight.js token spans inside code blocks."""
    from crawler.config import build_markdown_generator

    tok = '<span class="token punctuation">{}</span>'
    html = (
        "<html><body><main>"
        "<h1>The details element</h1>"
        "<p>The details element creates a disclosure widget in which information"
        " is visible only when the widget is toggled into an open state.</p>"
        "<p>A summary or label must be provided using the summary element.</p>"
        '<pre class="language-html"><code class="language-html">'
        f'{tok.format("&lt;")}<span class="token tag">details</span>{tok.format("&gt;")}\n'
        f'  {tok.format("&lt;")}<span class="token tag">summary</span>{tok.format("&gt;")}'
        "Details"
        f'{tok.format("&lt;/")}<span class="token tag">summary</span>{tok.format("&gt;")}\n'
        f'{tok.format("&lt;/")}<span class="token tag">details</span>{tok.format("&gt;")}'
        "</code></pre>"
        '<p>Inline <code><span class="hljs-tag">&lt;br&gt;</span></code> works too.</p>'
        # CodeMirror 6 editor (MDN "Try it"): lines are divs, not <pre>.
        '<div class="cm-content"><div class="cm-line">'
        '<span class="cm-matchingBracket">&lt;</span><span>hr</span>'
        '<span class="cm-matchingBracket">&gt;</span></div></div>'
        "</main></body></html>"
    )

    result = build_markdown_generator().generate_markdown(input_html=html)

    assert "<details>\n  <summary>Details</summary>\n</details>" in result.raw_markdown
    assert "<details>\n  <summary>Details</summary>\n</details>" in result.fit_markdown
    assert "<br>" in result.fit_markdown
    assert "<hr>" in result.fit_markdown
