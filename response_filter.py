"""
Response Filter Module

Comprehensive filtering layer for ChatGPT API responses.
Cleans up UI artifacts, formatting issues, and normalizes output
for reliable use as a coding agent.
"""

import re
from typing import Callable

# Common programming languages that appear in code blocks
LANGUAGES = [
    "python", "javascript", "typescript", "java", "c", "cpp", "csharp", "cs",
    "go", "rust", "ruby", "php", "swift", "kotlin", "scala", "perl",
    "bash", "shell", "sh", "zsh", "powershell", "ps1", "cmd", "batch",
    "sql", "mysql", "postgresql", "sqlite", "mongodb",
    "html", "css", "scss", "sass", "less",
    "json", "yaml", "yml", "xml", "toml", "ini", "conf",
    "markdown", "md", "txt", "text", "plaintext",
    "dockerfile", "docker", "makefile", "cmake",
    "r", "matlab", "julia", "lua", "elixir", "erlang", "haskell",
    "vim", "awk", "sed", "grep",
]


def remove_copy_code_artifacts(text: str) -> str:
    """
    Remove '{language}Copy code' patterns that appear from ChatGPT UI extraction.
    
    Examples:
        'pythonCopy codedef foo():' -> 'def foo():'
        'bashCopy code#!/bin/bash' -> '#!/bin/bash'
    """
    # Build pattern for all known languages
    lang_pattern = "|".join(re.escape(lang) for lang in LANGUAGES)
    
    # Match: {language}Copy code (case insensitive for language)
    pattern = rf"(?i)({lang_pattern})Copy code"
    text = re.sub(pattern, "", text)
    
    # Also catch generic "Copy code" that might appear standalone
    text = re.sub(r"(?<!\w)Copy code(?!\w)", "", text)
    
    return text


def remove_edit_code_artifacts(text: str) -> str:
    """
    Remove 'Edit code' or '{language}Edit code' patterns.
    """
    lang_pattern = "|".join(re.escape(lang) for lang in LANGUAGES)
    pattern = rf"(?i)({lang_pattern})?Edit code"
    return re.sub(pattern, "", text)


def remove_html_artifacts(text: str) -> str:
    """
    Remove common HTML artifacts that might leak through.
    """
    # Remove HTML entities
    replacements = {
        "&lt;": "<",
        "&gt;": ">",
        "&amp;": "&",
        "&quot;": '"',
        "&#39;": "'",
        "&nbsp;": " ",
    }
    for entity, char in replacements.items():
        text = text.replace(entity, char)
    
    return text


def normalize_code_blocks(text: str) -> str:
    """
    Normalize code block formatting.
    Convert common variations to standard markdown format.
    """
    # Remove any triple backticks that might have been extracted as plain text
    # but keep the structure intact
    # This handles cases where markdown wasn't rendered
    
    return text


def remove_ui_button_text(text: str) -> str:
    """
    Remove common UI button/label text that leaks into responses.
    """
    ui_patterns = [
        # Remove only full-line UI labels to avoid mutating valid sentence content.
        r"(?m)^[ \t]*Copy[ \t]*$",
        r"(?m)^[ \t]*Copied![ \t]*$",
        r"(?m)^[ \t]*Run[ \t]*$",
        r"(?m)^[ \t]*\d+[ \t]*$",  # Standalone line numbers
    ]
    
    for pattern in ui_patterns:
        text = re.sub(pattern, "", text)
    
    return text


def normalize_whitespace(text: str) -> str:
    """
    Normalize excessive whitespace while preserving code structure.
    """
    # Replace multiple consecutive blank lines with at most 2
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    
    # Remove trailing whitespace from lines
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    
    # Trim leading/trailing whitespace from entire response
    text = text.strip()
    
    return text


def remove_thinking_artifacts(text: str) -> str:
    """
    Remove 'thinking' or reasoning artifacts that shouldn't be in final output.
    """
    # Remove <think>...</think> blocks if present
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    
    return text


# ============================================================================
# Main Filter Pipeline
# ============================================================================

# Ordered list of filter functions to apply
DEFAULT_FILTERS: list[Callable[[str], str]] = [
    remove_copy_code_artifacts,
    remove_edit_code_artifacts,
    remove_html_artifacts,
    remove_ui_button_text,
    remove_thinking_artifacts,
    normalize_whitespace,
]


def filter_response(text: str, filters: list[Callable[[str], str]] | None = None) -> str:
    """
    Apply all filters to clean up a response.
    
    Args:
        text: The raw response text to filter
        filters: Optional custom list of filter functions. Uses DEFAULT_FILTERS if None.
    
    Returns:
        Cleaned response text
    """
    if text is None:
        return ""
    
    if filters is None:
        filters = DEFAULT_FILTERS
    
    for filter_fn in filters:
        text = filter_fn(text)
    
    return text


# ============================================================================
# Testing / Debug Utilities
# ============================================================================

def analyze_response(text: str) -> dict:
    """
    Analyze a response for potential formatting issues.
    Useful for debugging and identifying new patterns to filter.
    
    Returns:
        Dict with detected issues and their counts
    """
    issues = {}
    
    # Check for Copy code patterns
    lang_pattern = "|".join(re.escape(lang) for lang in LANGUAGES)
    copy_matches = re.findall(rf"(?i)({lang_pattern})Copy code", text)
    if copy_matches:
        issues["language_copy_code"] = len(copy_matches)
    
    # Check for standalone Copy code
    standalone_copy = len(re.findall(r"(?<!\w)Copy code(?!\w)", text))
    if standalone_copy:
        issues["standalone_copy_code"] = standalone_copy
    
    # Check for HTML entities
    html_entities = ["&lt;", "&gt;", "&amp;", "&quot;", "&#39;"]
    for entity in html_entities:
        count = text.count(entity)
        if count:
            issues[f"html_entity_{entity}"] = count
    
    return issues


if __name__ == "__main__":
    # Quick test
    test_cases = [
        "pythonCopy codedef hello():\n    print('Hello')",
        "Here's the code:\nbashCopy code#!/bin/bash\necho 'test'",
        "Use &lt;div&gt; for containers",
        "Simple text without issues",
    ]
    
    print("Response Filter Test\n" + "=" * 50)
    for text in test_cases:
        print(f"\nOriginal: {text!r}")
        filtered = filter_response(text)
        print(f"Filtered: {filtered!r}")
        issues = analyze_response(text)
        if issues:
            print(f"Issues detected: {issues}")
