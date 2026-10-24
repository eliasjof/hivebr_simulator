/**
 * KaTeX auto-render initialization
 * Renders LaTeX math delimiters in the page content
 */
document.addEventListener("DOMContentLoaded", function () {
    renderMathInElement(document.body, {
        // Custom delimiters for inline and display math
        delimiters: [
            { left: "$$", right: "$$", display: true },      // Display: $$...$$
            { left: "\\[", right: "\\]", display: true },    // Display: \[...\]
            { left: "$", right: "$", display: false },       // Inline: $...$
            { left: "\\(", right: "\\)", display: false },   // Inline: \(...\)
        ],
        // Ignore these tags (don't render math inside them)
        ignoredTags: [
            "script", "noscript", "style", "textarea", "pre", "code",
            "option", "input", "select", "span.katex"
        ],
        // Throw error on parse error (set false to ignore)
        throwOnError: false,
        // Trust context for unsafe commands
        trust: true,
        // Macro definitions
        macros: {
            "\\R": "\\mathbb{R}",
            "\\N": "\\mathbb{N}",
            "\\Z": "\\mathbb{Z}",
            "\\C": "\\mathbb{C}",
            "\\dot": "\\dot{#1}",
            "\\ddot": "\\ddot{#1}",
        }
    });
});