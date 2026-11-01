# Live Full Stack: daily edition task

Each morning, research the news for the topics below, write that day’s edition as a new page, add it to the front page’s list, and publish it to GitHub.

- Site: https://www.livefullstack.com
- Repository: `mharr171/daily-news`, branch `main`
- Time zone for dates: America/Los_Angeles
- Task files: this file and the other task instructions live in the repository’s `tasks/` folder

## Topics

Cover each topic in this order. Aim for 2–4 stories per topic. If a topic has nothing worth reporting today, leave it out rather than padding it.

1. **Jobs & careers**: hiring and layoff news, salary trends, and notable openings in training and development, learning and development, sales enablement, onboarding, and insurance distribution, with a focus on the San Francisco Bay Area and remote roles. Add a “Why it matters” line to each story here, tied to someone looking for these roles.
2. **Watchmaking**: watch modding and microbrand news, including Seiko/TMI movements such as the NH35 and NH36, new cases, dials, and parts, and useful guides from the modding community.
3. **Tech & AI**: notable AI tool releases and updates, especially practical ones for everyday work and job searching.
4. **Board games**: new and upcoming releases, roll-and-write and city-building games, crowdfunding campaigns, and game design ideas.

To change what the paper covers, edit this section only, or run `tasks/update-topics.md`.

## Step 1: Get the repository

Use the GitHub connector if it’s connected. Otherwise, clone the repository with git, using the access token given in this task’s setup. Never write the token into any file, commit, or report.

## Step 2: Check before starting

1. Work out today’s date in the time zone above, as `YYYY-MM-DD` (for example `2026-11-02`) and in long form (for example `Monday, November 2, 2026`).
2. If `posts/YYYY-MM-DD.html` already exists for today, stop and report that today’s edition is already published.

## Step 3: Research

1. Read `posts.json` and note the headlines from the last 7 days, so you don’t repeat stories already covered.
2. For each topic, search the web for news from the last 24–48 hours. Prefer original reporting and official sources (company announcements, publishers, manufacturers) over aggregators and forums.
3. Open each story you plan to use and confirm what it says. Don’t report anything you couldn’t verify from the article itself.
4. Pick the strongest stories. The first story in each topic is its lead, so put the most important one first.

## Step 4: Write the stories

- Write every headline and summary in your own words. Don’t copy sentences from the source. A short quote under 15 words is allowed only when the exact wording matters, and at most one per story.
- Summaries are 2–3 sentences in plain language: what happened, who it affects, and what happens next.
- Credit each story with the source’s name and the article’s date.
- Link each headline to the original article.
- Use typographic apostrophes and quotes (’ “ ”) in text, and write `&amp;` for an ampersand in HTML.
- No photos.
- Keep the page free of personal details: no names of private people, no addresses, and nothing about the reader’s own applications or job search status.

Each story uses this format, inside its topic section:

```html
<article class="story">
  <h3><a href="ARTICLE URL" target="_blank" rel="noopener">Headline</a></h3>
  <p>Summary.</p>
  <p class="why"><strong>Why it matters:</strong> One line (Jobs &amp; careers only).</p>
  <p class="source">Source name, Nov 1, 2026</p>
</article>
```

Each topic uses this format:

```html
<section class="topic" id="jobs-careers">
  <h2>Jobs &amp; careers</h2>
  <div class="stories">
    <!-- stories here -->
  </div>
</section>
```

Give each section an id made from its topic name in lowercase, with spaces and symbols turned into single hyphens (for example, “Jobs & careers” becomes `jobs-careers` and “Tech & AI” becomes `tech-ai`).

## Step 5: Build the day’s page

1. Copy `templates/day.html` to `posts/YYYY-MM-DD.html`. Never edit the template itself.
2. In the new file, replace:
   - `{{DATE}}` with the date as `YYYY-MM-DD`
   - `{{DATE_LONG}}` with the long date
   - `{{ISSUE_NO}}` with the number of editions in `posts.json` plus 1
   - `{{SUMMARY}}` with a 2–3 sentence overview of the day’s biggest stories across all topics
   - `{{STORIES}}` with the topic sections, in the order listed above

## Step 6: Update posts.json

Add a new entry at the **top** of the `editions` list:

```json
{
  "date": "YYYY-MM-DD",
  "file": "posts/YYYY-MM-DD.html",
  "summary": "Same overview used for {{SUMMARY}}.",
  "headlines": [
    { "title": "The day’s single biggest headline", "topic": "Jobs & careers" },
    { "title": "Next headline", "topic": "Watchmaking" }
  ]
}
```

- List 4–5 headlines, most important first. The first one becomes the big headline on the front page.
- `topic` must match a topic name above, written with a plain `&` (this is JSON, not HTML).
- Keep every older entry. Never delete past editions.

## Step 7: Check your work

Before publishing, confirm all of these:

- `posts.json` is valid JSON.
- The new page contains no leftover `{{` placeholders.
- Every story link opens a real article.
- The only changed files are `posts.json` and the new `posts/YYYY-MM-DD.html`.
- `index.html`, `CNAME`, `README.md`, and everything in `templates/` and `tasks/` are untouched.

If any check fails, fix it. If you can’t, don’t publish, and explain the problem in your report.

## Step 8: Publish

Commit the changes to `main` with the message `Edition YYYY-MM-DD` and push. GitHub Pages republishes within a few minutes.

## Step 9: Report

Finish with a short report: the edition’s date and issue number, how many stories ran in each topic, any topic left out and why, and the link `https://www.livefullstack.com/posts/YYYY-MM-DD.html`.
