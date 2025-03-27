from rich.console import Console
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.live import Live
from typing import Dict, Any, Generator

from .config import merged_config

# Default configuration
DEFAULT_THEME = "monokai"
DEFAULT_MARKDOWN_STYLE = "default"


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
    return terminal_config.get("theme", DEFAULT_THEME)


def get_markdown_style() -> str:
    """Get the configured markdown style"""
    terminal_config = get_terminal_config()
    return terminal_config.get("markdown_style", DEFAULT_MARKDOWN_STYLE)


# Create a console instance with configurable settings
def create_console() -> Console:
    """Create a console with configured settings"""
    terminal_config = get_terminal_config()

    # Extract console settings from config
    width = terminal_config.get("width", None)
    color_system = terminal_config.get("color_system", "auto")
    highlight = terminal_config.get("highlight", True)

    return Console(width=width, color_system=color_system, highlight=highlight)


# Create the default console
console = create_console()


def highlight_markdown(text):
    """
    Highlight markdown text.
    Returns a Rich renderable object.
    """
    style = get_markdown_style()
    return Markdown(text, style=style)


def highlight_diff(diff_text):
    """
    Highlight a git diff with proper syntax highlighting.
    Returns a Rich renderable object.
    """
    theme = get_theme()
    return Syntax(diff_text, "diff", theme=theme, line_numbers=True)


def highlight_code(code, language="python"):
    """
    Highlight code with proper syntax highlighting.
    Returns a Rich renderable object.
    """
    theme = get_theme()
    return Syntax(code, language, theme=theme, line_numbers=True)


class StreamingFormatter:
    """
    Format streaming content with appropriate highlighting based on format type.
    This handles partial content that's being streamed.
    """

    def __init__(self, format_type: str = "markdown"):
        """
        Initialize the formatter.
        
        Args:
            format_type: The type of formatting to apply ("markdown", "diff", "code")
        """
        self.buffer = ""
        self.console = create_console()
        self.format_type = format_type

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
        Format the current buffer with appropriate highlighting.
        
        Returns:
            A Rich renderable object
        """
        try:
            if self.format_type == "markdown":
                style = get_markdown_style()
                return Markdown(self.buffer, style=style)
            elif self.format_type == "diff":
                return highlight_diff(self.buffer)
            elif self.format_type == "code":
                return highlight_code(self.buffer)
            else:
                # Default to plain text if format type is unknown
                return self.buffer
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


def stream_with_highlighting(stream_generator: Generator[str, None, None], format_type: str = "markdown") -> None:
    """
    Stream content with syntax highlighting.

    Args:
        stream_generator: A generator that yields content chunks
        format_type: The type of formatting to apply ("markdown", "diff", "code")
    """
    formatter = StreamingFormatter(format_type)
    formatter.display_stream(stream_generator)
