# Commands


# Rebase

 - reorder support using GIT_SEQUENCE_EDITOR
 - squash support
 - split support
 - rewrite support

# Better Git Apply

- improve `git apply` support
  - don't edit diffs: instead show old code, new code and output alternative new code instead


# Testing

- high level test runs for each command
  - create sample git repo
  - create sample changes
  - generate test fixtures (capture sample llm responses for prompts)
  - regenerate test fixtures when prompts change