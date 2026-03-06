# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Commands

### Dependency Management
- **Install dependencies**: This project uses uv for dependency management.
  ```bash
  uv sync
  ```
- **Install with dev dependencies**:
  ```bash
  uv sync --all-extras
  ```

### Running the Application
- **Run main application**:
  ```bash
  uv run javsp
  ```
- **Run with custom movie directory** (avoids manual prompt):
  ```bash
  uv run javsp /path/to/movie/folder
  ```
- **View available command-line arguments**:
  ```bash
  uv run javsp -h
  ```

### Testing
- **Run all tests**:
  ```bash
  uv run pytest
  ```
- **Run crawler tests only**:
  ```bash
  uv run pytest unittest/test_crawlers.py
  ```
- **Run tests for a specific crawler** (e.g., javbus):
  ```bash
  uv run pytest unittest/test_crawlers.py --only javbus
  ```
- **Run with verbose output**:
  ```bash
  uv run pytest -v
  ```
- **Run tests for proxy-free features**:
  ```bash
  uv run pytest unittest/test_proxyfree.py
  ```

### Code Quality
- **Lint code with flake8**:
  ```bash
  uv run flake8 javsp/
  ```

## Code Architecture

### High-Level Structure

JavSP is an AV metadata scraper that extracts movie IDs from filenames, fetches metadata from multiple websites, and organizes files with proper naming and metadata files for media servers (Emby, Jellyfin, Kodi).

**Core workflow**: Scan → Identify → Crawl (parallel) → Aggregate → Translate → Generate names → Download covers → Create NFO → Move files

### Key Components

#### Entry Point (`javsp/__main__.py`)
- **`entry()`**: Main entry point that orchestrates the entire workflow
- **`RunNormalMode()`**: Processes movies through the complete pipeline
- **`parallel_crawler()`**: Spawns threads to crawl multiple sites concurrently for each movie
- **`info_summary()`**: Aggregates data from multiple crawlers using configurable priority
- **`generate_names()`**: Generates file/folder names from templates with length constraints

#### Data Models (`javsp/datatype.py`)
- **`Movie`**: Represents a movie file with associated metadata (dvdid/cid, file paths, save paths)
- **`MovieInfo`**: Contains scraped metadata (title, actors, cover, plot, genres, etc.)

#### Web Crawlers (`javsp/web/`)
- **`base.py`**: Unified network request interface with proxy support, CloudFlare bypass
  - `Request` class: Customizable per-crawler with headers/cookies
  - `get_html()`, `post_html()`: Return lxml-parsed documents
- Each crawler module (e.g., `javbus.py`, `javdb.py`) implements:
  - `parse_data(info: MovieInfo)`: Populates MovieInfo object in-place
  - Some implement `parse_data_raw()` for custom retry logic
- **`translate.py`**: Translation services (Baidu, Bing, Google, OpenAI-compatible APIs)
  - Supports multiple providers with fallback priority
  - Auto-detects if text is already in target language

#### Configuration (`javsp/config.py`)
- Loads from `config.yml` using Pydantic models
- Supports environment variable substitution (e.g., `${API_KEY}` from `.env`)
- Key sections: scanner, network, crawler, summarizer, translator

#### Image Processing (`javsp/cropper/`)
- **`interface.py`**: Defines `Cropper` interface
- **`slimeface_crop.py`**: AI-based cropping using Slimeface for non-standard covers
- Watermark/label addition for subtitles/uncensored content

#### File Operations (`javsp/file.py`)
- **`scan_movies()`**: Recursively scans directories for video files
- Movie ID extraction from filenames with pattern matching
- Hardlink support for space-efficient file organization

#### NFO Generation (`javsp/nfo.py`)
- Creates XML metadata files compatible with Kodi/Emby/Jellyfin
- Includes plot, actors, genres, cover URLs, etc.

### Configuration

- **`config.yml`**: Main configuration (crawler selection, naming patterns, translation settings)
- **`.env`**: Store API keys here (copy from `.env.example`), referenced as `${VAR_NAME}` in config
- **`data/actress_alias.json`**: Actress name normalization map

### Testing

- Tests use pytest with custom fixtures (`unittest/conftest.py`)
- **Test data**: JSON files in `unittest/data/` named as `{avid} ({crawler}).json`
- `pytest_generate_tests()` dynamically generates test cases from data files
- `--only` flag filters tests to specific crawler

### Development Notes

- **Python version**: Requires 3.10-3.12
- **Encoding**: UTF-8 enforced throughout (see `sys.stdout.reconfigure()`)
- **Logging**: Uses Python logging with TQDM integration for progress bars
- **Parallel crawling**: Uses threading.Thread (not async) for I/O-bound web scraping
- **Crawler priority**: Data aggregation follows crawler order in `config.yml`
- **Error handling**: Custom exceptions in `javsp/web/exceptions.py` (SiteBlocked, MovieNotFoundError, etc.)
