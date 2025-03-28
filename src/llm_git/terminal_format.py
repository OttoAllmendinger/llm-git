from rich.console import Console
from rich.syntax import Syntax as RichSyntax
from rich.markdown import Markdown as RichMarkdown
from rich.live import Live
from typing import Dict, Any, Generator, Optional

from .config import merged_config


def get_terminal_config() -> Dict[str, Any]:
    """
    Get terminal configuration from merged config.

    Returns:
        Dict with terminal configuration settings
    """
    config = merged_config()
    return config.get("terminal", {})


def get_theme() -> str:
    """Get the configured syntax highlighting theme"""
    terminal_config = get_terminal_config()
    return terminal_config.get("theme", "monokai")


def get_markdown_style() -> str:
    """Get the configured markdown style"""
    terminal_config = get_terminal_config()
    return terminal_config.get("markdown_style", "default")


def get_syntax_width() -> Optional[int]:
    """Get the configured width for syntax highlighted content"""
    terminal_config = get_terminal_config()
    return terminal_config.get("syntax_width", None)


def get_markdown_width() -> int:
    """Get the configured width for markdown content"""
    terminal_config = get_terminal_config()
    return terminal_config.get("markdown_width", 72)


# Create a console instance with configurable settings
def create_console(width=None) -> Console:
    """
    Create a console with configured settings.
    
    Args:
        width: Optional width override for the console
        
    Returns:
        A configured Console instance
    """
    terminal_config = get_terminal_config()

    # Extract console settings from config
    config_width = get_syntax_width()
    # Use provided width if specified, otherwise use config width
    final_width = width if width is not None else config_width
    color_system = terminal_config.get("color_system", "auto")
    highlight = terminal_config.get("highlight", True)

    return Console(width=final_width, color_system=color_system, highlight=highlight)


# Create the default console
console = create_console()


class Formatter:
    """Base class for formatters"""
    def render(self, content: str):
        """Render content with this formatter"""
        raise NotImplementedError("Subclasses must implement render")


class MarkdownFormatter(Formatter):
    """Format content as Markdown"""
    def render(self, content: str):
        return RichMarkdown(content, style=get_markdown_style())


class SyntaxFormatter(Formatter):
    """Format content with syntax highlighting"""
    def __init__(self, language: str, line_numbers: bool = True):
        self.language = language
        self.line_numbers = line_numbers
        
    def render(self, content: str):
        return RichSyntax(
            content, 
            self.language, 
            theme=get_theme(), 
            line_numbers=self.line_numbers
        )


# Simple helper functions to create formatters
def markdown():
    """Create a Markdown formatter"""
    return MarkdownFormatter()


def syntax(language: str, line_numbers: bool = True):
    """Create a syntax formatter for the specified language"""
    return SyntaxFormatter(language, line_numbers)


class StreamingFormatter:
    """
    Format streaming content with appropriate highlighting based on formatter.
    This handles partial content that's being streamed.
    """

    def __init__(self, formatter):
        """
        Initialize the formatter.
        
        Args:
            formatter: A formatter object with a render method
        """
        self.buffer = ""
        # Use a custom console with configured markdown width for markdown
        if isinstance(formatter, MarkdownFormatter):
            self.console = create_console(width=get_markdown_width())
        else:
            self.console = create_console()
        self.formatter = formatter

    def update(self, new_content: str) -> Any:
        """
        Update with new content from the stream.
        
        Args:
            new_content: New content to add to the buffer
            
        Returns:
            A Rich renderable object
        """
        self.buffer += new_content
        return self._format_current_buffer()

    def _format_current_buffer(self) -> Any:
        """
        Format the current buffer with the provided formatter.
        
        Returns:
            A Rich renderable object
        """
        try:
            # Use the formatter's render method
            return self.formatter.render(self.buffer)
        except Exception:
            # If formatting fails, just return the raw buffer
            return self.buffer

    def display_stream(self, stream_generator: Generator[str, None, None]) -> None:
        """
        Display a stream with live updating and formatting.

        Args:
            stream_generator: A generator that yields content chunks
        """
        with Live(console=self.console, refresh_per_second=10) as live:
            for chunk in stream_generator:
                live.update(self.update(chunk))


def stream_with_highlighting(stream_generator: Generator[str, None, None], formatter=None) -> None:
    """
    Stream content with syntax highlighting.

    Args:
        stream_generator: A generator that yields content chunks
        formatter: A formatter object with a render method
    """
    if formatter is None:
        formatter = markdown()
        
    formatter_instance = StreamingFormatter(formatter)
    formatter_instance.display_stream(stream_generator)
