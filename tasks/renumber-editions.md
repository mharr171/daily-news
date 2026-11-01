# Live Full Stack: renumber the editions

Make every edition’s issue number match its place in date order: the oldest edition is No. 1, the next is No. 2, and so on. Use this after adding an edition for a past date or removing editions.

- Repository: `mharr171/daily-news`, branch `main`

The front page works out issue numbers from `posts.json` by itself, so only the day pages need fixing. Each day page carries its number in two places:

- the stamp near the top: `<p class="stamp">Issue No. 3</p>`
- the page description in the head: `content="Live Full Stack, issue 3: …"`

## Step 1: Get the repository

Use the GitHub connector if it’s connected. Otherwise, clone the repository with git, using the access token given in this task’s setup. Never write the token into any file, commit, or report.

## Step 2: Work out the correct numbers

1. Read `posts.json` and sort its editions by `date`, oldest first.
2. Number them from 1 in that order.
3. If two entries share a date, or an entry’s `file` doesn’t exist, stop and report the problem instead of guessing.

## Step 3: Compare

For each edition, open its page and read its current number from the stamp. Make a list of the pages whose number is wrong, showing the date, the current number, and the correct number.

If every number is already correct, stop and report that no changes were needed.

## Step 4: Fix the pages

For each page on the list, change only these two things:

- the number in `<p class="stamp">Issue No. N</p>`
- the number in the description’s `issue N:`

Change nothing else in any page.

Also make sure the `editions` list in `posts.json` is in date order, newest first. Reorder it only if it isn’t, and don’t change any entry’s contents.

## Step 5: Check your work

- Every page’s stamp matches its correct number, and no two pages share a number.
- `posts.json` is valid JSON with the same entries as before.
- Only day pages in `posts/` and, if reordered, `posts.json` changed.
- `index.html`, `CNAME`, `README.md`, and everything in `templates/` and `tasks/` are untouched.

## Step 6: Publish and report

Commit to `main` with the message `Renumber editions` and push. Report each page whose number changed, from what to what.
