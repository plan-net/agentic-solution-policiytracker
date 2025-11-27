"""
Document preprocessing utilities for cleaning scraped web content.

This module handles:
- YAML frontmatter extraction and preservation
- HTML entity decoding
- Link removal (markdown, images, bare URLs)
- Duplicate line removal
- Whitespace cleaning
"""

import html
import re

import structlog

logger = structlog.get_logger()


def extract_frontmatter(content: str) -> tuple[str, str]:
    """
    Extract YAML frontmatter from document.

    Frontmatter is content between --- markers at the start of the document.

    Args:
        content: Full document content

    Returns:
        Tuple of (frontmatter, body)
    """
    # Match content between --- markers at start of document
    frontmatter_pattern = r"^---\n(.*?)\n---\n(.*)$"
    match = re.match(frontmatter_pattern, content, re.DOTALL)

    if match:
        return match.group(1), match.group(2)
    return "", content


def decode_html_entities(text: str) -> str:
    """
    Decode HTML entities to their Unicode equivalents.

    Converts:
    - &amp; → &
    - &lt; → <
    - &gt; → >
    - &quot; → "
    - &#39; → '
    - And all other HTML entities

    Args:
        text: Text containing HTML entities

    Returns:
        Text with HTML entities decoded
    """
    return html.unescape(text)


def remove_links(text: str) -> str:
    """
    Remove various types of links from text.

    Removes:
    - Image links: ![alt](url) → (removed entirely)
    - Markdown links: [text](url) → (removed entirely, including text)
    - Bare URLs: https://... → (removed)
    - www URLs: www.example.com → (removed)

    Args:
        text: Text containing links

    Returns:
        Text with all links removed
    """
    # Remove image links: ![alt](url)
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)

    # Remove markdown links entirely (both text and url): [text](url)
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", "", text)

    # Remove standalone URLs (http/https)
    text = re.sub(r"https?://\S+", "", text)

    # Remove www. URLs
    text = re.sub(r"www\.\S+", "", text)

    return text


def remove_duplicate_lines(text: str) -> str:
    """
    Remove consecutive duplicate lines.

    Common in scraped content where navigation elements repeat.

    Args:
        text: Text with potential duplicate lines

    Returns:
        Text with consecutive duplicates removed
    """
    lines = text.split("\n")
    deduplicated = []
    prev_line = None

    for line in lines:
        stripped = line.strip()
        # Keep line if it's different from previous or is empty (preserve spacing)
        if stripped != prev_line or not stripped:
            deduplicated.append(line)
            prev_line = stripped

    return "\n".join(deduplicated)


def remove_promotional_content(text: str) -> str:
    """
    Remove promotional and marketing content that confuses LLM extraction.

    Removes sections like:
    - "7 Best Stocks for the Next 30 Days"
    - "Want the latest recommendations"
    - "Click to get this free report"
    - Marketing calls-to-action

    Args:
        text: Text with potential promotional content

    Returns:
        Text with promotional sections removed
    """
    # Common promotional phrases to filter
    promotional_patterns = [
        r"7 Best Stocks for the Next 30 Days.*?(?=\n\n|\Z)",
        r"Just released: Experts distill.*?(?=\n\n|\Z)",
        r"Want the latest recommendations.*?(?=\n\n|\Z)",
        r"Click to get this free report.*?(?=\n\n|\Z)",
        r"See them now >>.*?(?=\n\n|\Z)",
        r"Free Stock Analysis Report.*?(?=\n\n|\Z)",
        r"This article originally published on.*?(?=\n\n|\Z)",
        r"The views and opinions expressed herein.*?(?=\n\n|\Z)",
    ]

    for pattern in promotional_patterns:
        text = re.sub(pattern, "", text, flags=re.DOTALL | re.IGNORECASE)

    return text


def clean_whitespace(text: str) -> str:
    """
    Clean excessive whitespace.

    - Multiple blank lines → single blank line
    - Trailing whitespace from lines → removed
    - Leading/trailing document whitespace → preserved

    Args:
        text: Text with excessive whitespace

    Returns:
        Text with cleaned whitespace
    """
    # Replace multiple blank lines with double newline
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)

    # Remove trailing whitespace from each line
    lines = [line.rstrip() for line in text.split("\n")]

    return "\n".join(lines)


def preprocess_document(content: str, enable_link_removal: bool = True) -> str:
    """
    Complete preprocessing pipeline for scraped documents.

    Pipeline:
    1. Extract and preserve frontmatter (YAML metadata)
    2. Decode HTML entities (&amp; → &, &gt; → >, etc.)
    3. Remove promotional/marketing content
    4. Remove links from body (optional)
    5. Remove duplicate consecutive lines
    6. Clean excessive whitespace
    7. Reassemble document

    Args:
        content: Raw document content
        enable_link_removal: Whether to remove links (default: True)

    Returns:
        Preprocessed document content with preserved frontmatter
    """
    # Step 1: Extract frontmatter and body
    frontmatter, body = extract_frontmatter(content)

    if frontmatter:
        logger.debug("Extracted frontmatter from document")

    # Step 2: Decode HTML entities
    original_body = body
    body = decode_html_entities(body)
    if body != original_body:
        logger.debug("Decoded HTML entities in document body")

    # Step 3: Remove promotional content
    original_length = len(body)
    body = remove_promotional_content(body)
    removed_chars = original_length - len(body)
    if removed_chars > 0:
        logger.debug(f"Removed promotional content: reduced by {removed_chars} characters")

    # Step 4: Clean body
    if enable_link_removal:
        original_length = len(body)
        body = remove_links(body)
        removed_chars = original_length - len(body)
        if removed_chars > 0:
            logger.debug(f"Removed links: reduced content by {removed_chars} characters")

    body = remove_duplicate_lines(body)
    body = clean_whitespace(body)

    # Step 5: Reassemble document
    if frontmatter:
        return f"---\n{frontmatter}\n---\n\n{body}"
    return body
