import re
from collections import Counter
from app import database
from app import reddit_client
from app import llm_client

def clean_text(text):
    if not text:
        return ""
    # Remove URLS
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    # Remove special characters, keep letters, numbers, spaces
    text = re.sub(r'[^a-zA-Z0-9\s\']', '', text)
    return text.lower().strip()

def extract_keywords(text, num_words=5):
    stopwords = {
        'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', "you're", "you've", "you'll", "you'd",
        'your', 'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she', "she's", 'her', 'hers',
        'herself', 'it', "it's", 'its', 'itself', 'they', 'them', 'their', 'theirs', 'themselves', 'what', 'which',
        'who', 'whom', 'this', 'that', "that'll", 'these', 'those', 'am', 'is', 'are', 'was', 'were', 'be', 'been',
        'being', 'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing', 'a', 'an', 'the', 'and', 'but', 'if',
        'or', 'because', 'as', 'until', 'while', 'of', 'at', 'by', 'for', 'with', 'about', 'against', 'between',
        'into', 'through', 'during', 'before', 'after', 'above', 'below', 'to', 'from', 'up', 'down', 'in', 'out',
        'on', 'off', 'over', 'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why',
        'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not',
        'only', 'own', 'same', 'so', 'than', 'too', 'very', 's', 't', 'can', 'will', 'just', 'don', "don't", 'should',
        "should've", 'now', 'd', 'll', 'm', 'o', 're', 've', 'y', 'ain', 'aren', "aren't", 'couldn', "couldn't",
        'didn', "didn't", 'doesn', "doesn't", 'hadn', "hadn't", 'hasn', "hasn't", 'haven', "haven't", 'isn', "isn't",
        'ma', 'mightn', "mightn't", 'mustn', "mustn't", 'needn', "needn't", 'shan', "shan't", 'shouldn', "shouldn't",
        'wasn', "wasn't", 'weren', "weren't", 'won', "won't", 'wouldn', "wouldn't", "anyone", "someone", "something",
        "things", "get", "like", "go", "use", "make", "want", "people", "would", "really", "could"
    }
    words = clean_text(text).split()
    filtered_words = [w for w in words if w not in stopwords and len(w) > 2]
    return [w for w, count in Counter(filtered_words).most_common(num_words)]

def cluster_texts(texts_with_meta):
    """
    Groups texts (posts or comments) into thematic clusters using TF-IDF/keyword overlap.
    Each item in texts_with_meta is a dict containing: 'text', 'score', 'url'.
    """
    # Pre-defined semantic centroids
    centroids = {
        "Invoicing & Late Payments": ["invoice", "payment", "unpaid", "reminders", "stripe", "chasing", "client", "billing"],
        "Lead Generation & Acquisition": ["lead", "prospect", "sales", "upwork", "cold email", "client", "agency", "proposal"],
        "Scope Creep & Change Orders": ["scope", "creep", "change", "overtime", "extra hours", "underestimate", "budget", "contract"],
        "Expense Sorting & Bookkeeping": ["tax", "expense", "receipt", "quickbooks", "accounting", "auditing", "bank statement"]
    }
    
    clusters = {name: [] for name in centroids.keys()}
    clusters["Other Complaints"] = []
    
    for item in texts_with_meta:
        text_clean = clean_text(item["text"])
        assigned = False
        
        # Check matching centroids
        for name, keywords in centroids.items():
            overlap = sum(1 for kw in keywords if kw in text_clean)
            if overlap >= 2: # At least two matching keywords
                clusters[name].append(item)
                assigned = True
                break
                
        if not assigned:
            # Check single strong keyword match
            for name, keywords in centroids.items():
                if any(kw in text_clean for kw in keywords[:3]): # Top 3 are primary keys
                    clusters[name].append(item)
                    assigned = True
                    break
                    
        if not assigned:
            clusters["Other Complaints"].append(item)
            
    # Process dynamically named sub-clusters for the 'Other' category if it is large
    final_clusters = []
    
    for cluster_name, items in clusters.items():
        if not items:
            continue
            
        # Extract summaries
        texts_only = [item["text"] for item in items]
        summary = llm_client.summarize_cluster_with_llm(texts_only)
        
        # Calculate stats
        total_engagement = sum(item["score"] for item in items)
        avg_engagement = round(total_engagement / len(items), 1)
        
        # Format quotes with source urls
        quotes = []
        for item in items[:3]:
            # Clean and shorten quotes
            body = item["text"]
            if len(body) > 150:
                body = body[:150] + "..."
            quotes.append({
                "quote": body,
                "url": item["url"]
            })
            
        final_clusters.append({
            "title": summary.get("title", cluster_name),
            "description": summary.get("description", "A collection of discussions and concerns surrounding this niche topic."),
            "representative_quotes": quotes,
            "avg_engagement": avg_engagement,
            "frequency": len(items)
        })
        
    return final_clusters

def mine_subreddit(subreddit_name, lookback_days=30):
    """
    Scrapes subreddit, filters for pain points, clusters them, and saves results.
    """
    # 1. Scraping
    raw_posts = reddit_client.fetch_subreddit_posts(subreddit_name)
    if not raw_posts:
        return []
        
    # Add subreddit to DB
    sub_id = database.add_subreddit(subreddit_name)
    database.save_posts_and_comments(sub_id, raw_posts)
    database.update_subreddit_scrape_time(subreddit_name)
    
    # 2. Extract texts to analyze
    candidates = []
    for post in raw_posts:
        candidates.append({
            "text": f"{post['title']}. {post['body']}",
            "score": post["score"],
            "url": post["url"]
        })
        for comment in post.get("comments", []):
            candidates.append({
                "text": comment["body"],
                "score": comment["score"],
                "url": post["url"]
            })
            
    # 3. Filter for pain points
    texts_only = [c["text"] for c in candidates]
    pain_point_indices = llm_client.analyze_pain_points_with_llm(texts_only)
    pain_points = [candidates[idx] for idx in pain_point_indices]
    
    if not pain_points:
        # Fallback to using all candidates if filtering was too strict
        pain_points = candidates[:10]
        
    # 4. Clustering
    clusters = cluster_texts(pain_points)
    
    # 5. Save clusters
    database.save_pain_point_clusters(subreddit_name, clusters)
    
    return clusters

def validate_idea(idea_name, idea_text, target_niche):
    """
    Searches historical records, calculates demand score, and generates a reports.
    """
    # 1. Semantic/Keyword search over database text
    all_records = database.get_all_scraped_text()
    
    # Simple semantic overlap search using keywords from the idea
    idea_keywords = extract_keywords(f"{idea_name} {idea_text} {target_niche}", num_words=10)
    matching_discussions = []
    
    for record in all_records:
        record_clean = clean_text(record["text"])
        # Score based on how many keywords from the idea match this record
        overlap = sum(1 for kw in idea_keywords if kw in record_clean)
        if overlap >= 1:
            matching_discussions.append((overlap, record))
            
    # Sort by overlap score and then reddit engagement score
    matching_discussions.sort(key=lambda x: (x[0], x[1]["score"]), reverse=True)
    sorted_matches = [item[1] for item in matching_discussions]
    
    # 2. Generate LLM Report & Demand Score
    report_data = llm_client.generate_validation_report_with_llm(
        idea_name,
        idea_text,
        target_niche,
        sorted_matches
    )
    
    # 3. Save to database
    report_id = database.save_idea_validation(
        idea_name,
        idea_text,
        target_niche,
        report_data["demand_score"],
        report_data["score_breakdown"],
        report_data["report_md"]
    )
    
    report_data["id"] = report_id
    report_data["idea_name"] = idea_name
    report_data["idea_text"] = idea_text
    report_data["target_niche"] = target_niche
    
    return report_data
