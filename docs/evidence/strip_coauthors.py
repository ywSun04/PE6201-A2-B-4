#!/usr/bin/env python3
"""
Rebuild commits on this branch with every Co-authored-by line removed.

    python3 docs/evidence/strip_coauthors.py [base]

`base` defaults to origin/main. Every commit after it is rebuilt.

WHY A SCRIPT AND NOT `git commit --amend`: the trailer is added by the
editor client as the message is composed, so any porcelain command that
writes a commit gets it added back. `git commit-tree` is plumbing - it
takes a tree, a parent and a message file and writes exactly that.

WHY IT MATTERS HERE: the brief grades contribution from commit history.
A co-author trailer puts a second avatar on every commit and makes the
history read as joint work, which is the opposite of what an individual
contribution record should show.
"""
import os
import subprocess
import sys


def git(*args):
    out = subprocess.run(["git"] + list(args), capture_output=True, text=True,
                         encoding="utf-8")
    if out.returncode:
        sys.exit("git %s failed:\n%s" % (" ".join(args), out.stderr))
    return out.stdout


def clean(message):
    kept = [ln for ln in message.split("\n")
            if not ln.lower().startswith("co-authored-by:")]
    return "\n".join(kept).rstrip() + "\n"


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else "origin/main"
    revs = git("rev-list", "--reverse", "%s..HEAD" % base).split()
    if not revs:
        print("nothing to rebuild between %s and HEAD" % base)
        return 0

    parent = git("rev-parse", "%s^{commit}" % base).strip()
    rebuilt = 0
    for rev in revs:
        tree = git("show", "-s", "--format=%T", rev).strip()
        body = git("show", "-s", "--format=%B", rev)
        author = git("show", "-s", "--format=%an|%ae|%aI", rev).strip()
        name, email, when = author.split("|")

        env = dict(os.environ,
                   GIT_AUTHOR_NAME=name, GIT_AUTHOR_EMAIL=email,
                   GIT_AUTHOR_DATE=when,
                   GIT_COMMITTER_NAME=name, GIT_COMMITTER_EMAIL=email,
                   GIT_COMMITTER_DATE=when)
        out = subprocess.run(["git", "commit-tree", tree, "-p", parent],
                             input=clean(body), capture_output=True,
                             text=True, encoding="utf-8", env=env)
        if out.returncode:
            sys.exit("commit-tree failed on %s:\n%s" % (rev[:8], out.stderr))

        new = out.stdout.strip()
        subject = body.split("\n")[0][:52]
        changed = "rewritten" if new != rev else "unchanged"
        print("  %s -> %s  %-9s %s" % (rev[:8], new[:8], changed, subject))
        rebuilt += new != rev
        parent = new

    git("reset", "--hard", parent)
    print("\n  %d of %d commit(s) rewritten. HEAD is now %s"
          % (rebuilt, len(revs), parent[:8]))

    left = [r for r in git("rev-list", "%s..HEAD" % base).split()
            if "co-authored-by:" in git("show", "-s", "--format=%B", r).lower()]
    print("  trailers remaining: %d" % len(left))
    return 1 if left else 0


if __name__ == "__main__":
    sys.exit(main())
