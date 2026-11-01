# Live Full Stack: remove the sample editions

Run this once, before or after the first real edition, to clear out the placeholder content that came with the site templates.

- Repository: `mharr171/daily-news`, branch `main`

## Step 1: Get the repository

Use the GitHub connector if it’s connected. Otherwise, clone the repository with git, using the access token given in this task’s setup. Never write the token into any file, commit, or report.

## Step 2: Find the samples

A sample edition is any entry in `posts.json` whose `summary` starts with “Sample edition”. List each one with its date and `file` path, and check which of those files exist in the repository.

If there are none, stop and report that the site has no sample editions left.

## Step 3: Confirm

Show the list from Step 2 and ask: “Remove these sample editions?” Continue only after a clear yes.

## Step 4: Remove them

1. Delete each sample entry from `posts.json`. Keep every other entry exactly as it is.
2. Delete each sample page that exists, such as `posts/2026-10-31.html`.
3. If no editions remain, `posts.json` should read exactly:

```json
{ "editions": [] }
```

The front page then shows a notice that the first edition is on its way.

## Step 5: Check your work

- `posts.json` is valid JSON.
- No real edition was removed.
- `index.html`, `CNAME`, `README.md`, and everything in `templates/` and `tasks/` are untouched.

## Step 6: Publish and report

Commit to `main` with the message `Remove sample editions` and push. Report which entries and files were removed.

If real editions already exist, their issue numbers may now start above 1. Run `tasks/renumber-editions.md` to fix that.
