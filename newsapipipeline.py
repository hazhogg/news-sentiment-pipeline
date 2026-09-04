import requests
import psycopg2
import pandas as pd
import os
import schedule
import time
import warnings
from datetime import datetime
from dotenv import load_dotenv
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

warnings.filterwarnings('ignore')
load_dotenv()

# ── CONFIG ─────────────────────────────────────────────────────────────────
NEWS_API_KEY = os.environ.get('NEWS_API_KEY')
BASE_URL = 'https://newsapi.org/v2/everything'

TOPICS = [
    'artificial intelligence',
    'technology',
    'stock market',
    'climate change',
    'cryptocurrency',
    'politics',
    'sport',
]

DB_CONFIG = {
    'host':     os.environ.get('DB_HOST', 'localhost'),
    'database': 'news_db',
    'user':     'postgres',
    'password': os.environ.get('DB_PASSWORD'),
    'port':     '5432'
}

analyzer = SentimentIntensityAnalyzer()

# ── SETUP DATABASE ─────────────────────────────────────────────────────────
def setup_database(conn):
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id           SERIAL PRIMARY KEY,
            article_id   VARCHAR(255) UNIQUE,
            topic        VARCHAR(100),
            title        TEXT,
            description  TEXT,
            source       VARCHAR(100),
            author       VARCHAR(100),
            published_at TIMESTAMP,
            url          TEXT,
            sentiment    VARCHAR(20),
            sentiment_score NUMERIC,
            positive     NUMERIC,
            negative     NUMERIC,
            neutral      NUMERIC,
            fetched_at   TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS topic_summary (
            id              SERIAL PRIMARY KEY,
            topic           VARCHAR(100),
            fetched_at      TIMESTAMP,
            article_count   INTEGER,
            avg_sentiment   NUMERIC,
            positive_count  INTEGER,
            negative_count  INTEGER,
            neutral_count   INTEGER
        )
    """)

    conn.commit()
    print('Database ready!')

# ── EXTRACT ────────────────────────────────────────────────────────────────
def extract(topic):
    print(f'  Extracting {topic}...')
    response = requests.get(BASE_URL, params={
        'q':        topic,
        'language': 'en',
        'pageSize': 20,
        'sortBy':   'publishedAt',
        'apiKey':   NEWS_API_KEY
    })
    if response.status_code != 200:
        raise Exception(f'API error: {response.status_code}')
    return response.json()

# ── TRANSFORM ──────────────────────────────────────────────────────────────
def analyse_sentiment(text):
    """Use VADER to score sentiment of text"""
    if not text:
        return 'neutral', 0.0, 0.0, 0.0, 0.0
    scores = analyzer.polarity_scores(text)
    compound = scores['compound']
    if compound >= 0.05:
        sentiment = 'positive'
    elif compound <= -0.05:
        sentiment = 'negative'
    else:
        sentiment = 'neutral'
    return sentiment, round(compound, 4), round(scores['pos'], 4), round(scores['neg'], 4), round(scores['neu'], 4)

def transform(data, topic):
    print(f'  Transforming {topic}...')
    rows = []
    for article in data['articles']:
        # Combine title and description for better sentiment
        text = f"{article.get('title', '')} {article.get('description', '')}"
        sentiment, score, pos, neg, neu = analyse_sentiment(text)

        # Create unique ID from URL
        url = article.get('url', '')
        article_id = str(hash(url))[-12:]

        rows.append({
            'article_id':      article_id,
            'topic':           topic,
            'title':           article.get('title', ''),
            'description':     article.get('description', ''),
            'source':          article.get('source', {}).get('name', ''),
            'author':          article.get('author', ''),
            'published_at':    article.get('publishedAt', ''),
            'url':             url,
            'sentiment':       sentiment,
            'sentiment_score': score,
            'positive':        pos,
            'negative':        neg,
            'neutral':         neu,
            'fetched_at':      datetime.now(),
        })
    return pd.DataFrame(rows)

# ── LOAD ───────────────────────────────────────────────────────────────────
def load(df, conn):
    print(f'  Loading {len(df)} articles...')
    cursor = conn.cursor()
    for _, row in df.iterrows():
        try:
            cursor.execute("""
                INSERT INTO articles
                (article_id, topic, title, description, source, author,
                 published_at, url, sentiment, sentiment_score,
                 positive, negative, neutral, fetched_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (article_id) DO NOTHING
            """, (
                row['article_id'], row['topic'], row['title'],
                row['description'], row['source'], row['author'],
                row['published_at'], row['url'], row['sentiment'],
                row['sentiment_score'], row['positive'],
                row['negative'], row['neutral'], row['fetched_at']
            ))
        except Exception as e:
            print(f'  Skipping row: {e}')
            continue

def load_summary(df, topic, conn):
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO topic_summary
            (topic, fetched_at, article_count, avg_sentiment,
             positive_count, negative_count, neutral_count)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (
            topic, datetime.now(), len(df),
            round(df['sentiment_score'].mean(), 4),
            len(df[df['sentiment'] == 'positive']),
            len(df[df['sentiment'] == 'negative']),
            len(df[df['sentiment'] == 'neutral']),
        ))
    except Exception as e:
        print(f'  Summary error: {e}')

# ── MAIN PIPELINE ──────────────────────────────────────────────────────────
def run_pipeline():
    print(f'\n[{datetime.now().strftime("%H:%M:%S")}] Running news sentiment pipeline...')
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True

        all_summaries = []

        for topic in TOPICS:
            print(f'\nTopic: {topic}')
            try:
                raw  = extract(topic)
                df   = transform(raw, topic)
                load(df, conn)
                load_summary(df, topic, conn)

                avg_score = df['sentiment_score'].mean()
                pos = len(df[df['sentiment'] == 'positive'])
                neg = len(df[df['sentiment'] == 'negative'])
                neu = len(df[df['sentiment'] == 'neutral'])

                all_summaries.append({
                    'topic': topic,
                    'articles': len(df),
                    'avg_score': avg_score,
                    'positive': pos,
                    'negative': neg,
                    'neutral': neu,
                })

                # Small delay to respect rate limits
                time.sleep(1)

            except Exception as e:
                print(f'  Error: {e}')
                continue

        # Print summary
        print('\n--- Sentiment Summary ---')
        print(f'{"Topic":<25} {"Articles":>8} {"Avg Score":>10} {"Pos":>5} {"Neg":>5} {"Neu":>5}')
        print('-' * 65)
        for s in sorted(all_summaries, key=lambda x: x['avg_score'], reverse=True):
            emoji = '😊' if s['avg_score'] > 0.05 else '😠' if s['avg_score'] < -0.05 else '😐'
            print(f"{emoji} {s['topic']:<23} {s['articles']:>8} {s['avg_score']:>10.3f} {s['positive']:>5} {s['negative']:>5} {s['neutral']:>5}")

        # Most negative headlines
        print('\n--- Most Negative Headlines ---')
        negative = pd.read_sql("""
            SELECT DISTINCT ON (title) topic, title, sentiment_score
            FROM articles
            WHERE fetched_at >= NOW() - INTERVAL '1 hour'
            ORDER BY title, sentiment_score ASC
            LIMIT 5
        """, conn)
        for _, row in negative.iterrows():
            print(f"  [{row['topic']}] {row['title'][:80]} ({row['sentiment_score']})")

        # Most positive headlines
        print('\n--- Most Positive Headlines ---')
        positive = pd.read_sql("""
            SELECT DISTINCT ON (title) topic, title, sentiment_score
            FROM articles
            WHERE fetched_at >= NOW() - INTERVAL '1 hour'
            ORDER BY title, sentiment_score DESC
            LIMIT 5
        """, conn)
        for _, row in positive.iterrows():
            print(f"  [{row['topic']}] {row['title'][:80]} ({row['sentiment_score']})")

        conn.close()
        print('\n✅ Pipeline complete!')

    except Exception as e:
        print(f'❌ Pipeline failed: {e}')

# ── RUN ────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    # Create database
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    try:
        setup_conn = psycopg2.connect(
            host='localhost', database='postgres',
            user='postgres', password=os.environ.get('DB_PASSWORD'), port='5432'
        )
        setup_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        setup_conn.cursor().execute('CREATE DATABASE news_db')
        setup_conn.close()
        print('news_db created!')
    except Exception as e:
        print(f'Database note: {e}')

    conn = psycopg2.connect(**DB_CONFIG)
    setup_database(conn)
    conn.close()

    run_pipeline()

    # Update every 6 hours
    schedule.every(6).hours.do(run_pipeline)

    print('\nScheduler running — updates every 6 hours.')
    print('Press Ctrl+C to stop.\n')

    while True:
        schedule.run_pending()
        time.sleep(60)