# NYC Crashes Data Caching & Auto-Update System

## Overview

The data pipeline has been updated to pull data directly from the NYC official API and maintain a local cache with automatic updates.

## Features

### 1. **Automatic Caching**

- Data is cached locally at: `data/nyc_crashes_cached.csv`
- Cache metadata stored at: `data/nyc_crashes_meta.json`
- Timestamp recorded when data was pulled

### 2. **Automatic Updates**

- When online and cache is **older than 7 days**, automatically updates from API
- When offline, uses cached data (if available)
- Force updates possible with `nyc:update` shortcut

### 3. **Smart Connectivity Detection**

- Detects internet availability before attempting downloads
- Falls back to cache gracefully when offline
- SSL certificate issues handled automatically

## Usage

### Command Line (`main.py`)

```bash
# Default: Use NYC API with caching (recommended)
python3 main.py

# Force update from API
python3 main.py --file nyc:update

# Use cached data only (no internet needed)
python3 main.py --file nyc:cached

# Use local file
python3 main.py path/to/file.csv

# Use sample data
python3 main.py sample
```

### Python API (`Datapull.py`)

```python
from Datapull import load_and_preview, pull_and_cache_nyc_crashes

# Load with automatic caching
data, summary = load_and_preview("nyc", preview=10)

# Manual cache control
cache_path, metadata = pull_and_cache_nyc_crashes(force_update=False)
print(metadata)
# Output:
# {
#   'cache_timestamp': '2025-12-30T17:00:55.086067',
#   'source': 'api',
#   'last_updated_from_api': '2025-12-30T17:00:55.086144',
#   'url': 'https://data.cityofnewyork.us/resource/h9gi-nx95.csv'
# }
```

## Shortcuts Supported

| Shortcut        | Behavior                                                   |
| --------------- | ---------------------------------------------------------- |
| `nyc` (default) | Download from API if cache doesn't exist or is >7 days old |
| `nyc:latest`    | Same as `nyc`                                              |
| `nyc:cached`    | Use cache only (error if no cache exists)                  |
| `nyc:update`    | Force download from API, overwrite cache                   |
| `sample`        | Use built-in sample data                                   |
| `/path/to/file` | Load from local file                                       |

## Data Source

**URL:** `https://data.cityofnewyork.us/resource/h9gi-nx95.csv`  
**Dataset:** NYC Motor Vehicle Collisions - Crashes  
**Owner:** NYC Department of Transportation (DOT)  
**Update Frequency:** Real-time (updated as collisions are reported)

## Cache Files

### `data/nyc_crashes_cached.csv`

- Raw CSV data pulled from NYC API
- Contains ~1000 rows of crash data
- Includes columns: crash_date, crash_time, borough, latitude, longitude, on_street_name, etc.

### `data/nyc_crashes_meta.json`

- Metadata about the cache
- Fields:
  - `cache_timestamp`: When data was cached
  - `source`: "api" (pulled from API) or "cache" (using existing)
  - `last_updated_from_api`: Last successful API pull timestamp
  - `url`: Source API endpoint

## Behavior Examples

### Scenario 1: First Run (No Cache)

```
→ Check internet: ONLINE
→ No cache exists
→ Download from API
→ Save to data/nyc_crashes_cached.csv
→ Continue with analysis
```

### Scenario 2: Recent Cache, Online

```
→ Check internet: ONLINE
→ Cache exists and is 2 days old
→ Cache is recent (< 7 days)
→ Use cached data
→ Continue with analysis
```

### Scenario 3: Stale Cache, Online

```
→ Check internet: ONLINE
→ Cache exists but is 10 days old
→ Cache is stale (> 7 days)
→ Download from API
→ Update cache
→ Continue with analysis
```

### Scenario 4: Offline, Cache Exists

```
→ Check internet: OFFLINE
→ Cache exists
→ Use cached data
→ Continue with analysis
```

### Scenario 5: Offline, No Cache

```
→ Check internet: OFFLINE
→ No cache exists
→ ERROR: No data source available
```

## Technical Details

### SSL/Certificate Handling

- Automatically disables SSL verification if needed
- Works around macOS certificate issues
- Secure for development; production should use proper certificates

### Pandas Fallback

- Uses pandas when available (faster)
- Falls back to csv module if pandas unavailable
- Automatically combines crash_date + crash_time into crash_datetime

### Error Handling

- Network failures: Falls back to cache
- Parsing errors: Skips problematic lines
- Missing files: Clear error messages

## Future Enhancements

- [ ] Cache size management (limit to N MB)
- [ ] Incremental updates (only new records)
- [ ] Data validation/quality checks
- [ ] Multiple data source support
- [ ] Cache expiration policies (per dataset)
