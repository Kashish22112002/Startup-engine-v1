"""
Reddit data fetcher using public JSON endpoints — no API credentials required.

Reddit exposes public JSON feeds for every subreddit:
  - https://www.reddit.com/r/{sub}/hot.json?limit=25
  - https://www.reddit.com/r/{sub}/new.json?limit=25
  - https://www.reddit.com/r/{sub}/comments/{post_id}.json  (for comments)

These require no authentication; only a descriptive User-Agent header.
"""
import json
import time
import random
import urllib.request
import urllib.error
from datetime import datetime, timedelta

_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
_REQUEST_DELAY = 1.0   # seconds between requests to be polite


def _reddit_get(url: str) -> dict | None:
    """Fetch a Reddit JSON endpoint and return the parsed response, or None on failure."""
    req = urllib.request.Request(url, headers={
        "User-Agent": _USER_AGENT,
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
    })
    try:
        import gzip
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read()
            # Handle gzip-compressed responses
            if resp.info().get("Content-Encoding") == "gzip":
                raw = gzip.decompress(raw)
            return json.loads(raw.decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
        print(f"[reddit_client] Request failed for {url}: {exc}")
        return None



def _fetch_comments(subreddit: str, post_id: str, max_comments: int = 5) -> list[dict]:
    """Fetch the top-level comments for a single post."""
    url = f"https://www.reddit.com/r/{subreddit}/comments/{post_id}.json?limit=10&depth=1"
    time.sleep(_REQUEST_DELAY)
    data = _reddit_get(url)
    if not data or len(data) < 2:
        return []

    comments = []
    comment_listing = data[1].get("data", {}).get("children", [])
    for child in comment_listing[:max_comments]:
        if child.get("kind") != "t1":
            continue
        c = child["data"]
        body = c.get("body", "").strip()
        if not body or body == "[deleted]" or body == "[removed]":
            continue
        comments.append({
            "reddit_comment_id": c.get("id", f"cid_{random.randint(10000,99999)}"),
            "body": body,
            "score": int(c.get("score", 0)),
            "created_utc": float(c.get("created_utc", time.time())),
        })
    return comments


def fetch_subreddit_posts(subreddit_name: str, limit: int = 20) -> list[dict]:
    """
    Fetch hot + new posts from a subreddit using Reddit's public JSON API.
    Falls back to simulation mode if the requests fail.

    Returns a list of post dicts in the format expected by analyzer.py:
      {
        "reddit_post_id": str,
        "title": str,
        "body": str,
        "score": int,
        "num_comments": int,
        "created_utc": float,
        "url": str,
        "comments": [ {"reddit_comment_id", "body", "score", "created_utc"} ]
      }
    """
    subreddit_name = subreddit_name.lower().replace("r/", "").strip()
    per_feed = max(limit // 2, 10)

    posts_by_id: dict[str, dict] = {}

    for feed in ("hot", "new"):
        url = f"https://www.reddit.com/r/{subreddit_name}/{feed}.json?limit={per_feed}"
        print(f"[reddit_client] Fetching r/{subreddit_name}/{feed} …")
        data = _reddit_get(url)
        time.sleep(_REQUEST_DELAY)

        if not data:
            break

        children = data.get("data", {}).get("children", [])
        for child in children:
            if child.get("kind") != "t3":
                continue
            p = child["data"]

            # Only self-posts (text posts) have useful pain-point content
            if not p.get("is_self", False):
                continue

            post_id = p.get("id", "")
            if post_id in posts_by_id:
                continue

            body = p.get("selftext", "").strip()
            if body in ("[deleted]", "[removed]", ""):
                body = ""

            posts_by_id[post_id] = {
                "reddit_post_id": post_id,
                "title": p.get("title", ""),
                "body": body,
                "score": int(p.get("score", 0)),
                "num_comments": int(p.get("num_comments", 0)),
                "created_utc": float(p.get("created_utc", time.time())),
                "url": f"https://reddit.com{p.get('permalink', '')}",
                "comments": [],   # filled below
            }

        if len(posts_by_id) >= limit:
            break

    if not posts_by_id:
        print(f"[reddit_client] No live data for r/{subreddit_name} (Reddit may be blocking the request). Using simulation mode.")
        return generate_simulated_posts(subreddit_name, limit)

    # Fetch comments for each post (up to `limit` posts)
    post_list = list(posts_by_id.values())[:limit]
    print(f"[reddit_client] Fetching comments for {len(post_list)} posts …")
    for post in post_list:
        post["comments"] = _fetch_comments(subreddit_name, post["reddit_post_id"])

    print(f"[reddit_client] Done — {len(post_list)} posts fetched from r/{subreddit_name}.")
    return post_list


# ---------------------------------------------------------------------------
# Simulation fallback (used when Reddit is unreachable or returns nothing)
# ---------------------------------------------------------------------------

def generate_simulated_posts(subreddit_name: str, limit: int = 20) -> list[dict]:
    topics = [
        {
            "theme": "invoicing_delays",
            "title_templates": [
                "Anyone else struggling with client payment delays?",
                "Chasing invoices is taking 30% of my time, help",
                "I hate follow-up emails for unpaid invoices. How do you automate this?",
            ],
            "body_templates": [
                "I run a freelance consulting business. Currently, I have 4 clients who are 15-30 days late on their invoices. Writing 'friendly reminders' feels awkward, and I end up wasting hours keeping track of who owes what in a spreadsheet. Is there a simple tool that does automated, firm-but-polite reminders?",
                "Every single month, I send out invoices, and every single month, clients just 'forget' to pay. I'm spending my weekends drafting email nudges. I wish there was an app that just text/email pings them automatically, hooks into Stripe, and adds a late fee if they ignore it.",
            ],
            "comments": [
                "Honestly, I hired a virtual assistant just to do this, but an automated tool would save me $500 a month.",
                "I use spreadsheets and calendar reminders. It sucks. I hate the confrontation of asking for money.",
                "A tool that integrates with Slack or WhatsApp to ping clients would be awesome. Email is too easy to archive and ignore.",
                "I would pay $30/mo for something that handles late fee calculations and reminder sequences dynamically.",
                "Make sure you charge 50% upfront. But yeah, late stage invoicing is a huge pain.",
            ],
            "niche_keywords": ["freelance", "smallbusiness", "consulting", "webdev", "agency", "accounting"],
        },
        {
            "theme": "lead_generation",
            "title_templates": [
                "How do you find high-ticket clients without spending all day on Upwork?",
                "Is cold emailing dead, or am I just terrible at it?",
                "What's your workflow for finding qualified sales leads?",
            ],
            "body_templates": [
                "I've been trying to scale my boutique agency, but Upwork fees are eating my margins, and sending proposals feels like throwing applications into a black hole. Cold emailing has a 1% response rate. Where are you guys finding actual leads who have a budget?",
                "I'm a solo developer. I love coding, but I absolutely dread sales prospecting. I spend hours scrolling LinkedIn and search results to find companies with outdated sites to email. Surely there's an automated parser or miner that finds these niche leads?",
            ],
            "comments": [
                "Finding leads is the #1 reason why solo freelancers fail. The sales pipeline is exhausting.",
                "I built a custom scraper for my niche, but it gets blocked constantly. If there was a clean service, I'd subscribe.",
                "Cold email isn't dead, but finding the RIGHT decision-maker's contact info is a nightmare.",
                "You need to build a personal brand. But that takes months. We need immediate leads to survive.",
                "Try looking at job boards. If they are hiring full-time, they might hire a freelancer. It's a manual grind though.",
            ],
            "niche_keywords": ["agency", "sales", "marketing", "consulting", "solopreneur", "saas"],
        },
        {
            "theme": "scope_creep",
            "title_templates": [
                "How do you deal with 'quick changes' that end up taking hours?",
                "Clients scope-creeping every project. Need advice",
                "I'm working double the hours for free due to scope creep",
            ],
            "body_templates": [
                "I sign a contract for a website build. Halfway through, the client says 'Oh, can we add a simple user login?' and 'Can we customize the admin dashboard?' I say yes to be nice, and now I'm 40 hours over budget with no extra pay. How do I track and charge for out-of-scope requests without offending the client?",
                "Scope creep is killing my profitability. I outline features in the contract, but clients always assume additional micro-requests are freebies. Is there a tool that helps track scope adjustments visually so clients can see the budget increase in real-time?",
            ],
            "comments": [
                "You need to learn to say: 'Sure, we can do that! Here is the change order and price estimate.'",
                "A dashboard where the client clicks 'approve extra feature' and it charges their card automatically would be a lifesaver.",
                "I struggle with this too. I hate saying no, and I end up eating the cost.",
                "We need a shared visual roadmap. When they add a card, they see the invoice estimate increase automatically.",
                "Make scope lines extremely clear. A change-management micro-app for freelancers is a solid idea.",
            ],
            "niche_keywords": ["webdev", "design", "agency", "freelance", "copywriting"],
        },
        {
            "theme": "expense_tracking",
            "title_templates": [
                "Sorting receipts for taxes makes me want to cry",
                "Is there an easy way to match receipts to bank transactions?",
                "Best tool for tracking business expenses as a solopreneur?",
            ],
            "body_templates": [
                "Tax season is here, and I've got a shoe box of physical receipts and a download folder full of PDF invoices. QuickBooks is bloated and expensive. I just want an app that scans my email inbox and receipts folder, extracts the price and vendor, and matches it with my bank feed. Why is this so hard?",
                "I lose hundreds in deductions every year because I forget to log business expenses. Standard apps require manual categorizing and complex account links. We need a frictionless receipt-matcher that handles digital receipts instantly.",
            ],
            "comments": [
                "QuickBooks is awful. It's built for accountants, not business owners.",
                "I use a Google Form shortcut on my phone screen to input expenses. It's the only way I stay disciplined.",
                "OCR receipt apps always get the tax amount wrong or fail to read folded paper.",
                "I'd pay a good chunk of cash for an AI expense auditor that reads my bank statements and flags missing invoices.",
                "Same, taxes are a nightmare. I literally spend 3 full days sorting spreadsheets every April.",
            ],
            "niche_keywords": ["finance", "accounting", "smallbusiness", "solopreneur", "freelance"],
        },
    ]

    matched_topics = [
        t for t in topics
        if any(kw in subreddit_name for kw in t["niche_keywords"])
    ] or topics

    random.seed(hash(subreddit_name))
    posts = []
    now = datetime.utcnow()

    for i in range(min(limit, len(matched_topics) * 3)):
        topic = matched_topics[i % len(matched_topics)]
        title = random.choice(topic["title_templates"])
        if random.random() > 0.7:
            title = f"{title} (in {subreddit_name})"
        body = random.choice(topic["body_templates"])

        score = random.randint(15, 350)
        num_comments = random.randint(5, 45)
        created_time = now - timedelta(days=random.randint(1, 45), hours=random.randint(1, 23))
        post_id = f"simpost_{subreddit_name}_{i}_{random.randint(1000, 9999)}"

        selected_comments = random.sample(topic["comments"], min(len(topic["comments"]), random.randint(3, 5)))
        comments = [
            {
                "reddit_comment_id": f"simcomm_{post_id}_{c_idx}",
                "body": comm_body,
                "score": random.randint(5, int(score * 0.4) + 2),
                "created_utc": (created_time + timedelta(hours=random.randint(1, 8))).timestamp(),
            }
            for c_idx, comm_body in enumerate(selected_comments)
        ]

        posts.append({
            "reddit_post_id": post_id,
            "title": title,
            "body": body,
            "score": score,
            "num_comments": num_comments,
            "created_utc": created_time.timestamp(),
            "url": f"https://reddit.com/r/{subreddit_name}/comments/{post_id}",
            "comments": comments,
        })

    return posts
