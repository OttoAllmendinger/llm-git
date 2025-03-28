import click


def model_option(f):
    return click.option(
        "--model",
        "-m",
        help="Model to use for this command",
    )(f)


def no_edit_option(f):
    return click.option(
        "--no-edit",
        is_flag=True,
        help="Skip editing the message",
    )(f)


def upstream_option(f):
    return click.option(
        "--upstream",
        "-u",
        help="Upstream branch to compare against",
    )(f)


def add_metadata_option(f):
    return click.option(
        "--add-metadata/--no-add-metadata",
        is_flag=True,
        default=None,
        help="Add LLM-Git metadata to commit message as Co-Authored-By trailer",
    )(f)


def extend_prompt_option(f):
    return click.option(
        "--extend-prompt", "-X",
        help="Additional instructions to extend the prompt",
    )(f)
