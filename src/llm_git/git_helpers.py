import json
import subprocess


def git_output(cmd, *args, **kwargs):
    """Run a git command and return its output"""
    full_cmd = ["git"] + cmd
    full_cmd = [str(arg) for arg in full_cmd]
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


def get_diff(exclude_files=None, staged=False, base=None):
    """Get git diff of changes
    
    Args:
        exclude_files (list): Files to exclude from the diff
        staged (bool): Whether to show staged changes
        base (str): Optional base commit to diff against
    """
    if exclude_files is None:
        exclude_files = ["package-lock.json", "yarn.lock"]

    cmd = ["diff", "--unified=10"]
    
    if base:
        cmd.append(base)
        
    if staged:
        cmd.append("--staged")

    for f in exclude_files:
        cmd.append(f":(exclude){f}")
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
    return cmd
