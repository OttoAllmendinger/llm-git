import os
from dataclasses import dataclass
from typing import Any, Callable, List, Optional, TypeVar

import click
import llm

from .terminal_format import console, stream_with_highlighting

T = TypeVar('T')

@dataclass
class LLMRequest:
    """
    Represents a request to an LLM model and provides methods to execute it.
    
    Attributes:
        prompt: The main prompt text to send to the model
        system_prompt: The system prompt to set context for the model
        model_id: Optional model identifier, uses default if None
        stream: Whether to stream the response
        output_type: Format type for output highlighting ("markdown", "diff", "code")
    """
    prompt: str
    system_prompt: str
    model_id: Optional[str] = None
    stream: bool = True
    output_type: str = "markdown"

    def execute(self) -> Any:
        """
        Execute this LLM request.
        
        Returns:
            The model's response
            
        Raises:
            click.ClickException: If the prompt is empty
        """
        from llm.cli import get_default_model

        if not self.prompt:
            raise click.ClickException("Prompt is empty")

        model_id = self.model_id or get_default_model()
        model = llm.get_model(model_id)

        if model.needs_key:
            model.key = llm.get_key(None, model.needs_key, model.key_env_var)

        if os.environ.get("LLM_GIT_SHOW_PROMPTS", "0") == "1":
            console.print("Prompt:", style="bold green")
            console.print(self.prompt)
            console.print("System Prompt:", style="bold green")
            console.print(self.system_prompt)

        if os.environ.get("LLM_GIT_ABORT", None) == "request":
            raise click.Abort()

        try:
            result = model.prompt(self.prompt, system=self.system_prompt, stream=self.stream)
            if self.stream:
                # Use the streaming formatter with highlighting by default
                def stream_generator():
                    for chunk in result:
                        yield str(chunk)
                stream_with_highlighting(stream_generator(), format_type=self.output_type)
            return result
        except Exception as e:
            console.print(f"prompt={self.prompt}", style="bold red")
            console.print(f"system_prompt={self.system_prompt}", style="bold red")
            console.print(f"Error: {e}", style="bold red")
            console.print_exception()
            raise

    def with_retry(self, func: Callable[[str], T], retries: int = 3) -> T:
        """
        Execute this LLM request with retries on error.
        
        Args:
            func: Function to process the LLM result
            retries: Number of retry attempts
            
        Returns:
            The result of func applied to the LLM response
            
        Raises:
            click.ClickException: If all retries fail
        """
        errors: List[Exception] = []
        original_prompt = self.prompt
        
        for i in range(retries):
            if errors:
                # Add error information to the prompt
                error_text = "\n".join(str(e) for e in errors)
                self.prompt = f"{original_prompt}\n\nPrevious errors:\n```\n{error_text}\n```\n"
            
            result = self.execute()
            try:
                return func(str(result))
            except Exception as e:
                console.print(f"Error: {e}, trying again", style="bold red")
                errors.append(e)
                # Reset prompt for next attempt
                self.prompt = original_prompt
        
        raise click.ClickException(f"Failed after {retries} retries") from errors[-1]

    @classmethod
    def create(cls, prompt: str, system_prompt: str, model_id: Optional[str] = None, 
               stream: bool = True, output_type: str = "markdown") -> "LLMRequest":
        """
        Create a new LLMRequest instance.
        
        Args:
            prompt: The main prompt text
            system_prompt: The system prompt
            model_id: Optional model identifier
            stream: Whether to stream the response
            output_type: Format type for output highlighting
            
        Returns:
            A new LLMRequest instance
        """
        return cls(
            prompt=prompt, 
            system_prompt=system_prompt, 
            model_id=model_id, 
            stream=stream,
            output_type=output_type
        )
