# Wiring the agent up, start to finish

`docs/AGENT.md` is the architecture. This is the click-by-click, and the honest cost.

## Do this first, before any agent exists

The **6. Provider watch** workflow already does the part that does not need intelligence: every
Monday it re-reads all fourteen providers' patch lists with `-x -u` and opens one issue if any
patch name appeared or disappeared. No API key, no quota, no model.

Run it once by hand today so it has a baseline:

    gh workflow run agent-watch.yml

Live with that for two weeks before adding an agent. You may find the issue is enough on its own,
in which case you have saved yourself a whole moving part. If it is not enough, the issue becomes
the agent's task input, which is a far better prompt than "go look at the providers".

## Then: Google Jules, free tier

Best fit because it is PR-only by design, which is the guardrail rather than a policy you hope it
follows. Free tier is 15 tasks per rolling 24 hours, 3 concurrent, more than enough for weekly
provider review.

1. Go to `jules.google.com`, sign in with the **personal** Google account, not the work one.
2. Connect the Jules GitHub app and grant it **only** `govinda-rajulu/patch-factory`.
3. It reads `AGENTS.md` automatically. That file is the contract: hard limits, the six rules, and
   the list of paths it must never touch.
4. Set the repo to require PRs from it. You already have `CODEOWNERS`, so nothing it opens can
   merge without you.
5. First task, paste this verbatim:

       Read AGENTS.md, then docs/review/DECISIONS-reddit-morphe.tsv.
       For every row where column 1 is empty, fill it with IN or OUT and append a one-line
       reason, using only the rules in AGENTS.md and src/patches/BANNED and CONFIRM.
       Change nothing else. Open one pull request titled: reddit: classify morphe patches.

   That is small, reviewable, uses no judgement you have not already encoded, and clears real
   backlog. Read the diff properly. If it obeyed the contract on that, widen it slowly.

## What to never ask it

- Anything open-ended. "Keep the repo healthy" against a repo that publishes signed binaries is
  how you get a change you cannot audit.
- To dispatch a build, touch a workflow, or edit `BANNED` / `CONFIRM` / `QUARANTINE`.
- To decide a `CONFIRM` patch. That marker means a human decides; an agent that decides them has
  removed the only reason the file exists.

## Tokens and secrets, if you ever go beyond Jules

Give it a **fine-grained** PAT scoped to this one repository, with `contents: write` and
`pull-requests: write`. Never `workflow: write`: an agent that can edit `.github/workflows` can
edit its own guardrails, and everything above becomes decoration.

## The alternatives, honestly

| Option | Verdict |
|---|---|
| **Jules** free | Recommended. Cloud VM, plans, multi-file edits, opens a PR. PR-only by design. |
| **Copilot** free | Chat and completions only; the agent that opens PRs is on the paid plans. Useful as a *reviewer* on a PR you already have. |
| **Gemini CLI** | Already in Cloud Shell, but unpaid access is being migrated to Antigravity CLI, so do not build a routine on it. It also cannot run shell commands in your environment, which is why every gate here is shell you run yourself. |
| **Self-hosted** | Not worth it. The task is a few thousand tokens of provider changelog a week. |

Verify the current free limits yourself before relying on any of them. They move constantly and
this table will age.

## The test that matters

Once it has opened a PR, ask yourself one thing: **could I have caught this if it were wrong?**
If the diff is small and every claim in the body cites a `list-patches` line or a rule, yes. If
the diff is thirty files, close it and narrow the task. That judgement is the whole job, and it
does not transfer to the agent no matter how good the agent gets.
