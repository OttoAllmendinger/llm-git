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


def get_diff(exclude_files=None, staged=False):
    """Get git diff of changes"""
    if exclude_files is None:
        exclude_files = ["package-lock.json", "yarn.lock"]

    cmd = ["diff", "--unified=10"]
    if staged:
        cmd.append("--staged")

    for f in exclude_files:
        cmd.append(f":(exclude){f}")
    return git_output(cmd)


def get_staged_diff(exclude_files=None):
    """Get git diff of staged changes"""
    return get_diff(exclude_files, staged=True)


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
