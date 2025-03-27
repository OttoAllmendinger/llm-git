import sys
import subprocess
from llm.utils import extract_fenced_code_block
import click

from .prompts import prompts
from .git_helpers import (
    git_output,
    get_diff,
    get_staged_diff,
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


LLM_GIT_URL = "https://github.com/OttoAllmendinger/llm-git"

def commit_command(no_edit, amend, model, add_metadata=None):
    """Generate commit message and commit changes"""
    diff = get_staged_diff() if not amend else ""

    if amend:
        # For amend, use the current commit message as input
        current_msg = git_output(["show", "--format=%B", "-s"])
        input_text = current_msg
    else:
        # For new commit, use the diff as input and get previous commit message
        input_text = diff

    request = LLMRequest(
        prompt=input_text,
        system_prompt=prompts.commit_message(),
        model_id=model,
        stream=True,
        output_type="markdown"
    )
    result = request.execute()
    msg = str(result)

    # Check if we should add metadata
    config = merged_config()
    commit_config = config.get("commit", {})
    
    # Command-line option overrides config if provided
    should_add_metadata = add_metadata if add_metadata is not None else commit_config.get("add_metadata", True)
    
    if should_add_metadata:
        # Get the metadata format and fill in the model_id
        metadata_format = commit_config.get(
            "metadata_format", 
            "Co-authored-by: llm-git <llm-git@ttll.de>"
        )
        model_name = model or "default"
        metadata = metadata_format.format(model_id=model_name)
        
        # Add the metadata as a trailer if it's not already there
        if metadata not in msg:
            # Make sure there's a blank line before the trailer
            if not msg.endswith("\n\n"):
                if msg.endswith("\n"):
                    msg += "\n"
                else:
                    msg += "\n\n"
            msg += metadata

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


def apply_command(instructions, cached, model):
    if sys.stdin.isatty():
        input_text = get_diff()
    else:
        input_text = sys.stdin.read()

    _apply(
        model,
        input_text,
        prompts.apply_patch_custom_instructions(instructions=instructions),
        cached,
        output_type="diff"
    )


def add_command(model):
    # Use the apply_patch_minimal prompt directly
    _apply(model, get_diff(), prompts.apply_patch_minimal(), True, output_type="diff")


def create_branch_command(commit_spec, preview, model):
    """Generate branch name from commits and optionally create it"""
    if commit_spec is None:
        commit_spec = get_merge_base(get_origin_default_branch(), "HEAD") + "..HEAD"

    if ".." in commit_spec:
        log = git_output(["log", "--oneline", commit_spec, "--format=fuller"])
    else:
        log = git_output(["show", "--oneline", commit_spec, "--format=fuller"])

    request = LLMRequest(
        prompt=log,
        system_prompt=prompts.branch_name(),
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


def describe_staged_command(model):
    """Describe staged changes and suggest commit splits with syntax highlighting"""
    diff = get_staged_diff()

    # Display the diff with syntax highlighting first
    console.print("Staged changes:", style="bold green")
    console.print(highlight_diff(diff))
    console.print("\nAnalyzing changes...\n", style="bold yellow")

    # Then run the LLM with formatted output
    request = LLMRequest(
        prompt=diff,
        system_prompt=prompts.describe_staged(),
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
            result = method()

            # Display the formatted prompt
            console.print(highlight_code(result, "markdown"))
        except Exception:
            # console.print(f"[red]Error rendering prompt: {str(e)}[/red]")
            # print with stack trace
            console.print_exception()


def create_pr_command(upstream, no_edit, model):
    """Generate PR description from commits"""
    if upstream is None:
        upstream = get_origin_default_branch()

    range_base = git_output(["merge-base", "HEAD", upstream])
    commit_range = f"{range_base}..HEAD"

    log = git_output(["log", commit_range])

    request = LLMRequest(
        prompt=log,
        system_prompt=prompts.pr_description(),
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
