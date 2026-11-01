# Live Full Stack: update the topics

Help the reader review and change the topics their daily edition covers. This is a conversation: ask questions, make suggestions, and only save changes they approve.

- Repository: `mharr171/daily-news`, branch `main`
- The topics live in the “Topics” section of `tasks/daily-news-task.md`.

## Step 1: Get the repository

Use the GitHub connector if it’s connected. Otherwise, clone the repository with git, using the access token given in this task’s setup. Never write the token into any file, commit, or report.

## Step 2: Show the current topics

Read the Topics section of `tasks/daily-news-task.md` and show each topic’s name and a one-line summary of what it covers.

If `posts.json` has editions, also note, for each topic, how many stories it carried over the last 7 editions. A topic that’s often empty is worth raising.

## Step 3: Ask what they want

Ask one question at a time, offering short multiple-choice answers where you can:

1. Do you want to keep, change, add, or remove topics?
2. For each change: what should this topic cover, and what should it leave out?
3. Has anything changed that the paper should reflect, such as a new job focus, a new hobby, or a topic that’s become less useful?

## Step 4: Make suggestions

Based on the answers and the current topics, suggest improvements where they would help, and explain each in one sentence. For example:

- Narrowing a topic that’s too broad to fill well, or broadening one that’s often empty.
- Splitting a topic that mixes very different news.
- A new topic that fits their stated interests.
- Better search focus, such as specific companies, brands, regions, or kinds of sources.
- Adding or removing a “Why it matters” line for a topic.

Keep it to a handful of suggestions, and let them accept or skip each one. Don’t add a topic they didn’t agree to.

Guidelines for good topics:

- 3–6 topics in total keeps an edition readable.
- Each topic should reliably have news most days. Very niche ones can be folded into a broader topic.
- Topic names are short, in sentence case, like “Jobs & careers”.

## Step 5: Confirm

Show the complete new Topics section exactly as it will be saved, in order. Ask: “Save these topics?” Make any requested edits, and continue only after a clear yes.

## Step 6: Save

1. Replace only the numbered topic list in the Topics section of `tasks/daily-news-task.md`. Change nothing else in that file or any other file.
2. Past editions stay as they are; new topics start with the next edition.
3. Commit to `main` with the message `Update topics` and push.

## Step 7: Report

Summarize what changed: topics added, removed, renamed, or refocused.
