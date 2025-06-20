"""HTML to Markdown conversion utilities."""

from typing import Optional
import markdownify
import readabilipy.simple_json


def extract_content_from_html(html: str, use_readability: bool = True) -> str:
    """Extract and convert HTML content to Markdown format.

    Args:
        html: Raw HTML content to process
        use_readability: Whether to use readability algorithm to extract main content

    Returns:
        Simplified markdown version of the content
    """
    if use_readability:
        ret = readabilipy.simple_json.simple_json_from_html_string(
            html, use_readability=True
        )
        if not ret["content"]:
            return "<error>Page failed to be simplified from HTML</error>"
        html_content = ret["content"]
    else:
        html_content = html
    
    content = markdownify.markdownify(
        html_content,
        heading_style=markdownify.ATX,
    )
    return content


def html_to_markdown(
    html: str,
    *,
    heading_style: str = markdownify.ATX,
    strip_tags: Optional[list[str]] = None,
    convert_tags: Optional[dict[str, str]] = None,
    escape_asterisks: bool = True,
    escape_underscores: bool = True,
    use_readability: bool = False
) -> str:
    """Convert HTML to Markdown with customizable options.

    Args:
        html: Raw HTML content to convert
        heading_style: Style for headings (ATX or SETEXT)
        strip_tags: List of HTML tags to strip completely
        convert_tags: Dictionary mapping HTML tags to custom conversions
        escape_asterisks: Whether to escape asterisks in text
        escape_underscores: Whether to escape underscores in text
        use_readability: Whether to use readability algorithm for content extraction

    Returns:
        Markdown formatted string
    """
    if use_readability:
        return extract_content_from_html(html, use_readability=True)
    
    return markdownify.markdownify(
        html,
        heading_style=heading_style,
        strip=strip_tags or [],
        convert=convert_tags or {},
        escape_asterisks=escape_asterisks,
        escape_underscores=escape_underscores,
    )


def clean_markdown(markdown: str) -> str:
    """Clean up markdown content by removing excessive whitespace.

    Args:
        markdown: Raw markdown content

    Returns:
        Cleaned markdown content
    """
    # Remove excessive blank lines (more than 2 consecutive)
    lines = markdown.split('\n')
    cleaned_lines = []
    blank_count = 0
    
    for line in lines:
        if line.strip() == '':
            blank_count += 1
            if blank_count <= 2:
                cleaned_lines.append(line)
        else:
            blank_count = 0
            cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines).strip()


def is_html_content(content: str, content_type: str = "") -> bool:
    """Check if content appears to be HTML.

    Args:
        content: Content to check
        content_type: HTTP content-type header value

    Returns:
        True if content appears to be HTML
    """
    return (
        "<html" in content[:100].lower() or 
        "text/html" in content_type.lower() or 
        (not content_type and any(tag in content[:500].lower() for tag in ["<html", "<head", "<body", "<!doctype"]))
    )


class HtmlToMarkdownConverter:
    """A configurable HTML to Markdown converter."""
    
    def __init__(
        self,
        *,
        use_readability: bool = True,
        heading_style: str = markdownify.ATX,
        strip_tags: Optional[list[str]] = None,
        convert_tags: Optional[dict[str, str]] = None,
        escape_asterisks: bool = True,
        escape_underscores: bool = True,
        clean_output: bool = True
    ):
        """Initialize the converter with configuration options.

        Args:
            use_readability: Whether to use readability algorithm for content extraction
            heading_style: Style for headings (ATX or SETEXT)
            strip_tags: List of HTML tags to strip completely
            convert_tags: Dictionary mapping HTML tags to custom conversions
            escape_asterisks: Whether to escape asterisks in text
            escape_underscores: Whether to escape underscores in text
            clean_output: Whether to clean up the markdown output
        """
        self.use_readability = use_readability
        self.heading_style = heading_style
        self.strip_tags = strip_tags or []
        self.convert_tags = convert_tags or {}
        self.escape_asterisks = escape_asterisks
        self.escape_underscores = escape_underscores
        self.clean_output = clean_output
    
    def convert(self, html: str) -> str:
        """Convert HTML to Markdown using the configured options.

        Args:
            html: HTML content to convert

        Returns:
            Markdown formatted string
        """
        if self.use_readability:
            markdown = extract_content_from_html(html, use_readability=True)
        else:
            markdown = markdownify.markdownify(
                html,
                heading_style=self.heading_style,
                strip=self.strip_tags,
                convert=self.convert_tags,
                escape_asterisks=self.escape_asterisks,
                escape_underscores=self.escape_underscores,
            )
        
        if self.clean_output:
            markdown = clean_markdown(markdown)
        
        return markdown 