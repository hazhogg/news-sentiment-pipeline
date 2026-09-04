# News Sentiment Pipeline

An automated data engineering pipeline that fetches live news headlines across 7 topics, analyses sentiment using VADER NLP, and stores results in PostgreSQL for trend analysis.

## What it does

- Fetches live news headlines from NewsAPI across 7 topics
- Analyses sentiment of each headline (positive/negative/neutral) using VADER
- Stores articles and sentiment scores in PostgreSQL
- Tracks sentiment trends over time per topic
- Generates 5 visualisation charts
- Updates automatically every 6 hours

## Topics tracked

- Artificial Intelligence
- Technology
- Stock Market
- Climate Change
- Cryptocurrency
- Politics
- Sport

## Tech stack

- Python
- pandas
- PostgreSQL
- psycopg2
- NewsAPI
- VADER Sentiment Analysis
- schedule
- matplotlib
- Docker

## How sentiment works

VADER (Valence Aware Dictionary and sEntiment Reasoner) is specifically designed for social media and news text. It scores each headline from -1 (most negative) to +1 (most positive):

```
score >= 0.05   → positive 😊
score <= -0.05  → negative 😠
between         → neutral  😐
```

## Sample output

```
Topic                     Articles  Avg Score   Pos   Neg   Neu
-----------------------------------------------------------------
😊 stock market                  20      0.295    14     5     1
😊 technology                    20      0.258    11     4     5
😊 sport                         19      0.245    12     4     3
😊 artificial intelligence       20      0.202    10     8     2
😐 cryptocurrency                20     -0.021     7     9     4
😠 politics                      18     -0.103     8     9     1
😠 climate change                20     -0.224     7    12     1
```

## Database tables

### articles
Individual headlines with sentiment scores:

| Column | Description |
|---|---|
| topic | Search topic |
| title | Article headline |
| description | Article summary |
| source | News source (BBC, Guardian etc.) |
| published_at | Publication time |
| sentiment | positive / negative / neutral |
| sentiment_score | VADER compound score (-1 to +1) |
| positive | Positive word density |
| negative | Negative word density |
| neutral | Neutral word density |

### topic_summary
Aggregated sentiment per topic per run:

| Column | Description |
|---|---|
| topic | Search topic |
| fetched_at | When data was collected |
| article_count | Number of articles |
| avg_sentiment | Average sentiment score |
| positive_count | Number of positive articles |
| negative_count | Number of negative articles |
| neutral_count | Number of neutral articles |

## Setup

### Option 1 — Docker (recommended)

1. Get a free API key at https://newsapi.org/register

2. Clone the repo:
```bash
git clone https://github.com/yourusername/news-sentiment-pipeline.git
cd news-sentiment-pipeline
```

3. Create a `.env` file:
```
DB_PASSWORD=yourpassword
DB_HOST=db
NEWS_API_KEY=your_api_key
```

4. Run:
```bash
docker compose up --build
```

### Option 2 — Local

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file:
```
DB_PASSWORD=yourpassword
DB_HOST=localhost
NEWS_API_KEY=your_api_key
```

3. Run:
```bash
python news_pipeline.py
```

## Visualisations

```bash
python visualise.py
```

Generates 5 charts:
- Sentiment by topic (bar chart)
- Sentiment breakdown pie charts per topic
- Sentiment over time (line chart — improves with more runs)
- Top news sources by article count
- Positive vs negative word density comparison

## Example queries

```sql
-- Most negative headlines today
SELECT topic, title, sentiment_score
FROM articles
WHERE fetched_at >= NOW() - INTERVAL '24 hours'
ORDER BY sentiment_score ASC
LIMIT 10;

-- Average sentiment per topic over time
SELECT topic,
       DATE_TRUNC('day', fetched_at) as day,
       AVG(sentiment_score) as avg_score
FROM articles
GROUP BY topic, day
ORDER BY day, topic;

-- Most positive news source
SELECT source, AVG(sentiment_score) as avg_sentiment, COUNT(*) as articles
FROM articles
GROUP BY source
ORDER BY avg_sentiment DESC
LIMIT 10;

-- Topics getting more negative over time
SELECT topic,
       DATE_TRUNC('hour', fetched_at) as hour,
       AVG(sentiment_score) as avg_score
FROM articles
GROUP BY topic, hour
ORDER BY topic, hour;
```

## Schedule

Pipeline runs automatically every 6 hours:
```
00:00  → midnight update
06:00  → morning update
12:00  → midday update
18:00  → evening update
```

## Project structure

```
news-sentiment-pipeline/
├── news_pipeline.py   ← main ETL pipeline
├── visualise.py       ← chart generation
├── requirements.txt   ← dependencies
├── Dockerfile         ← Docker configuration
├── docker-compose.yml ← multi-container setup
├── .gitignore         ← excludes .env and charts
└── .env               ← API key and DB password (not pushed)
```

## Author

Harry
