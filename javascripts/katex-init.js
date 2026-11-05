/**
 * KaTeX auto-render initialization
 * Renders LaTeX math from both text delimiters and arithmatex output
 */
document.addEventListener("DOMContentLoaded", function () {
    // First, render math from arithmatex output: <div class="arithmatex"><script type="math/tex">...</script></div>
    document.querySelectorAll('.arithmatex script[type="math/tex"]').forEach(function(script) {
        var display = script.getAttribute('mode') === 'display';
        var math = script.textContent;
        try {
            katex.render(math, script.parentElement, {
                displayMode: display,
                throwOnError: false,
                trust: true,
                macros: {
                    "\\R": "\\mathbb{R}",
                    "\\N": "\\mathbb{N}",
                    "\\Z": "\\mathbb{Z}",
                    "\\C": "\\mathbb{C}",
                }
            });
        } catch (e) {
            console.warn("KaTeX render error:", e, math);
        }
    });

    // Also render text delimiters for any raw math
    renderMathInElement(document.body, {
        delimiters: [
            { left: "$$", right: "$$", display: true },
            { left: "\\[", right: "\\]", display: true },
            { left: "$", right: "$", display: false },
            { left: "\\(", right: "\\)", display: false },
        ],
        ignoredTags: [
            "script", "noscript", "style", "textarea", "pre", "code",
            "option", "input", "select", "span.katex"
        ],
        throwOnError: false,
        trust: true,
    });
});