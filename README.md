# My Forge90 Work

This is **your** repo for the Forge90 course. You keep your homework here, one folder per day, and your instructor reads it from here. Nobody else in the class can see it: it is private, and only you and the instructor have access.

Every day the flow is the same and takes about two minutes:

1. Do the assignment inside that day's folder.
2. Run the checker: `python check_submission.py day03`. It tells you what is missing and gives you an automatic score.
3. Fix anything red, then `git add`, `git commit`, `git push`.

## One-time setup (about 10 minutes)

**1. Make your own copy of this template.** On this repo's GitHub page click the green **Use this template** button, then **Create a new repository**. Name it `forge90-work` and choose **Private**. Do not make it public.

**2. Add your instructor.** In your new repo go to **Settings**, then **Collaborators**, then **Add people**, and add the instructor: **`neeravpatel10`**. The instructor has to accept the invitation, so tell them once you have sent it.

**3. Clone your repo** onto your laptop (use your own GitHub username):

```text
git clone https://github.com/YOUR-USERNAME/forge90-work.git
cd forge90-work
```

**4. Put your API key in a `.env` file** in this folder, exactly as on Day 2:

```text
GEMINI_API_KEY=paste-your-key-here
```

`.gitignore` already blocks `.env`, so it is never uploaded. **Never commit a real key.** If you do, the checker shows a red `BLOCKED` warning and you must revoke that key (see "If the checker says BLOCKED" below).

**5. Set up Python** the same way as Day 2. If you already have a working environment from Day 2 you can keep using it. Otherwise:

```text
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

**6. Test the checker.** It should say nothing has been submitted yet:

```text
python check_submission.py day01
```

## Every day: how to submit

**Where things go.** Each day has its own folder: `day01`, `day02`, `day03`, `day04`, `day04b`, `day05`, and so on. **Wherever an assignment says "your own folder" or `my_work/`, it means that day's folder here.** Use the file names the assignment gives you, exactly, for example `day03/chat_loop.py` and `day03/day03_answers.md`.

**Notebooks:** run every cell from top to bottom, then **save**. Submit the notebook **with its outputs showing**. The instructor reads your outputs; they do not re-run your code.

**Check, then push.**

```text
python check_submission.py day03
git add day03
git commit -m "Day 03"
git push
```

The deadline for each assignment is the start of the next session. GitHub records when you pushed.

You can push as many times as you like. Run the checker again after each change.

## What the checker and the score mean

The checker reads `checks/dayNN.json`, so you can open it to see **exactly** what is checked and how many points each item is worth. Typical items are:

- the file exists and is not empty,
- the Python code has no syntax errors,
- the notebook was run, saved, and has no error cells,
- your answers file has each Part the assignment asks for,
- your work contains the pieces the assignment requires,
- **no API key or `.env` anywhere in your repo**.

**Score out of 100. 80 or more counts as COMPLETE.**

> The score measures **completeness and hygiene**, not how good your answers are. A high score means "nothing is missing". Your instructor still reads your work, and that is where the feedback comes from. Do not try to game the checker: writing filler to reach a word count earns you nothing.

## If the checker says BLOCKED

The checker found something that looks like a secret (an API key, or a tracked `.env`).

1. Go to **aistudio.google.com/apikey** and delete that key, then create a new one. A leaked key must be treated as public.
2. Put the new key in your `.env` only.
3. Remove the key from your files, run the checker again, and push.

Deleting the key from a file is **not enough** if it was already pushed, because git remembers old versions. That is why revoking the key is the important step.

## Rules

- **Made-up data only.** Never put a real customer's name, email, phone or order in any file (Day 5 explains why).
- **Your own work.** Discussing ideas is fine; the code and answers you submit are yours.
- **Keep the file names.** The checker and your instructor look for the exact names in each assignment.

## Troubleshooting

| What you see | What to do |
|---|---|
| `python` is not recognised | Try `py` instead, or activate your virtual environment first |
| `Nothing found in day03/ yet` | The folder name must be exactly `day03`, lowercase, with your files inside it |
| `not found` for a file | The file name or folder is wrong. Compare it with the assignment |
| A notebook item says cells were not run | Run all cells top to bottom, then save the notebook and check again |
| `git push` asks for a login | Sign in with your GitHub account (a browser window usually opens) |
| The instructor says they cannot see your repo | The invitation has not been sent or accepted. Check Settings, Collaborators |
| The checker has no checklist for a day | New days get new checklists. Open [forge90-student-template](https://github.com/neeravpatel10/forge90-student-template), copy the new `checks/dayNN.json` (and the latest `check_submission.py`, if it changed) into your own repo, then run the checker again |
