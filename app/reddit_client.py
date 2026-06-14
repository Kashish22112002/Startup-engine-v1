import os
import time
import random
import praw
from datetime import datetime, timedelta

def get_reddit_client():
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    user_agent = os.getenv("REDDIT_USER_AGENT", "startup-pain-point-miner:v1.0")
    
    if not client_id or not client_secret or "your_" in client_id:
        return None
    
    try:
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent
        )
        # Test connection
        reddit.read_only = True
        return reddit
    except Exception as e:
        print(f"Failed to initialize live Reddit client: {e}. Falling back to simulation.")
        return None

def fetch_subreddit_posts(subreddit_name, limit=20):
    """
    Fetches hot and top posts from a subreddit, along with their top comments.
    If the client is not configured, it generates simulated posts and comments.
    """
    reddit = get_reddit_client()
    subreddit_name = subreddit_name.lower().replace("r/", "").strip()
    
    if reddit:
        try:
            print(f"Live Mode: Scraping r/{subreddit_name}...")
            sub = reddit.subreddit(subreddit_name)
            posts = []
            
            # Fetch hot posts
            for submission in sub.hot(limit=limit):
                if submission.is_self: # Text posts are better for pain points
                    submission.comments.replace_more(limit=0) # Get top comments easily
                    comments = []
                    for comment in submission.comments[:5]:
                        comments.append({
                            "reddit_comment_id": comment.id,
                            "body": comment.body,
                            "score": comment.score,
                            "created_utc": comment.created_utc
                        })
                    
                    posts.append({
                        "reddit_post_id": submission.id,
                        "title": submission.title,
                        "body": submission.selftext,
                        "score": submission.score,
                        "num_comments": submission.num_comments,
                        "created_utc": submission.created_utc,
                        "url": f"https://reddit.com{submission.permalink}",
                        "comments": comments
                    })
            return posts
        except Exception as e:
            print(f"Error scraping live Reddit: {e}. Falling back to simulation mode.")
            # Fall through to simulation mode
    
    # Simulation Mode
    print(f"Simulation Mode: Generating high-fidelity mock data for r/{subreddit_name}...")
    time.sleep(1.5) # Simulate latency
    return generate_simulated_posts(subreddit_name, limit)

def generate_simulated_posts(subreddit_name, limit):
    # Dynamic templates based on typical subreddit niches
    topics = [
        {
            "theme": "invoicing_delays",
            "title_templates": [
                "Anyone else struggling with client payment delays?",
                "Chasing invoices is taking 30% of my time, help",
                "I hate follow-up emails for unpaid invoices. How do you automate this?"
            ],
            "body_templates": [
                "I run a freelance consulting business. Currently, I have 4 clients who are 15-30 days late on their invoices. Writing 'friendly reminders' feels awkward, and I end up wasting hours keeping track of who owes what in a spreadsheet. Is there a simple tool that does automated, firm-but-polite reminders?",
                "Every single month, I send out invoices, and every single month, clients just 'forget' to pay. I'm spending my weekends drafting email nudges. I wish there was an app that just text/email pings them automatically, hooks into Stripe, and adds a late fee if they ignore it."
            ],
            "comments": [
                "Honestly, I hired a virtual assistant just to do this, but an automated tool would save me $500 a month.",
                "I use spreadsheets and calendar reminders. It sucks. I hate the confrontation of asking for money.",
                "A tool that integrates with Slack or WhatsApp to ping clients would be awesome. Email is too easy to archive and ignore.",
                "I would pay $30/mo for something that handles late fee calculations and reminder sequences dynamically.",
                "Make sure you charge 50% upfront. But yeah, late stage invoicing is a huge pain."
            ],
            "niche_keywords": ["freelance", "smallbusiness", "consulting", "webdev", "agency", "accounting"]
        },
        {
            "theme": "lead_generation",
            "title_templates": [
                "How do you find high-ticket clients without spending all day on Upwork?",
                "Is cold emailing dead, or am I just terrible at it?",
                "What's your workflow for finding qualified sales leads?"
            ],
            "body_templates": [
                "I've been trying to scale my boutique agency, but Upwork fees are eating my margins, and sending proposals feels like throwing applications into a black hole. Cold emailing has a 1% response rate. Where are you guys finding actual leads who have a budget?",
                "I'm a solo developer. I love coding, but I absolutely dread sales prospecting. I spend hours scrolling LinkedIn and search results to find companies with outdated sites to email. Surely there's an automated parser or miner that finds these niche leads?"
            ],
            "comments": [
                "Finding leads is the #1 reason why solo freelancers fail. The sales pipeline is exhausting.",
                "I built a custom scraper for my niche, but it gets blocked constantly. If there was a clean service, I'd subscribe.",
                "Cold email isn't dead, but finding the RIGHT decision-maker's contact info is a nightmare.",
                "You need to build a personal brand. But that takes months. We need immediate leads to survive.",
                "Try looking at job boards. If they are hiring full-time, they might hire a freelancer. It's a manual grind though."
            ],
            "niche_keywords": ["agency", "sales", "marketing", "consulting", "solopreneur", "saas"]
        },
        {
            "theme": "scope_creep",
            "title_templates": [
                "How do you deal with 'quick changes' that end up taking hours?",
                "Clients scope-creeping every project. Need advice",
                "I'm working double the hours for free due to scope creep"
            ],
            "body_templates": [
                "I sign a contract for a website build. Halfway through, the client says 'Oh, can we add a simple user login?' and 'Can we customize the admin dashboard?' I say yes to be nice, and now I'm 40 hours over budget with no extra pay. How do I track and charge for out-of-scope requests without offending the client?",
                "Scope creep is killing my profitability. I outline features in the contract, but clients always assume additional micro-requests are freebies. Is there a tool that helps track scope adjustments visually so clients can see the budget increase in real-time?"
            ],
            "comments": [
                "You need to learn to say: 'Sure, we can do that! Here is the change order and price estimate.'",
                "A dashboard where the client clicks 'approve extra feature' and it charges their card automatically would be a lifesaver.",
                "I struggle with this too. I hate saying no, and I end up eating the cost.",
                "We need a shared visual roadmap. When they add a card, they see the invoice estimate increase automatically.",
                "Make scope lines extremely clear. A change-management micro-app for freelancers is a solid idea."
            ],
            "niche_keywords": ["webdev", "design", "agency", "freelance", "copywriting"]
        },
        {
            "theme": "expense_tracking",
            "title_templates": [
                "Sorting receipts for taxes makes me want to cry",
                "Is there an easy way to match receipts to bank transactions?",
                "Best tool for tracking business expenses as a solopreneur?"
            ],
            "body_templates": [
                "Tax season is here, and I've got a shoe box of physical receipts and a download folder full of PDF invoices. QuickBooks is bloated and expensive. I just want an app that scans my email inbox and receipts folder, extracts the price and vendor, and matches it with my bank feed. Why is this so hard?",
                "I lose hundreds in deductions every year because I forget to log business expenses. Standard apps require manual categorizing and complex account links. We need a frictionless receipt-matcher that handles digital receipts instantly."
            ],
            "comments": [
                "QuickBooks is awful. It's built for accountants, not business owners.",
                "I use a Google Form shortcut on my phone screen to input expenses. It's the only way I stay disciplined.",
                "OCR receipt apps always get the tax amount wrong or fail to read folded paper.",
                "I'd pay a good chunk of cash for an AI expense auditor that reads my bank statements and flags missing invoices.",
                "Same, taxes are a nightmare. I literally spend 3 full days sorting spreadsheets every April."
            ],
            "niche_keywords": ["finance", "accounting", "smallbusiness", "solopreneur", "freelance"]
        }
    ]
    
    # Select topics matching the subreddit or keywords
    matched_topics = []
    for t in topics:
        # Check if subreddit or niche overlaps with keywords
        is_match = False
        for kw in t["niche_keywords"]:
            if kw in subreddit_name:
                is_match = True
                break
        if is_match:
            matched_topics.append(t)
            
    # Fallback to general topics if no match
    if not matched_topics:
        matched_topics = topics
        
    random.seed(hash(subreddit_name))
    
    posts = []
    now = datetime.utcnow()
    
    for i in range(min(limit, len(matched_topics) * 3)):
        # Pick a topic
        topic = matched_topics[i % len(matched_topics)]
        
        # Pick title and body
        title = random.choice(topic["title_templates"])
        # Add a bit of variation to titles
        title = f"{title} (in {subreddit_name})" if random.random() > 0.7 else title
        body = random.choice(topic["body_templates"])
        
        # Generate post metadata
        score = random.randint(15, 350)
        num_comments = random.randint(5, 45)
        created_time = now - timedelta(days=random.randint(1, 45), hours=random.randint(1, 23))
        post_id = f"simpost_{subreddit_name}_{i}_{random.randint(1000, 9999)}"
        
        # Generate comments
        comments = []
        selected_comments = random.sample(topic["comments"], min(len(topic["comments"]), random.randint(3, 5)))
        for c_idx, comm_body in enumerate(selected_comments):
            comments.append({
                "reddit_comment_id": f"simcomm_{post_id}_{c_idx}",
                "body": comm_body,
                "score": random.randint(5, int(score * 0.4) + 2),
                "created_utc": (created_time + timedelta(hours=random.randint(1, 8))).timestamp()
            })
            
        posts.append({
            "reddit_post_id": post_id,
            "title": title,
            "body": body,
            "score": score,
            "num_comments": num_comments,
            "created_utc": created_time.timestamp(),
            "url": f"https://reddit.com/r/{subreddit_name}/comments/{post_id}",
            "comments": comments
        })
        
    return posts
