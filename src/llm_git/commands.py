import sys
import subprocess
import yaml
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
    git_show,
    get_latest_tag, # Import the new helper
)
from .file_helpers import (
    temp_file_with_content,
    edit_with_editor, # Import edit_with_editor
)
from .llm_utils import LLMRequest
from .terminal_format import console, markdown, syntax
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
        current_msg = git_show(format="%B")
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
        formatter=markdown()
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


def rebase_command(upstream, no_edit, model, extend_prompt=None):
    """
    Rebase the current branch onto the upstream branch with LLM assistance
    """
    import os
    import subprocess
    import sys
    
    if upstream is None:
        upstream = get_origin_default_branch()
    
    # Get the path to the llm-git executable
    llm_git_path = sys.argv[0]
    
    # Set the GIT_SEQUENCE_EDITOR environment variable to use our command
    env = os.environ.copy()
    env["GIT_SEQUENCE_EDITOR"] = f"{llm_git_path} git edit-rebase-todo"
    
    if model:
        env["GIT_SEQUENCE_EDITOR"] += f" --model {model}"
    
    if extend_prompt:
        env["GIT_SEQUENCE_EDITOR"] += f" --extend-prompt '{extend_prompt}'"
    
    if no_edit:
        env["GIT_SEQUENCE_EDITOR"] += " --no-edit"
    
    try:
        # Run git rebase with our custom editor
        subprocess.run(["git", "rebase", "-i", upstream], env=env, check=True)
    except subprocess.CalledProcessError:
        click.echo("Rebase failed. Resolve conflicts and continue with 'git rebase --continue'")


def edit_rebase_todo_command(rebase_todo_path, no_edit, model, extend_prompt=None):
    """
    Edit a git rebase-todo file using the LLM
    """
    from llm.utils import extract_fenced_code_block
    import os
    import subprocess
    
    # Read the rebase-todo file
    with open(rebase_todo_path, 'r') as f:
        rebase_todo = f.read()
    
    # Get the commit history for context
    # Extract the commit hashes from the rebase-todo
    import re
    commit_hashes = re.findall(r'^\w+\s+([a-f0-9]+)', rebase_todo, re.MULTILINE)
    
    # Get the commit details for context
    commit_details = ""
    for commit_hash in commit_hashes:
        commit_details += git_show(commit=commit_hash, format="fuller") + "\n\n"
    
    # Format the input data using the template
    input_data = {
        "rebase_plan": rebase_todo,
        "commit_details": commit_details
    }
    
    # Call the LLM to improve the rebase plan using templates from config
    request = LLMRequest(
        prompt=prompts.rebase_input().format(input_data),  # Input data formatted with template
        system_prompt=prompts.improve_rebase_plan().extend(extend_prompt).format(),  # Instructions from template
        model_id=model,
        stream=True,
        formatter=syntax("git")
    )
    
    result = request.execute()
    improved_plan = str(result)
    
    # Extract the improved rebase plan from the LLM response
    # The LLM might wrap the plan in markdown code blocks, so we need to extract it
    improved_plan = extract_fenced_code_block(improved_plan) or improved_plan
    
    # Write the improved plan back to the file
    with open(rebase_todo_path, 'w') as f:
        f.write(improved_plan)
    
    # If no_edit is False, open the editor for manual review
    if not no_edit:
        # Use the user's preferred editor
        editor = os.environ.get('EDITOR', 'vim')
        subprocess.run([editor, rebase_todo_path])


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
        formatter=syntax("diff") if output_type == "diff" else markdown()
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
        log = git_show(commit=commit_spec, format="fuller", oneline=True)

    request = LLMRequest(
        prompt=log,
        system_prompt=prompts.branch_name().extend(extend_prompt).format(),
        model_id=model,
        stream=True,
        formatter=markdown()
    )
    result = request.execute()
    branch_name_result = str(result).strip()

    if not preview:
        git_output(["checkout", "-b", branch_name_result])
    else:
        click.echo(branch_name_result)


def tag_command(commit_spec, preview, format_type, sign, no_edit, model, extend_prompt=None):
    """Generate a tag name and message from commits and optionally create an annotated tag"""
    if commit_spec is None:
        latest_tag = get_latest_tag()
        if latest_tag:
            commit_spec = f"{latest_tag}..HEAD"
            click.echo(f"Using commit range from latest tag: {commit_spec}", err=True)
        else:
            # Fallback if no tags are found
            default_branch = get_origin_default_branch()
            merge_base = get_merge_base(default_branch, "HEAD")
            commit_spec = f"{merge_base}..HEAD"
            click.echo(f"No tags found. Using commit range from merge-base with {default_branch}: {commit_spec}", err=True)

    if ".." in commit_spec:
        # Use --no-merges to simplify the log for the LLM
        log = git_output(["log", "--oneline", "--no-merges", commit_spec, "--format=fuller"])
    else:
        log = git_show(commit=commit_spec, format="fuller", oneline=True)

    request = LLMRequest(
        prompt=log,
        system_prompt=prompts.tag_name().extend(extend_prompt).format(),
        model_id=model,
        stream=True, # Keep streaming for responsiveness during generation
        formatter=markdown() # Keep markdown for potential formatting in message
    )
    result = request.execute()
    
    # Combine tag name and message for potential editing
    generated_output = str(result).strip()
    
    # Parse the generated result initially
    output_lines = generated_output.split('\n', 1)
    tag_name_result = output_lines[0].strip()
    tag_message_result = output_lines[1].strip() if len(output_lines) > 1 else f"Tag {tag_name_result}" # Default message if none provided

    if preview:
        if format_type == 'name':
            # Output only the tag name without a trailing newline
            click.echo(tag_name_result, nl=False)
        elif format_type == 'version':
            # Output only the version part (remove leading 'v' if present)
            version_part = tag_name_result
            if version_part.startswith('v'):
                version_part = version_part[1:]
            click.echo(version_part, nl=False)
        else:
            # Default preview output (name and message)
            click.echo(f"Generated Tag Name:\n{tag_name_result}\n")
            click.echo(f"Generated Tag Message:\n{tag_message_result}")
    else:
        # Allow editing unless --no-edit is specified
        if not no_edit:
            # Use the combined generated output for editing
            edited_output = edit_with_editor(generated_output)
            # Re-parse after editing
            edited_lines = edited_output.strip().split('\n', 1)
            tag_name_result = edited_lines[0].strip()
            tag_message_result = edited_lines[1].strip() if len(edited_lines) > 1 else f"Tag {tag_name_result}"
        
        # Create the tag using the (potentially edited) name and message
        cmd = ["tag"]
        if sign:
            cmd.append("-s") # Sign the tag
        # Use -a for annotated tag and -m for message
        cmd.extend(["-a", tag_name_result, "-m", tag_message_result])
        git_output(cmd)
        click.echo(f"Created tag '{tag_name_result}'")


def describe_staged_command(model, extend_prompt=None):
    """Describe staged changes and suggest commit splits with syntax highlighting"""
    diff = get_diff(staged=True)

    # Display the diff with syntax highlighting first
    console.print("Staged changes:", style="bold green")
    console.print(syntax("diff").render(diff))
    console.print("\nAnalyzing changes...\n", style="bold yellow")

    # Then run the LLM with formatted output
    request = LLMRequest(
        prompt=diff,
        system_prompt=prompts.describe_staged().extend(extend_prompt).format(),
        model_id=model,
        stream=True,
        formatter=markdown()
    )
    request.execute()


def dump_config_command():
    """Dump the current merged configuration"""
    config = merged_config()
    # Use yaml.dump to format the config dictionary
    config_yaml = yaml.dump(config, default_flow_style=False, sort_keys=False)
    console.print("Current merged configuration:", style="bold green")
    # Print with YAML syntax highlighting
    console.print(syntax("yaml", line_numbers=False).render(config_yaml))


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
            console.print(syntax("markdown", line_numbers=False).render(result))
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
        formatter=markdown()
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

