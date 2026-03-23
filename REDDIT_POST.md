# Reddit Post

**Title:**
`Built a tool that auto-monitors your H-1B LCA status and texts you when it gets certified`

---

If you've filed an H-1B LCA recently, you know the anxiety — refreshing the FLAG DOL portal every few hours wondering if it's approved yet.

I went through this recently and built a small Python tool to automate it. Here's what I learned and what the tool does.

---

**First — the LCA process is 100% automated**

There's no human reviewing your application. DOL runs a nightly batch script that checks:
- Is the wage above prevailing wage?
- Are all fields filled?

If yes → auto-certified. The only reason it takes 7 days is a **mandatory waiting period** baked into the law. The system is literally just sitting on your application until the timer runs out.

---

**The case number is mathematically predictable**

Every LCA number follows this format:

```
I-200-YYDDD-XXXXXX
```

- `YY` = 2-digit year
- `DDD` = Julian day (e.g. April 1 = day 091)
- `XXXXXX` = global sequential counter

So if your employer filed on April 1, 2026 your case number starts with `I-200-26091-`. You can find the full number by searching the DOL quarterly disclosure Excel file with your employer name + job title.

---

**What the tool does**

1. Takes your case number, emails, and phone numbers
2. Checks the FLAG DOL portal via headless browser
3. Sends email + SMS the moment status flips to CERTIFIED
4. Runs on a cron schedule so you don't have to think about it

Two modes — **SMTP** (just needs a Gmail app password, no other dependencies) or **gmail-tools MCP** if you're already in that ecosystem.

---

**When to expect certification**

From historical DOL data (analyzed ~83,000 cases):
- DOL batch runs overnight
- Results visible by ~5 AM ET on day 7
- Friday is the biggest certification day (35% of all certifications)
- Monday filings: ~38% certify exactly on day 7

---

**Repo:** https://github.com/cortexark/lca-status-monitor

Includes a finder agent that figures out your case number from just employer name + job title + filing date.

---

*Good luck to everyone waiting. The 7 days feel longer than they are.*
