import llm
import click

from .options import (
    model_option,
    no_edit_option,
    upstream_option,
    add_metadata_option,
)
from .commands import (
    commit_command,
    apply_command,
    add_command,
    create_branch_command,
    describe_staged_command,
    dump_prompts_command,
    create_pr_command,
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
    @click.pass_context
    def commit(ctx, no_edit, amend, add_metadata):
        """Generate commit message and commit changes"""
        model = ctx.obj.get("model")
        commit_command(no_edit, amend, model, add_metadata)

    @git_group.command()
    @click.argument("instructions")
    @click.option(
        "--cached", is_flag=True, help="Stage the changes after applying the patch"
    )
    @click.pass_context
    def apply(ctx, instructions, cached):
        """[BETA] Generate changes based on instructions (not fully functional yet)"""
        model = ctx.obj.get("model")
        apply_command(instructions, cached, model)

    @git_group.command(name="add")
    @click.pass_context
    def add(ctx):
        """[BETA] Generate and stage fixes for your code (not fully functional yet)"""
        model = ctx.obj.get("model")
        add_command(model)

    @git_group.command(name="create-branch")
    @click.argument("commit_spec", required=False)
    @click.option(
        "--preview", is_flag=True, default=False, help="Only preview the branch name without creating it"
    )
    @click.pass_context
    def create_branch(ctx, commit_spec, preview):
        """Generate branch name from commits and optionally create it"""
        model = ctx.obj.get("model")
        create_branch_command(commit_spec, preview, model)

    @git_group.command(name="describe-staged")
    @click.pass_context
    def describe_staged(ctx):
        """Describe staged changes and suggest commit splits with syntax highlighting"""
        model = ctx.obj.get("model")
        describe_staged_command(model)

    @git_group.command(name="dump-prompts")
    def dump_prompts():
        """Dump all available prompts"""
        dump_prompts_command()

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
    @click.pass_context
    def create_pr(ctx, upstream, no_edit):
        """Generate PR description from commits"""
        model = ctx.obj.get("model")
        create_pr_command(upstream, no_edit, model)
