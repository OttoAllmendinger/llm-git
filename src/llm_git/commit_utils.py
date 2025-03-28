from .prompts import prompts
from typing import Dict, Any, Optional

def add_metadata_to_message(msg, metadata):
    """
    Add metadata to a commit message if it's not already there.
    
    Args:
        msg (str): The commit message
        metadata (str): The metadata to add
        
    Returns:
        str: The commit message with metadata added
    """
    # Add the metadata as a trailer if it's not already there
    if metadata not in msg:
        # Make sure there's a blank line before the trailer
        if not msg.endswith("\n\n"):
            if msg.endswith("\n"):
                msg += "\n"
            else:
                msg += "\n\n"
        msg += metadata
    
    return msg

def extend_with_metadata(prompt_template, extend_prompt=None, add_metadata=False, format_args=None):
    """
    Extend a prompt template with metadata and additional instructions.
    
    Args:
        prompt_template: The base prompt template to extend
        extend_prompt: Additional instructions to extend the prompt
        add_metadata: Whether to add metadata to the commit message
        format_args: Arguments to format the prompt template with
        
    Returns:
        Formatted prompt string with extensions applied
    """
    # First extend with the user's additional instructions if provided
    extended = prompt_template.extend(extend_prompt) if extend_prompt else prompt_template
    
    # Format the prompt with the provided arguments
    format_args = format_args or {}
    formatted = extended.format(format_args)
    
    # Then add metadata if requested
    if add_metadata:
        # Use the extend_prompt_commit_metadata template to add metadata
        return prompts.extend_prompt_commit_metadata().format({"old_prompt": formatted})
    
    return formatted
