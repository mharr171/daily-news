# Live Full Stack: make an edition for a specific date

Create an edition for a date the reader chooses, such as a day the scheduled task missed.

- Repository: `mharr171/daily-news`, branch `main`
- Time zone for dates: America/Los_Angeles

## Step 1: Ask for the date

Ask: “Which date should I make an edition for?” Accept any clear date, such as “Nov 3”, “last Tuesday”, or `2026-11-03`. Restate it as both `YYYY-MM-DD` and the long form, for example `Tuesday, November 3, 2026`, and confirm it before continuing.

- A future date isn’t allowed. Ask for another date.
- For a date more than 30 days ago, warn that finding news from that day takes more digging and may produce a thinner edition, then ask whether to continue.

## Step 2: Get the repository

Use the GitHub connector if it’s connected. Otherwise, clone the repository with git, using the access token given in this task’s setup. Never write the token into any file, commit, or report.

## Step 3: Check for an existing edition

If `posts/YYYY-MM-DD.html` already exists, or `posts.json` already has an entry for that date, ask whether to replace it. If not, stop. If yes, the new edition replaces both the page and its `posts.json` entry, keeping the entry in the same place.

## Step 4: Make the edition

Follow Steps 3 through 7 of `tasks/daily-news-task.md`, with these differences:

- **Research window:** look for stories published on the chosen date or within the 48 hours before it. Don’t use anything published after the chosen date. Treat the edition as if it had been written that morning.
- **Avoiding repeats:** compare against the editions from the 7 days before the chosen date, not the 7 days before today.
- **Placement in posts.json:** insert the new entry so the `editions` list stays in date order, newest first, rather than always at the top.
- **Issue number:** use the edition’s position counting from the oldest edition, starting at 1. Inserting an edition between existing ones shifts the numbers of every later edition, so after publishing, run `tasks/renumber-editions.md` if any editions are dated after this one.

## Step 5: Publish

Commit to `main` with the message `Edition YYYY-MM-DD (added later)` and push.

## Step 6: Report

Report the date, issue number, how many stories ran in each topic, and the link `https://www.livefullstack.com/posts/YYYY-MM-DD.html`. If later editions need renumbering, say so.
