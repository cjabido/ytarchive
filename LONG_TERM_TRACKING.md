# Long-Term YouTube History Tracking Guide

This guide covers how to maintain a long-term database of your YouTube viewing history with automated imports and deduplication.

## Quick Start

### 1. Initial Import

Import your existing watch history:

```bash
python3 import_to_db.py watch-history.html
```

This creates `youtube_history.db` with all your videos, posts, and channels.

### 2. Query Your Data

```bash
# Overall statistics
python3 query_db.py stats

# Top 20 most watched channels
python3 query_db.py top

# Recent activity (last 7 days)
python3 query_db.py recent

# Search for videos
python3 query_db.py search "machine learning"

# View timeline for a specific channel
python3 query_db.py channel "LilyPichu"

# Export to CSV for analysis
python3 query_db.py export my_history.csv
```

## Automated Scheduled Imports

### Strategy 1: Manual Periodic Exports (Recommended)

Since Google doesn't provide an API for watch history, you'll need to periodically export from Google Takeout:

1. **Export from Google Takeout** (monthly/quarterly)
   - Go to https://takeout.google.com
   - Select only "YouTube and YouTube Music" → "history"
   - Download when ready

2. **Import the new export**
   ```bash
   python3 import_to_db.py ~/Downloads/watch-history.html
   ```

3. **Duplicates are automatically handled** - the script will skip entries that already exist

### Strategy 2: Automated Export with Browser Automation (Advanced)

If you want fully automated tracking, you can use browser automation:

**Option A: Using Selenium (requires setup)**

Create a script that:
1. Logs into Google Takeout
2. Requests YouTube history export
3. Downloads the file when ready
4. Runs the import script

**Option B: Using Chrome DevTools Protocol**

Use Puppeteer or Playwright to automate the export process.

### Strategy 3: Scheduled Import Script

Create a cron job or scheduled task:

**On macOS/Linux (crontab):**

```bash
# Edit crontab
crontab -e

# Add this line to run weekly on Sundays at 2 AM
0 2 * * 0 cd /path/to/youtube-history && python3 import_to_db.py ~/Downloads/watch-history.html >> import.log 2>&1
```

**On Windows (Task Scheduler):**

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger (e.g., weekly)
4. Action: Run `python3 import_to_db.py watch-history.html`

## Database Maintenance

### Backup Your Database

Always backup your database before major operations:

```bash
# Simple copy
cp youtube_history.db youtube_history_backup_$(date +%Y%m%d).db

# Or use SQLite backup command
sqlite3 youtube_history.db ".backup youtube_history_backup.db"
```

### Database Location

By default, the database is created in the current directory. For long-term tracking, consider:

```bash
# Store in a dedicated location
python3 import_to_db.py watch-history.html -d ~/Documents/youtube_history.db

# Or create an alias
alias yt-import='python3 /path/to/import_to_db.py -d ~/Documents/youtube_history.db'
alias yt-query='python3 /path/to/query_db.py -d ~/Documents/youtube_history.db'
```

### Cleanup Old Imports

If you keep multiple HTML exports, clean them up after importing:

```bash
# Archive old exports
mkdir -p archives
mv watch-history-*.html archives/

# Or delete after successful import
python3 import_to_db.py watch-history.html && rm watch-history.html
```

## Advanced Analytics

### Using SQL Directly

The database is SQLite, so you can query it directly:

```bash
sqlite3 youtube_history.db
```

**Example queries:**

```sql
-- Most watched channels by month
SELECT
    strftime('%Y-%m', watched_at) as month,
    c.channel_name,
    COUNT(*) as videos
FROM videos v
JOIN channels c ON v.channel_id = c.channel_id
GROUP BY month, c.channel_name
ORDER BY month DESC, videos DESC;

-- Viewing patterns by hour of day
SELECT
    strftime('%H', watched_at) as hour,
    COUNT(*) as video_count
FROM videos
GROUP BY hour
ORDER BY hour;

-- Binge watching detection (3+ videos from same channel in 1 hour)
SELECT
    c.channel_name,
    DATE(v.watched_at) as date,
    strftime('%H:00', v.watched_at) as hour,
    COUNT(*) as videos
FROM videos v
JOIN channels c ON v.channel_id = c.channel_id
GROUP BY c.channel_id, date, hour
HAVING videos >= 3
ORDER BY videos DESC;

-- Discover new channels by month
SELECT
    strftime('%Y-%m', first_seen) as month,
    COUNT(*) as new_channels
FROM channels
GROUP BY month
ORDER BY month DESC;
```

### Export for External Analysis

```bash
# Export to CSV for Excel/Google Sheets
python3 query_db.py export youtube_data.csv

# Export database to JSON
sqlite3 youtube_history.db ".mode json" ".once data.json" "SELECT * FROM videos"
```

### Integration with Data Analysis Tools

**Python/Pandas:**

```python
import sqlite3
import pandas as pd

conn = sqlite3.connect('youtube_history.db')

# Load data
videos = pd.read_sql('SELECT * FROM videos', conn)
channels = pd.read_sql('SELECT * FROM channels', conn)

# Analyze
print(videos['watched_at'].describe())
print(videos.groupby('channel_id').size().sort_values(ascending=False).head(10))
```

**R:**

```r
library(DBI)
library(RSQLite)

con <- dbConnect(RSQLite::SQLite(), "youtube_history.db")
videos <- dbGetQuery(con, "SELECT * FROM videos")

# Analyze viewing patterns
library(ggplot2)
ggplot(videos, aes(x=watched_at)) + geom_histogram()
```

## Best Practices

### 1. Regular Exports

- **Monthly exports** for active users (100+ videos/month)
- **Quarterly exports** for moderate users
- **Yearly exports** for light users

### 2. Verify Imports

After each import, check the stats:

```bash
python3 query_db.py stats
```

Compare against previous totals to ensure new data was imported.

### 3. Database Size Management

The database is lightweight, but for very long histories:

```bash
# Check database size
ls -lh youtube_history.db

# Vacuum to reclaim space (after deletions)
sqlite3 youtube_history.db "VACUUM;"

# Check table sizes
sqlite3 youtube_history.db "SELECT
    'videos' as table_name, COUNT(*) as count FROM videos
    UNION ALL
    SELECT 'posts', COUNT(*) FROM posts
    UNION ALL
    SELECT 'channels', COUNT(*) FROM channels;"
```

### 4. Data Privacy

Your viewing history is personal data:

- Store database in encrypted folder/drive
- Don't commit database to public Git repositories
- Add to `.gitignore`:
  ```
  *.db
  *.db-journal
  watch-history*.html
  ```
- Regular backups to secure location

## Troubleshooting

### Issue: Duplicates being imported

**Cause:** Timestamp format mismatch

**Solution:** The script uses (video_id, timestamp) as unique key. If timestamps are different (e.g., timezone changes), duplicates may occur.

**Fix:** Add more robust deduplication or check timestamp parsing.

### Issue: Missing recent videos

**Cause:** Export delay from Google Takeout

**Solution:** Google Takeout may not include very recent activity. Wait 24-48 hours after watching before exporting.

### Issue: Database locked

**Cause:** Multiple processes accessing database

**Solution:**
```bash
# Check for lock
lsof youtube_history.db

# If stuck, remove journal file
rm youtube_history.db-journal
```

## Migration and Portability

### Moving to Another Computer

```bash
# Copy just the database
scp youtube_history.db user@newcomputer:~/

# Or copy everything
tar -czf youtube_tracking.tar.gz *.py *.db *.md
scp youtube_tracking.tar.gz user@newcomputer:~/
```

### Upgrading Database Schema

If the schema changes in future versions:

```bash
# Backup first
cp youtube_history.db youtube_history_old.db

# Export to SQL
sqlite3 youtube_history.db .dump > backup.sql

# Re-import with new schema
python3 import_to_db.py watch-history.html -d youtube_history_new.db
```

## Additional Features to Consider

### 1. Add Categories/Tags

Extend the database to tag videos:

```sql
CREATE TABLE tags (
    id INTEGER PRIMARY KEY,
    video_id INTEGER,
    tag TEXT,
    FOREIGN KEY (video_id) REFERENCES videos(id)
);
```

### 2. Track Watch Time

If you have watch time data, add a column:

```sql
ALTER TABLE videos ADD COLUMN watch_duration_seconds INTEGER;
```

### 3. Sentiment/Notes

Add personal notes about videos:

```sql
CREATE TABLE notes (
    video_id INTEGER PRIMARY KEY,
    note TEXT,
    rating INTEGER,
    FOREIGN KEY (video_id) REFERENCES videos(id)
);
```

## Resources

- **SQLite Documentation**: https://www.sqlite.org/docs.html
- **Google Takeout**: https://takeout.google.com
- **Cron Tutorial**: https://crontab.guru

## Next Steps

1. Run your first import
2. Set up a monthly calendar reminder to export from Google Takeout
3. Create a backup strategy
4. Explore the analytics queries
5. Consider adding custom tags or categories for your most-watched content
