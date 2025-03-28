import sys
import subprocess
from llm.utils import extract_fenced_code_block
import click

from .prompts import prompts
from .git_helpers import (
    git_output,
    get_diff,
    get_diff_for_commit_message,
    build_commit_args,
    git_interactive,
    get_origin_default_branch,
    get_merge_base,
)
from .file_helpers import (
    temp_file_with_content,
    edit_with_editor,
)
from .llm_utils import LLMRequest
from .terminal_format import console, highlight_code, highlight_diff
from .config import merged_config
from .commit_utils import extend_with_metadata


def commit_command(no_edit, amend, model, add_metadata=None, extend_prompt=None, include_prompt=False):
    """Generate commit message and commit changes"""
    
    # Get the appropriate diff for the commit message
    diff = get_diff_for_commit_message(amend=amend)
    
    # Check if we should add metadata
    config = merged_config()
    commit_config = config.get("commit", {})
    
    # Command-line option overrides config if provided
    should_add_metadata = add_metadata if add_metadata is not None else commit_config.get("add_metadata", True)
    
    # Select the appropriate prompt template and format args based on whether we're amending
    format_args = {}
    if amend:
        # Get the current commit message for amend
        current_msg = git_output(["show", "--format=%B", "-s"])
        prompt_template = prompts.commit_message_amend()
        format_args["previous_message"] = current_msg
    else:
        prompt_template = prompts.commit_message()
    
    # Apply extensions and metadata in a single call
    system_prompt = extend_with_metadata(
        prompt_template,
        extend_prompt,
        should_add_metadata,
        format_args
    )
    
    # Create a single request with the appropriate system prompt
    request = LLMRequest(
        prompt=diff,
        system_prompt=system_prompt,
        model_id=model,
        stream=True,
        output_type="markdown"
    )
    
    result = request.execute()
    msg = str(result)

    # If include_prompt is True, add the commented-out prompt to the message
    if include_prompt and not no_edit:
        # Format the prompt as comments (each line starting with #)
        commented_prompt = "\n".join(f"# {line}" for line in system_prompt.split("\n"))
        # Add a separator
        prompt_section = f"\n\n# ----- LLM PROMPT (WILL BE REMOVED) -----\n{commented_prompt}\n# ----- END LLM PROMPT -----\n"
        # Append to the message
        msg += prompt_section

    with temp_file_with_content(msg) as file_path:
        cmd = build_commit_args(
            is_amend=amend, no_edit=no_edit, file_path=str(file_path)
        )
        git_interactive(cmd)


def _apply(model, input_text, prompt_text, cached=False, output_type="diff"):
    def apply_patch(input):
        patch = extract_fenced_code_block(input, last=True)
        if not patch:
            click.echo("apply_patch result:")
            click.echo(input, err=True)
            raise Exception("No patch found in the output")
        with temp_file_with_content(patch) as file_path:
            cmd = ["apply"]
            if cached:
                cmd.append("--cached")
            cmd.append(file_path)
            git_output(cmd)

    request = LLMRequest(
        prompt=f"Result of `git diff`:\n```\n{input_text}\n```",
        system_prompt=prompt_text,
        model_id=model,
        stream=True,
        output_type=output_type
    )
    request.with_retry(apply_patch)


def apply_command(instructions, cached, model, extend_prompt=None):
    if sys.stdin.isatty():
        input_text = get_diff()
    else:
        input_text = sys.stdin.read()

    _apply(
        model,
        input_text,
        prompts.apply_patch_custom_instructions().extend(extend_prompt).format({"instructions": instructions}),
        cached,
        output_type="diff"
    )


def add_command(model, extend_prompt=None):
    # Use the apply_patch_minimal prompt directly
    _apply(
        model, 
        get_diff(), 
        prompts.apply_patch_minimal().extend(extend_prompt).format(), 
        True, 
        output_type="diff"
    )


def create_branch_command(commit_spec, preview, model, extend_prompt=None):
    """Generate branch name from commits and optionally create it"""
    if commit_spec is None:
        commit_spec = get_merge_base(get_origin_default_branch(), "HEAD") + "..HEAD"

    if ".." in commit_spec:
        log = git_output(["log", "--oneline", commit_spec, "--format=fuller"])
    else:
        log = git_output(["show", "--oneline", commit_spec, "--format=fuller"])

    request = LLMRequest(
        prompt=log,
        system_prompt=prompts.branch_name().extend(extend_prompt).format(),
        model_id=model,
        stream=True,
        output_type="markdown"
    )
    result = request.execute()
    branch_name_result = str(result).strip()

    if not preview:
        git_output(["checkout", "-b", branch_name_result])
    else:
        click.echo(branch_name_result)


def describe_staged_command(model, extend_prompt=None):
    """Describe staged changes and suggest commit splits with syntax highlighting"""
    diff = get_diff(staged=True)

    # Display the diff with syntax highlighting first
    console.print("Staged changes:", style="bold green")
    console.print(highlight_diff(diff))
    console.print("\nAnalyzing changes...\n", style="bold yellow")

    # Then run the LLM with formatted output
    request = LLMRequest(
        prompt=diff,
        system_prompt=prompts.describe_staged().extend(extend_prompt).format(),
        model_id=model,
        stream=True,
        output_type="markdown"
    )
    request.execute()


def dump_prompts_command():
    """Dump all available prompts"""
    import inspect
    from .prompts import prompts, PromptFactory

    # Get all methods from PromptFactory that don't start with underscore
    prompt_methods = [
        name
        for name, method in inspect.getmembers(
            PromptFactory(None, lenient=True), predicate=inspect.ismethod
        )
        if not name.startswith("_")
    ]

    # Display the available prompts
    console.print("Available prompts:", style="bold green")

    for method_name in sorted(prompt_methods):
        # Skip __init__ and other special methods
        if method_name.startswith("__"):
            continue

        console.print(f"\n[bold cyan]{method_name}[/bold cyan]")

        # Call the method on the prompts instance
        try:
            # Get the method from the prompts instance
            method = getattr(prompts, method_name)

            # Call the method with empty kwargs
            result = method().format()

            # Display the formatted prompt
            console.print(highlight_code(result, "markdown"))
        except Exception:
            # console.print(f"[red]Error rendering prompt: {str(e)}[/red]")
            # print with stack trace
            console.print_exception()


def create_pr_command(upstream, no_edit, model, extend_prompt=None):
    """Generate PR description from commits"""
    if upstream is None:
        upstream = get_origin_default_branch()

    range_base = git_output(["merge-base", "HEAD", upstream])
    commit_range = f"{range_base}..HEAD"

    log = git_output(["log", commit_range])

    request = LLMRequest(
        prompt=log,
        system_prompt=prompts.pr_description().extend(extend_prompt).format(),
        model_id=model,
        stream=True,
        output_type="markdown"
    )
    result = request.execute()
    pr_desc = str(result)

    if not no_edit:
        pr_desc = edit_with_editor(pr_desc)

    # Split the first line as title and the rest as body
    lines = pr_desc.splitlines()
    title = lines[0] if lines else ""
    body = "\n".join(lines[1:]) if len(lines) > 1 else ""

    # Create a temporary file for the body
    with temp_file_with_content(body) as body_file:
        # Use GitHub CLI to create PR
        subprocess.run(
            [
                "gh",
                "pr",
                "create",
                "--draft",
                "--title",
                title,
                "--body-file",
                body_file,
            ]
        )
