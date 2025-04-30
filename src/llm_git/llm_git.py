import llm
import click

from .options import (
    model_option,
    no_edit_option,
    upstream_option,
    add_metadata_option,
    extend_prompt_option,
)
from .commands import (
    commit_command,
    apply_command,
    add_command,
    create_branch_command,
    describe_staged_command,
    dump_prompts_command,
    create_pr_command, 
    rebase_command,
    edit_rebase_todo_command,
    tag_command
)


@llm.hookimpl
def register_commands(cli):
    @cli.group(name="git")
    @model_option
    @click.pass_context
    def git_group(ctx, model):
        """Git related commands"""
        # Store model in the context object to make it available to subcommands
        ctx.ensure_object(dict)
        ctx.obj["model"] = model

    @git_group.command()
    @no_edit_option
    @click.option("--amend", "--am", is_flag=True, help="Amend the previous commit")
    @add_metadata_option
    @extend_prompt_option
    @click.option(
        "--include-prompt",
        is_flag=True,
        default=False,
        help="Include the LLM prompt (commented out) in the commit message file",
        envvar="LLM_GIT_COMMIT_INCLUDE_PROMPT",
    )
    @click.pass_context
    def commit(ctx, no_edit, amend, add_metadata, extend_prompt, include_prompt):
        """Generate commit message and commit changes"""
        model = ctx.obj.get("model")
        commit_command(no_edit, amend, model, add_metadata, extend_prompt, include_prompt)

    @git_group.command()
    @upstream_option
    @no_edit_option
    @extend_prompt_option
    @click.pass_context
    def rebase(ctx, upstream, no_edit, extend_prompt):
        """Rebase the current branch onto the upstream branch with LLM assistance"""
        model = ctx.obj.get("model")
        rebase_command(upstream, no_edit, model, extend_prompt)

    @git_group.command(name="edit-rebase-todo")
    @click.argument("rebase_todo_path", type=click.Path(exists=True))
    @no_edit_option
    @extend_prompt_option
    @click.pass_context
    def edit_rebase_todo(ctx, rebase_todo_path, no_edit, extend_prompt):
        """Edit a git rebase-todo file using the LLM"""
        model = ctx.obj.get("model")
        edit_rebase_todo_command(rebase_todo_path, no_edit, model, extend_prompt)

    @git_group.command()
    @click.argument("instructions")
    @click.option(
        "--cached", is_flag=True, help="Stage the changes after applying the patch"
    )
    @extend_prompt_option
    @click.pass_context
    def apply(ctx, instructions, cached, extend_prompt):
        """[BETA] Generate changes based on instructions (not fully functional yet)"""
        model = ctx.obj.get("model")
        apply_command(instructions, cached, model, extend_prompt)

    @git_group.command(name="add")
    @extend_prompt_option
    @click.pass_context
    def add(ctx, extend_prompt):
        """[BETA] Generate and stage fixes for your code (not fully functional yet)"""
        model = ctx.obj.get("model")
        add_command(model, extend_prompt)

    @git_group.command(name="create-branch")
    @click.argument("commit_spec", required=False)
    @click.option(
        "--preview", is_flag=True, default=False, help="Only preview the branch name without creating it"
    )
    @extend_prompt_option
    @click.pass_context
    def create_branch(ctx, commit_spec, preview, extend_prompt):
        """Generate branch name from commits and optionally create it"""
        model = ctx.obj.get("model")
        create_branch_command(commit_spec, preview, model, extend_prompt)

    @git_group.command(name="describe-staged")
    @extend_prompt_option
    @click.pass_context
    def describe_staged(ctx, extend_prompt):
        """Describe staged changes and suggest commit splits with syntax highlighting"""
        model = ctx.obj.get("model")
        describe_staged_command(model, extend_prompt)

    @git_group.command(name="dump-prompts")
    def dump_prompts():
        """Dump all available prompts"""
        dump_prompts_command()

    @git_group.command(name="tag")
    @click.argument("commit_spec", required=False)
    @click.option(
        "--preview", is_flag=True, default=False, help="Only preview the tag name without creating it"
    )
    @click.option(
        "--format", "format_type", type=click.Choice(['name', 'version']), default=None, 
        help="When using --preview, specify the output format (name: full tag name, version: version part only)"
    )
    @click.option(
        "-s", "--sign", is_flag=True, default=False, help="Create a GPG-signed tag"
    )
    @extend_prompt_option
    @click.pass_context
    def tag(ctx, commit_spec, preview, format_type, sign, extend_prompt):
        """Generate a tag name from commits and optionally create it"""
        model = ctx.obj.get("model")
        tag_command(commit_spec, preview, format_type, sign, model, extend_prompt)

    @cli.group(name="github")
    @model_option
    @click.pass_context
    def github_group(ctx, model):
        """GitHub related commands"""
        ctx.ensure_object(dict)
        ctx.obj["model"] = model

    @github_group.command(name="create-pr")
    @upstream_option
    @no_edit_option
    @extend_prompt_option
    @click.pass_context
    def create_pr(ctx, upstream, no_edit, extend_prompt):
        """Generate PR description from commits"""
        model = ctx.obj.get("model")
        create_pr_command(upstream, no_edit, model, extend_prompt)

