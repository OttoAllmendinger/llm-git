import string
from typing import Dict, List, Any, Optional, cast

from . import config

# Define template types
TemplateDict = Dict[str, str]
TemplateList = List[TemplateDict]
FormattedPrompts = Dict[str, str]


class LenientFormatter(string.Formatter):
    """
    A custom formatter that doesn't raise KeyError for missing keys.
    Instead, it returns a placeholder indicating the missing key.
    """

    def get_value(self, key, args, kwargs):
        try:
            return super().get_value(key, args, kwargs)
        except (KeyError, AttributeError):
            return f"<KeyError {key}>"

    def get_field(self, field_name, args, kwargs):
        try:
            return super().get_field(field_name, args, kwargs)
        except (KeyError, AttributeError):
            return f"<KeyError {field_name}>", field_name


def apply_format(
    templates: TemplateList, formatter: Optional[string.Formatter] = None, **kwargs: Any
) -> FormattedPrompts:
    """
    Format templates with provided kwargs in a single forward pass.

    For every key in templates, format the value with the given kwargs.
    Add the result as `prompt[key]` to the kwargs.

    Args:
        templates: List of dictionaries containing template strings
        formatter: Optional custom formatter to use (defaults to standard string.Formatter)
        **kwargs: Variables to use for formatting

    Returns:
        Dictionary with formatted templates
    """
    result: Dict[str, Any] = kwargs.copy()
    result["prompt"] = {}

    # Use provided formatter or default to standard Formatter
    formatter = formatter or string.Formatter()

    # Process each template dictionary in sequence
    for template_dict in templates:
        # Process each template in the current dictionary
        for key, template in template_dict.items():
            try:
                # Use the formatter instead of .format()
                formatted = formatter.format(template, **result)
                result["prompt"][key] = formatted
            except KeyError:
                pass

    return cast(FormattedPrompts, result["prompt"])


def _get_default_variables() -> Dict[str, str]:
    """
    Get default variables that should be available in all prompts.

    Returns:
        Dictionary of default variables
    """
    import os
    from .git_helpers import git_output

    return {"pwd": os.getcwd(), "branch": git_output(["branch", "--show-current"])}


class PromptTemplate:
    """
    A template for a prompt that can be formatted with arguments.
    """
    def __init__(self, prompt_id: str, factory: 'PromptFactory'):
        """
        Initialize a prompt template.
        
        Args:
            prompt_id: ID of the prompt in the template data
            factory: The PromptFactory that created this template
        """
        self.prompt_id = prompt_id
        self.factory = factory
    
    def extend(self, extend_prompt: Optional[str] = None) -> 'PromptTemplate':
        """
        Extend the prompt template with additional instructions.
        
        Args:
            extend_prompt: Additional instructions to extend the prompt
            
        Returns:
            A new prompt template with extended instructions or self if no extension
        """
        if not extend_prompt:
            return self
            
        # Create an ExtendedPromptTemplate that will apply the extension when formatted
        return ExtendedPromptTemplate(self.prompt_id, self.factory, extend_prompt)
        
    def format(self, template_args: Dict[str, str] = None) -> str:
        """
        Format this prompt template with the given arguments.
        
        Args:
            template_args: Dictionary of arguments to format the template with
            
        Returns:
            Formatted prompt string
        """
        template_args = template_args or {}
        return self.factory._eval_prompt_template(self.prompt_id, template_args)


class ExtendedPromptTemplate(PromptTemplate):
    """
    A prompt template that has been extended with additional instructions.
    """
    def __init__(self, prompt_id: str, factory: 'PromptFactory', extend_prompt: str):
        """
        Initialize an extended prompt template.
        
        Args:
            prompt_id: ID of the prompt in the template data
            factory: The PromptFactory that created this template
            extend_prompt: Additional instructions to extend the prompt
        """
        super().__init__(prompt_id, factory)
        self.extend_prompt = extend_prompt
        
    def format(self, template_args: Dict[str, str] = None) -> str:
        """
        Format this prompt template with the given arguments and apply extension.
        
        Args:
            template_args: Dictionary of arguments to format the template with
            
        Returns:
            Formatted prompt string with extension applied
        """
        template_args = template_args or {}
        
        # Format the original prompt first
        old_prompt = self.factory._eval_prompt_template(self.prompt_id, template_args)
        
        # Then use it with the extend_prompt template
        return self.factory._eval_prompt_template("extend_prompt", {
            "old_prompt": old_prompt,
            "add_prompt": self.extend_prompt
        })


# Create factory functions for prompts that return plain strings
class PromptFactory:
    def __init__(
        self, template_data: Optional[TemplateList] = None, lenient: bool = False
    ):
        """
        Initialize the PromptFactory with template data.

        Args:
            template_data: Optional list of template dictionaries. If None,
                          templates will be loaded from config.
            lenient: If True, use LenientFormatter that doesn't raise errors for missing keys
        """
        if template_data is None:
            template_data = self.from_config()
        self.template_data: TemplateList = template_data
        self.formatter = LenientFormatter() if lenient else string.Formatter()

    @staticmethod
    def from_config() -> TemplateList:
        """
        Create a template list from configuration files.

        Returns:
            List of template dictionaries from global, user, and repo configs
        """
        configs = [config.global_config, config.user_config, config.repo_config]
        return [c.get("prompts", {}) for c in configs]

    def _eval_prompt_template(self, prompt_id: str, template_args: Dict[str, str]) -> str:
        """
        Evaluate a prompt template with the given parameters.

        Args:
            prompt_id: ID of the prompt to evaluate
            template_args: Parameters to format the prompt with

        Returns:
            Formatted prompt string

        Raises:
            KeyError: If the prompt_id is not found in the formatted templates
        """
        # Add default variables if not already provided
        default_vars = _get_default_variables()
        for key, value in default_vars.items():
            if key not in template_args:
                template_args[key] = value

        formatted_prompts = apply_format(
            self.template_data, formatter=self.formatter, **template_args
        )

        # Return the requested prompt
        if prompt_id not in formatted_prompts:
            return f"<KeyError prompt[{prompt_id}]>"
        return formatted_prompts[prompt_id]

    def commit_message(self) -> PromptTemplate:
        """Generate a commit message based on provided parameters."""
        return PromptTemplate("commit_message", self)

    def commit_message_amend(self) -> PromptTemplate:
        """Generate a commit message for amending an existing commit."""
        return PromptTemplate("commit_message_amend", self)

    def branch_name(self) -> PromptTemplate:
        """Generate a branch name based on provided parameters."""
        return PromptTemplate("branch_name", self)

    def pr_description(self) -> PromptTemplate:
        """Generate a PR description based on provided parameters."""
        return PromptTemplate("pr_description", self)

    def describe_staged(self) -> PromptTemplate:
        """Generate a description of staged changes."""
        return PromptTemplate("describe_staged", self)

    def split_diff(self) -> PromptTemplate:
        """Generate instructions to split a diff into multiple commits."""
        return PromptTemplate("split_diff", self)

    def apply_patch_base(self) -> PromptTemplate:
        """Generate base instructions for applying a patch."""
        return PromptTemplate("apply_patch_base", self)

    def apply_patch_custom_instructions(self) -> PromptTemplate:
        """Generate custom instructions for applying a patch."""
        return PromptTemplate("apply_patch_custom_instructions", self)

    def apply_patch_minimal(self) -> PromptTemplate:
        """Generate minimal instructions for applying a patch."""
        return PromptTemplate("apply_patch_minimal", self)
        
    def extend_prompt_commit_metadata(self) -> PromptTemplate:
        """Extend a prompt with commit metadata."""
        return PromptTemplate("extend_prompt_commit_metadata", self)


# Create a singleton instance for backward compatibility
# Use lenient=True for backward compatibility with previous behavior
prompts = PromptFactory(lenient=True)
