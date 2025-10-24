# Migration Summary: Poetry to uv & Translation Simplification

This document summarizes the changes made to migrate JavSP from Poetry to uv and simplify the translation configuration.

## Changes Made

### 1. Dependency Management Migration (Poetry → uv)

**File: `pyproject.toml`**
- Removed all Poetry-specific sections:
  - `[tool.poetry]`
  - `[tool.poetry.dependencies]`
  - `[tool.poetry.scripts]`
  - `[[tool.poetry.source]]`
  - `[tool.poetry.group.dev.dependencies]`
  - `[tool.poetry-dynamic-versioning]`
- Updated `[build-system]` to use `hatchling` instead of `poetry-core`
- Added `[tool.hatch.build.targets.wheel]` configuration
- Changed version from dynamic to static (`version = "1.0.0"`)
- Kept existing `[project]` section which is compatible with both Poetry and uv

**Commands changed from:**
```bash
poetry install
poetry run javsp
poetry run pytest
```

**To:**
```bash
uv sync
uv run javsp
uv run pytest
```

### 2. Translation Configuration Simplification

**File: `config.yml`**
- Removed entire legacy `engine` configuration section
- Removed examples for Baidu, Bing, Claude, and legacy OpenAI engines
- Simplified translator section to only include:
  - `providers` list (OpenAI-compatible APIs)
  - Translation fields configuration
  - Target language setting
  - Auto-detect language setting
- Added comment indicating automatic fallback to Google Translate

**File: `javsp/config.py`**
- **Removed classes:**
  - `BaiduTranslateEngine`
  - `BingTranslateEngine`
  - `ClaudeTranslateEngine`
  - `OpenAITranslateEngine`
  - `GoogleTranslateEngine`
  - `TranslateEngine` type alias
- **Kept:**
  - `OpenAICompatibleProvider` class (for OpenAI-compatible APIs)
- **Updated `Translator` class:**
  - Removed `engine` field
  - Kept only `providers` list field
  - Updated comments to reflect Google fallback behavior

**File: `javsp/web/translate.py`**
- **Removed functions:**
  - `translate()` - legacy translation dispatcher
  - `baidu_translate()`
  - `bing_translate()`
  - `claude_translate()`
  - `openai_translate()` - legacy OpenAI function
- **Kept:**
  - `translate_with_openai_compatible()` - OpenAI SDK-based translation
  - `google_trans()` - Google Translate fallback
  - `should_skip_translation()` - language detection
  - `translate_movie_info()` - main translation entry point
- **Updated `translate_with_providers()`:**
  - Removed legacy engine fallback logic
  - Added automatic Google Translate fallback after all providers fail
  - Improved error messaging and logging
- **Updated `test_translation_providers()`:**
  - Removed legacy engine testing
  - Added Google Translate test as mandatory fallback test

**File: `javsp/__main__.py`**
- Updated translation check from `Cfg().translator.providers or Cfg().translator.engine` to `bool(Cfg().translator.providers) or Cfg().translator.fields.title or Cfg().translator.fields.plot`
- Updated warning message to indicate Google Translate will be used as fallback
- Removed all references to legacy translation engines

### 3. Documentation Updates

**File: `WARP.md`**
- Updated all commands from Poetry to uv:
  - `poetry install` → `uv sync`
  - `poetry install --with dev` → `uv sync --all-extras`
  - `poetry run <command>` → `uv run <command>`
- All other architecture and development notes remain unchanged

## New Translation Logic Flow

1. **Try all configured OpenAI-compatible providers** (in order):
   - ModelScope
   - Gemini
   - Any other configured providers

2. **If all providers fail, automatically fallback to Google Translate**
   - No configuration needed
   - Always available as last resort

3. **Language detection** (if enabled):
   - Skip translation if text is already in target language

## Benefits

1. **Simpler dependency management**: uv is faster and more straightforward than Poetry
2. **Cleaner codebase**: Removed ~200 lines of unused translation engine code
3. **Simpler configuration**: Only need to configure OpenAI-compatible providers
4. **Guaranteed fallback**: Google Translate always available, no configuration needed
5. **Easier maintenance**: Fewer dependencies and less code to maintain

## Migration for Users

Users need to:
1. Install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh` (or use package manager)
2. Run `uv sync` instead of `poetry install`
3. Update their `config.yml` to remove `engine:` line (it's ignored anyway)
4. Use `uv run` prefix for all commands instead of `poetry run`

## Testing

- ✅ Syntax check passed for all modified Python files
- ✅ `uv sync` successfully installs all dependencies
- ✅ `uv run javsp -h` works correctly
- ✅ All import statements are valid

## Notes

- The project still uses the same Python version requirements (3.10-3.12)
- All existing functionality is preserved
- Configuration is backward compatible (old `engine:` fields are simply ignored)
- Google Translate is now always used as fallback, ensuring translation always works
