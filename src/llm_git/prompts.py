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

    def _eval_prompt_template(self, prompt_id: str, kwargs: Dict[str, Any]) -> str:
        """
        Evaluate a prompt template with the given parameters.

        Args:
            prompt_id: ID of the prompt to evaluate
            kwargs: Parameters to format the prompt with

        Returns:
            Formatted prompt string

        Raises:
            KeyError: If the prompt_id is not found in the formatted templates
        """
        # Add default variables if not already provided
        default_vars = _get_default_variables()
        for key, value in default_vars.items():
            if key not in kwargs:
                kwargs[key] = value

        formatted_prompts = apply_format(
            self.template_data, formatter=self.formatter, **kwargs
        )

        # Return the requested prompt
        if prompt_id not in formatted_prompts:
            return f"<KeyError prompt[{prompt_id}]>"
        return formatted_prompts[prompt_id]

    def commit_message(self, **kwargs: Any) -> str:
        """Generate a commit message based on provided parameters."""
        return self._eval_prompt_template("commit_message", kwargs)

    def branch_name(self, **kwargs: Any) -> str:
        """Generate a branch name based on provided parameters."""
        return self._eval_prompt_template("branch_name", kwargs)

    def pr_description(self, **kwargs: Any) -> str:
        """Generate a PR description based on provided parameters."""
        return self._eval_prompt_template("pr_description", kwargs)

    def describe_staged(self, **kwargs: Any) -> str:
        """Generate a description of staged changes."""
        return self._eval_prompt_template("describe_staged", kwargs)

    def split_diff(self, **kwargs: Any) -> str:
        """Generate instructions to split a diff into multiple commits."""
        return self._eval_prompt_template("split_diff", kwargs)

    def apply_patch_base(self, **kwargs: Any) -> str:
        """Generate base instructions for applying a patch."""
        return self._eval_prompt_template("apply_patch_base", kwargs)

    def apply_patch_custom_instructions(self, **kwargs: Any) -> str:
        """Generate custom instructions for applying a patch."""
        return self._eval_prompt_template("apply_patch_custom_instructions", kwargs)

    def apply_patch_minimal(self, **kwargs: Any) -> str:
        """Generate minimal instructions for applying a patch."""
        return self._eval_prompt_template("apply_patch_minimal", kwargs)


# Create a singleton instance for backward compatibility
# Use lenient=True for backward compatibility with previous behavior
prompts = PromptFactory(lenient=True)
