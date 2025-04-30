import os
import json
import subprocess
from .config import merged_config


def git_output(full_cmd, *args, **kwargs):
    """Run a git command and return its output"""
    full_cmd = ["git"] + full_cmd
    full_cmd = [str(arg) for arg in full_cmd]

    debug = os.environ.get("LLM_GIT_SHOW_COMMAND", "0") == "1"
    if debug:
        print(f"Running command: {' '.join(full_cmd)}")

    try:
        result = subprocess.run(
            full_cmd, check=True, capture_output=True, text=True, *args, **kwargs
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        error_str = json.dumps(
            {
                "cmd": e.cmd,
                "returncode": e.returncode,
                "stdout": e.stdout,
                "stderr": e.stderr,
            }
        )
        raise Exception(error_str)


def git_interactive(cmd):
    """Execute a git command that requires interactive input (like editor)"""
    full_cmd = ["git"] + cmd
    # Use subprocess.run with shell=False and pass through stdin/stdout/stderr
    # to allow proper terminal interaction for editors
    result = subprocess.run(full_cmd, check=True)
    return result


def get_origin_default_branch():
    """Get the default branch from the origin remote (what origin/HEAD points to)"""
    remote_prefix = "refs/remotes/origin"
    symbolic_ref = git_output(["symbolic-ref", f"{remote_prefix}/HEAD"])
    # Extract the branch name from the symbolic ref
    if symbolic_ref.startswith(remote_prefix):
        return "origin" + symbolic_ref[len(remote_prefix) :]

    raise Exception(f"Invalid symbolic ref: {symbolic_ref}")


def get_merge_base(branch1, branch2):
    return git_output(["merge-base", branch1, branch2])


def get_latest_tag():
    """Get the most recent tag reachable from HEAD"""
    try:
        # --tags: Consider all tags, not just annotated ones
        # --abbrev=0: Output the full tag name without abbreviation
        # --always: If no tags are found, output the unique commit hash instead
        # We check the output to see if it's a tag or just a commit hash fallback
        tag_or_hash = git_output(["describe", "--tags", "--abbrev=0", "--always"])
        
        # Check if the output is actually a tag by seeing if it exists in the tag list
        all_tags = git_output(["tag", "-l"]).splitlines()
        if tag_or_hash in all_tags:
            return tag_or_hash
        else:
            # No reachable tag found, describe returned a commit hash
            return None
            
    except Exception as e:
        # Handle cases where git describe fails (e.g., empty repo)
        # Check if the error indicates no names found
        if "fatal: No names found" in str(e):
            return None
        raise e


def get_default_exclude_files():
    """Get the default list of files to exclude from diffs and shows
    
    Returns:
        list: Default files to exclude
        
    Raises:
        Exception: If exclude_files is not found in the config
    """
    config = merged_config()
    git_config = config.get("git", {})
    
    # Get exclude_files from config
    exclude_files = git_config.get("exclude_files")
    
    # If the config doesn't have exclude_files, raise an exception
    if exclude_files is None:
        raise Exception("exclude_files not found in config")
    
    return exclude_files


def get_diff(exclude_files=None, staged=False, base=None):
    """Get git diff of changes
    
    Args:
        exclude_files (list): Files to exclude from the diff
        staged (bool): Whether to show staged changes
        base (str): Optional base commit to diff against
    """
    if exclude_files is None:
        exclude_files = get_default_exclude_files()

    cmd = ["diff", "--unified=10"]
    
    if base:
        cmd.append(base)
        
    if staged:
        cmd.append("--staged")

    for f in exclude_files:
        cmd.append(f":(exclude){f}")
    return git_output(cmd)


def git_show(commit="HEAD", exclude_files=None, format=None, oneline=False, **kwargs):
    """Get git show output for a commit
    
    Args:
        commit (str): The commit to show (default: HEAD)
        exclude_files (list): Files to exclude from the output
        format (str): Optional format string for git show (e.g. "%B", "%H", "fuller")
        oneline (bool): Whether to use --oneline flag
        **kwargs: Additional arguments to pass to git show
        
    Returns:
        str: The git show output
    """
    if exclude_files is None:
        exclude_files = get_default_exclude_files()

    cmd = ["show"]
    
    # Add format if specified
    if format:
        cmd.append(f"--format={format}")
    
    # Add oneline flag if specified
    if oneline:
        cmd.append("--oneline")
    
    # Add unified diff context size
    cmd.append("--unified=10")
    
    # Add the commit
    cmd.append(commit)
    
    # Add exclude patterns
    for f in exclude_files:
        cmd.append(f":(exclude){f}")
        
    # Add any additional arguments
    for key, value in kwargs.items():
        if len(key) == 1:
            cmd.append(f"-{key}")
        else:
            cmd.append(f"--{key.replace('_', '-')}")
        
        if value is not True:  # Skip value for boolean flags
            cmd.append(str(value))
            
    return git_output(cmd)


def get_diff_for_commit_message(amend=False):
    """
    Get the appropriate diff for generating a commit message.
    
    Args:
        amend (bool): If True, get the diff between HEAD^ and the index (staged),
                     which includes both the commit being amended and any new staged changes.
                     If False, get the staged diff.
    
    Returns:
        str: The diff content
    """
    if amend:
        # For amend, compare HEAD^ with staged changes
        return get_diff(staged=True, base="HEAD^")
    else:
        # For regular commits, just get the staged diff
        return get_diff(staged=True)


def build_commit_args(is_amend=False, no_edit=False, file_path=None):
    """Build git commit command arguments with appropriate flags"""
    cmd = ["commit"]
    if is_amend:
        cmd.append("--amend")
    if not no_edit:
        cmd.append("--edit")
    if file_path:
        cmd.extend(["-F", file_path])
        # Add --cleanup=strip to remove comments and trailing spaces
        cmd.append("--cleanup=strip")
    return cmd

