import psycopg2
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    host='localhost',
    database='news_db',
    user='postgres',
    password=os.environ.get('DB_PASSWORD'),
    port='5432'
)

# ── 1. SENTIMENT BY TOPIC ──────────────────────────────────────────────────
def plot_topic_sentiment():
    df = pd.read_sql("""
        SELECT topic, AVG(sentiment_score) as avg_score
        FROM articles
        GROUP BY topic
        ORDER BY avg_score DESC
    """, conn)

    colors = ['#22c55e' if x > 0.05 else '#ef4444' if x < -0.05 else '#f59e0b'
              for x in df['avg_score']]

    fig, ax = plt.subplots(figsize=(12, 6))
    bars = ax.barh(df['topic'][::-1], df['avg_score'][::-1], color=colors[::-1])
    ax.axvline(x=0, color='black', linewidth=0.8)
    ax.set_xlabel('Average Sentiment Score')
    ax.set_title('News Sentiment by Topic', fontsize=16, fontweight='bold')
    ax.bar_label(bars, fmt='%.3f', padding=3)
    plt.tight_layout()
    plt.savefig('topic_sentiment.png', dpi=150)
    plt.show()
    print('Saved topic_sentiment.png')

# ── 2. SENTIMENT BREAKDOWN PIE CHARTS ─────────────────────────────────────
def plot_sentiment_breakdown():
    df = pd.read_sql("""
        SELECT topic,
               SUM(CASE WHEN sentiment = 'positive' THEN 1 ELSE 0 END) as positive,
               SUM(CASE WHEN sentiment = 'negative' THEN 1 ELSE 0 END) as negative,
               SUM(CASE WHEN sentiment = 'neutral'  THEN 1 ELSE 0 END) as neutral
        FROM articles
        GROUP BY topic
        ORDER BY topic
    """, conn)

    topics = df['topic'].tolist()
    n = len(topics)
    cols = 3
    rows = (n + cols - 1) // cols

    fig, axes = plt.subplots(rows, cols, figsize=(15, rows * 4))
    axes = axes.flatten()

    for i, (_, row) in enumerate(df.iterrows()):
        sizes  = [row['positive'], row['negative'], row['neutral']]
        labels = ['Positive', 'Negative', 'Neutral']
        colors = ['#22c55e', '#ef4444', '#f59e0b']
        axes[i].pie(sizes, labels=labels, colors=colors, autopct='%1.0f%%', startangle=90)
        axes[i].set_title(row['topic'].title(), fontweight='bold')

    for j in range(i+1, len(axes)):
        axes[j].set_visible(False)

    plt.suptitle('Sentiment Breakdown by Topic', fontsize=16, fontweight='bold')
    plt.tight_layout()
    plt.savefig('sentiment_breakdown.png', dpi=150)
    plt.show()
    print('Saved sentiment_breakdown.png')

# ── 3. SENTIMENT OVER TIME ─────────────────────────────────────────────────
def plot_sentiment_over_time():
    df = pd.read_sql("""
        SELECT topic,
               DATE_TRUNC('hour', fetched_at) as hour,
               AVG(sentiment_score) as avg_score
        FROM articles
        GROUP BY topic, hour
        ORDER BY hour
    """, conn)

    df['hour'] = pd.to_datetime(df['hour'])

    # ← add this filter to only show last 7 days
    df = df[df['hour'] >= pd.Timestamp.now() - pd.Timedelta(days=7)]

    fig, ax = plt.subplots(figsize=(14, 6))
    colors = ['#5b4fcf','#22c55e','#ef4444','#f59e0b','#06b6d4','#ec4899','#8b5cf6']

    for i, (topic, group) in enumerate(df.groupby('topic')):
        ax.plot(group['hour'], group['avg_score'],
                label=topic, color=colors[i % len(colors)],
                linewidth=2, marker='o', markersize=6)

    ax.axhline(y=0, color='black', linewidth=0.8, linestyle='--')
    ax.set_xlabel('Time')
    ax.set_ylabel('Average Sentiment Score')
    ax.set_title('News Sentiment Over Time (Last 7 Days)', fontsize=16, fontweight='bold')
    ax.legend(loc='upper right', fontsize=8)
    plt.tight_layout()
    plt.savefig('sentiment_over_time.png', dpi=150)
    plt.show()
    print('Saved sentiment_over_time.png')

# ── 4. TOP SOURCES ─────────────────────────────────────────────────────────
def plot_top_sources():
    df = pd.read_sql("""
        SELECT source, COUNT(*) as articles,
               AVG(sentiment_score) as avg_sentiment
        FROM articles
        WHERE source != ''
        GROUP BY source
        ORDER BY articles DESC
        LIMIT 15
    """, conn)

    colors = ['#22c55e' if x > 0.05 else '#ef4444' if x < -0.05 else '#f59e0b'
              for x in df['avg_sentiment']]

    fig, ax = plt.subplots(figsize=(12, 7))
    bars = ax.barh(df['source'][::-1], df['articles'][::-1], color=colors[::-1])
    ax.set_xlabel('Number of Articles')
    ax.set_title('Top News Sources (coloured by sentiment)', fontsize=16, fontweight='bold')
    ax.bar_label(bars, padding=3)
    plt.tight_layout()
    plt.savefig('top_sources.png', dpi=150)
    plt.show()
    print('Saved top_sources.png')

# ── 5. MOST NEGATIVE vs POSITIVE TOPICS ───────────────────────────────────
def plot_pos_neg_comparison():
    df = pd.read_sql("""
        SELECT topic,
               AVG(positive) as avg_pos,
               AVG(negative) as avg_neg
        FROM articles
        GROUP BY topic
        ORDER BY avg_pos DESC
    """, conn)

    x = range(len(df))
    width = 0.35

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar([i - width/2 for i in x], df['avg_pos'], width, label='Positive', color='#22c55e')
    ax.bar([i + width/2 for i in x], df['avg_neg'], width, label='Negative', color='#ef4444')
    ax.set_xticks(x)
    ax.set_xticklabels(df['topic'], rotation=45, ha='right')
    ax.set_ylabel('Average Score')
    ax.set_title('Positive vs Negative Word Density by Topic', fontsize=16, fontweight='bold')
    ax.legend()
    plt.tight_layout()
    plt.savefig('pos_neg_comparison.png', dpi=150)
    plt.show()
    print('Saved pos_neg_comparison.png')

# ── RUN ALL ────────────────────────────────────────────────────────────────
print('Generating visualisations...')
plot_topic_sentiment()
plot_sentiment_breakdown()
plot_sentiment_over_time()
plot_top_sources()
plot_pos_neg_comparison()

conn.close()
print('\nAll charts saved!')