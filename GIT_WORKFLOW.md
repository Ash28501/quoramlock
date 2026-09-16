# Git Workflow Guide for QuorumLock

This project is a good excuse to practice a real branching workflow instead of pushing everything straight to `main`. Below is the exact sequence of commands for each phase, plus the git concepts each step teaches you.

---

## The model we're using: trunk-based with feature branches

- `main` — always in a working, demoable state. You only merge into it via a pull request (PR), never commit to it directly.
- `feature/<name>` — one branch per roadmap phase. Created from `main`, merged back into `main` when the phase works.
- Tags (`v0.1-single-node`, `v0.2-raft-cluster`, ...) — mark each completed milestone so you (or an interviewer) can check out exactly what existed at each stage.

This is simpler than full Git Flow (no `develop` branch) — appropriate for a solo project, but it still teaches you branching, PRs, merging, conflict resolution, and tagging, which is what actually gets used day-to-day at most companies.

---

## One-time setup

```bash
mkdir quorumlock && cd quorumlock
git init
git branch -M main
# create the repo on GitHub first (via github.com), then:
git remote add origin https://github.com/<your-username>/quorumlock.git
```

Add the README and .gitignore first, and make your first commit directly to `main` — this initial scaffold commit is the one exception to "never commit directly to main," since there's nothing to branch from yet.

```bash
git add README.md GIT_WORKFLOW.md .gitignore
git commit -m "chore: initial project scaffold and docs"
git push -u origin main
```

**Concept: `git push -u`** — the `-u` sets up tracking between your local `main` and `origin/main`, so future pushes just need `git push`.

---

## Per-phase workflow (repeat for each of the 7 roadmap phases)

### 1. Start the phase — create a branch from `main`

```bash
git checkout main
git pull origin main          # make sure you're starting from the latest
git checkout -b feature/single-node-server
```

**Concept: branching** — this creates an isolated line of work. Anything you commit here doesn't touch `main` until you explicitly merge it. This is what lets you experiment/break things safely.

### 2. Work and commit as you go

Commit in small, logical chunks rather than one giant commit at the end — it makes your history readable and makes `git bisect` (finding which commit introduced a bug) actually useful later.

```bash
git add server/grpc_service.py
git commit -m "feat: implement AcquireLock gRPC endpoint"

git add server/lock_manager.py
git commit -m "feat: add in-memory lock state with TTL expiry"
```

**Concept: Conventional Commits** — prefixing messages with `feat:`, `fix:`, `chore:`, `docs:`, `test:` makes your history scannable and is a real convention used in industry (and by tools that auto-generate changelogs).

### 3. Push the branch and open a Pull Request

```bash
git push -u origin feature/single-node-server
```

Then go to GitHub and open a PR from `feature/single-node-server` into `main`. Even working solo, write a real PR description (what changed, how you tested it) — this is exactly the habit that matters on a team, and it gives you a paper trail you can literally show in interviews.

**Concept: Pull Requests** — a PR isn't a git concept per se (it's a GitHub feature), but it's the mechanism for code review and for keeping `main` protected. On GitHub, you can enable "branch protection" on `main` to *require* a PR before merging — worth turning on for this repo.

### 4. Merge into `main`

Two options — worth understanding both:

**Merge commit (default, recommended while learning):**
```bash
git checkout main
git pull origin main
git merge feature/single-node-server
```
This preserves the full branch history with a merge commit. Easiest to reason about.

**Squash merge (do this on GitHub's PR "Squash and merge" button, not locally):**
Combines all your feature-branch commits into a single clean commit on `main`. Good once you've been committing very granularly and want `main`'s history to stay high-level.

Either is fine here — pick "Squash and merge" on GitHub if your feature-branch commits are messy work-in-progress commits, or a regular merge if they're already clean.

### 5. Tag the milestone

```bash
git tag -a v0.1-single-node -m "Single-node lock server working"
git push origin v0.1-single-node
```

**Concept: tags** — an immutable pointer to a specific commit. Unlike branches, tags don't move. Great for marking "this is what I demoed" or release points — and it means you can always `git checkout v0.1-single-node` later to see exactly that state, even after `main` has moved on.

### 6. Delete the merged branch

```bash
git branch -d feature/single-node-server
git push origin --delete feature/single-node-server
```

Keeps your branch list clean. GitHub also has an auto-delete-on-merge setting worth turning on.

---

## Handling merge conflicts (you will hit this eventually)

If `main` has moved on since you branched, `git merge` (or the PR merge) may show a conflict. To resolve it locally:

```bash
git checkout feature/raft-cluster
git fetch origin
git merge origin/main
# git will mark conflicting files — open them, look for <<<<<<< / ======= / >>>>>>> markers
# edit the file to keep the correct combined content, then:
git add <the resolved file>
git commit
git push
```

**Concept: rebase vs merge** — `git merge` (above) preserves both histories and adds a merge commit. `git rebase origin/main` instead replays your commits on top of the latest `main`, producing a linear history but rewriting your commit hashes. For this project, stick with merge — rebase is a good "level 2" concept to learn later once branching/merging feels natural.

---

## Full phase-by-phase branch list for this project

```
feature/single-node-server   → v0.1-single-node
feature/raft-cluster         → v0.2-raft-cluster
feature/fencing-tokens       → v0.3-fencing-tokens
feature/docker-demo          → v0.4-docker-demo
feature/observability        → v0.5-observability
feature/fault-injection      → v0.6-fault-injection
feature/docs-and-benchmarks  → v1.0
```

By the end, your GitHub repo's commit graph and tag list *itself* becomes a visible artifact of disciplined engineering practice — something worth pointing to in an interview alongside the code.
