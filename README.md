# LLM Git

AI-powered Git commands for your command line. LLM Git enhances your Git workflow with AI assistance for commit messages, branch naming, PR descriptions, and more.

A plugin for the [LLM](https://llm.datasette.io/) command-line tool.

## Overview

LLM Git provides a suite of commands that use AI to help with common Git tasks:

- Generate meaningful commit messages based on your changes
- Create descriptive branch names from commit history
- Write comprehensive PR descriptions
- Analyze and describe staged changes
- Generate fixes for your code
- Improve interactive rebases with AI assistance

## Installation

```bash
llm install git+https://github.com/OttoAllmendinger/llm-git.git
```

## Quick Usage

```bash
# Generate a commit message and commit your staged changes
llm git commit

# Generate a branch name based on your recent commits and create it
llm git create-branch

# Create a PR with generated description
llm github create-pr

# Get an analysis of your staged changes
llm git describe-staged

# Generate changes to your code based on instructions
llm git apply "fix the bugs in this code"

# Perform an interactive rebase with AI assistance
llm git rebase HEAD~5
```

## Commands

### Git Commands

- `llm git [--model MODEL] commit [--no-edit] [--amend] [--add-metadata] [--extend-prompt TEXT] [--include-prompt]` - Generate commit message and commit changes
- `llm git [--model MODEL] rebase [--upstream BRANCH] [--no-edit] [--extend-prompt TEXT] [--onto BRANCH]` - Rebase the current branch with AI assistance
- `llm git [--model MODEL] create-branch [COMMIT_SPEC] [--preview] [--extend-prompt TEXT]` - Generate branch name from commits and create it
- `llm git [--model MODEL] describe-staged [--extend-prompt TEXT]` - Describe staged changes with suggestions
- `llm git [--model MODEL] apply INSTRUCTIONS [--cached] [--extend-prompt TEXT]` - [BETA] Generate changes based on instructions (not fully functional yet)
- `llm git [--model MODEL] add [--extend-prompt TEXT]` - [BETA] Generate and stage fixes (not fully functional yet)
- `llm git dump-prompts` - Display all available prompts

### GitHub Commands

- `llm github [--model MODEL] create-pr [--upstream BRANCH] [--no-edit] [--extend-prompt TEXT]` - Generate PR description from commits

## Prompts

LLM Git uses a flexible prompt system that allows you to customize how the AI generates content. Prompts are loaded from three different sources, in order of increasing precedence:

1. **Global config**: Built-in default prompts in `src/llm_git/config.yaml`
2. **User config**: Your personal customizations in `~/.config/llm-git/config.yaml`
3. **Repository config**: Project-specific settings in `.llm-git.yaml` at the root of your Git repository

### Extending Prompts

The key feature of LLM Git's prompt system is the ability to extend prompts from higher-level configs. When you define a prompt with the same name in your user or repository config, you can reference the original prompt using `{prompt[prompt_name]}` and then add your own customizations.

Here's a simplified example showing how to extend the `commit_message` prompt:

**1. Global config (built-in defaults):**
```yaml
prompts:
  assistant_intro: |
    # Git Assistant
    You are a git assistant.
    Line length for text output is 72 characters.
  
  commit_message: |
    {prompt[assistant_intro]}
    
    ## Writing Style
    - Use the imperative mood
    - Be terse and concise
    
    ## Output
    Only output the commit message.
```

**2. User config (`~/.config/llm-git/config.yaml`):**
```yaml
prompts:
  commit_message: |
    {prompt[commit_message]}
    
    ## User Preferences
    - Always include a brief explanation of WHY the change was made
    - Use conventional commits format (feat, fix, docs, etc.)
```

**3. Repository config (`.llm-git.yaml`):**
```yaml
prompts:
  commit_message: |
    {prompt[commit_message]}
    
    ## Project-Specific Requirements
    - Reference ticket numbers in the format PROJ-123
    - Always mention affected components
```

When LLM Git processes the `commit_message` prompt, it will:
1. Start with the global `commit_message`
2. Extend it with the user's preferences
3. Further extend it with the repository-specific requirements

This approach allows you to build on existing prompts rather than having to redefine them completely, making customization more modular and maintainable.

### Available Prompts

You can view all available prompts and their current values by running:

```bash
llm git dump-prompts
```

## Environment Variables

- `LLM_GIT_SHOW_PROMPTS=1` - Show prompts sent to the LLM
- `LLM_GIT_ABORT=request` - Abort before sending request to LLM
- `LLM_GIT_KEEP_TEMP_FILES=1` - Keep temporary files for debugging
- `LLM_GIT_COMMIT_INCLUDE_PROMPT=1` - Include the LLM prompt (commented out) in the commit message file
