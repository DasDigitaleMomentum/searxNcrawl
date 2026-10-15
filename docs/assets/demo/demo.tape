# Records docs/assets/demo.gif with https://github.com/charmbracelet/vhs.
# Needs a SearXNG instance with JSON output; run from the repository root:
#   vhs docs/assets/demo/demo.tape
Output docs/assets/demo.gif
Set Shell "zsh"
Set FontSize 15
Set Width 1300
Set Height 660
Set Padding 20
Set Theme "GitHub Dark"
Set TypingSpeed 40ms
Hide
Type "export PROMPT='$ ' && clear"
Enter
Show
Type "export SEARXNG_URL=http://localhost:8899"
Enter
Sleep 400ms
Type 'uv run docs/assets/demo/demo.py "crawl4ai quick start"'
Sleep 500ms
Enter
Wait+Screen@120s /kB of Markdown/
Sleep 5s
