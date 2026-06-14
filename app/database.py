import os
import sqlite3
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS subreddits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        last_scraped_at TEXT,
        tracked INTEGER DEFAULT 0
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subreddit_id INTEGER,
        reddit_post_id TEXT UNIQUE NOT NULL,
        title TEXT,
        body TEXT,
        score INTEGER,
        num_comments INTEGER,
        created_utc REAL,
        url TEXT,
        FOREIGN KEY (subreddit_id) REFERENCES subreddits(id)
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER,
        reddit_comment_id TEXT UNIQUE NOT NULL,
        body TEXT,
        score INTEGER,
        created_utc REAL,
        FOREIGN KEY (post_id) REFERENCES posts(id)
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS embeddings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_type TEXT NOT NULL, -- 'post' or 'comment'
        source_id INTEGER NOT NULL,
        vector TEXT NOT NULL, -- JSON array of floats
        model_name TEXT NOT NULL
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pain_point_clusters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        niche_query TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        representative_quotes TEXT NOT NULL, -- JSON string list of dicts
        avg_engagement REAL,
        frequency INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS idea_validations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        idea_name TEXT NOT NULL,
        idea_text TEXT NOT NULL,
        target_niche TEXT NOT NULL,
        demand_score INTEGER NOT NULL,
        score_breakdown TEXT NOT NULL, -- JSON string of component scores
        report_md TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    conn.commit()
    conn.close()

# Helper functions for database operations
def add_subreddit(name, tracked=0):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT OR IGNORE INTO subreddits (name, tracked) VALUES (?, ?)",
            (name.lower().strip(), tracked)
        )
        conn.commit()
        cursor.execute("SELECT id FROM subreddits WHERE name = ?", (name.lower().strip(),))
        row = cursor.fetchone()
        return row[0] if row else None
    finally:
        conn.close()

def update_subreddit_scrape_time(name):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE subreddits SET last_scraped_at = ? WHERE name = ?",
            (datetime.utcnow().isoformat(), name.lower().strip())
        )
        conn.commit()
    finally:
        conn.close()

def get_tracked_subreddits():
    conn = get_db_connection()
    try:
        rows = conn.execute("SELECT * FROM subreddits").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def save_posts_and_comments(subreddit_id, items):
    """
    items should be a list of dicts, each having post details and optionally comments.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        for item in items:
            # Save post
            cursor.execute(
                """
                INSERT OR REPLACE INTO posts 
                (subreddit_id, reddit_post_id, title, body, score, num_comments, created_utc, url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    subreddit_id,
                    item["reddit_post_id"],
                    item["title"],
                    item["body"],
                    item["score"],
                    item["num_comments"],
                    item["created_utc"],
                    item["url"]
                )
            )
            # Get internal post id
            cursor.execute("SELECT id FROM posts WHERE reddit_post_id = ?", (item["reddit_post_id"],))
            post_id = cursor.fetchone()[0]
            
            # Save comments
            if "comments" in item:
                for comment in item["comments"]:
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO comments 
                        (post_id, reddit_comment_id, body, score, created_utc)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            post_id,
                            comment["reddit_comment_id"],
                            comment["body"],
                            comment["score"],
                            comment["created_utc"]
                        )
                    )
        conn.commit()
    finally:
        conn.close()

def save_pain_point_clusters(niche_query, clusters):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        for c in clusters:
            cursor.execute(
                """
                INSERT INTO pain_point_clusters 
                (niche_query, title, description, representative_quotes, avg_engagement, frequency)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    niche_query.lower().strip(),
                    c["title"],
                    c["description"],
                    json.dumps(c["representative_quotes"]),
                    c.get("avg_engagement", 0.0),
                    c.get("frequency", 1)
                )
            )
        conn.commit()
    finally:
        conn.close()

def get_pain_point_clusters(niche_query=None):
    conn = get_db_connection()
    try:
        if niche_query:
            rows = conn.execute(
                "SELECT * FROM pain_point_clusters WHERE niche_query = ? ORDER BY frequency DESC, avg_engagement DESC",
                (niche_query.lower().strip(),)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM pain_point_clusters ORDER BY created_at DESC").fetchall()
        
        result = []
        for r in rows:
            d = dict(r)
            d["representative_quotes"] = json.loads(d["representative_quotes"])
            result.append(d)
        return result
    finally:
        conn.close()

def save_idea_validation(idea_name, idea_text, target_niche, demand_score, score_breakdown, report_md):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO idea_validations 
            (idea_name, idea_text, target_niche, demand_score, score_breakdown, report_md)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                idea_name,
                idea_text,
                target_niche,
                demand_score,
                json.dumps(score_breakdown),
                report_md
            )
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()

def get_idea_validations():
    conn = get_db_connection()
    try:
        rows = conn.execute("SELECT * FROM idea_validations ORDER BY created_at DESC").fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["score_breakdown"] = json.loads(d["score_breakdown"])
            result.append(d)
        return result
    finally:
        conn.close()

def get_all_scraped_text():
    """
    Returns all posts and comments from the database for global semantic searching.
    """
    conn = get_db_connection()
    try:
        posts = conn.execute("SELECT id, title, body, score, num_comments, url, 'post' as type FROM posts").fetchall()
        comments = conn.execute(
            "SELECT c.id, c.body, c.score, p.url, 'comment' as type FROM comments c JOIN posts p ON c.post_id = p.id"
        ).fetchall()
        
        results = []
        for p in posts:
            results.append({
                "id": p["id"],
                "type": p["type"],
                "text": f"{p['title'] or ''} {p['body'] or ''}".strip(),
                "score": p["score"],
                "url": p["url"],
                "num_comments": p["num_comments"]
            })
        for c in comments:
            results.append({
                "id": c["id"],
                "type": c["type"],
                "text": c["body"] or "",
                "score": c["score"],
                "url": c["url"],
                "num_comments": 0
            })
        return results
    finally:
        conn.close()
