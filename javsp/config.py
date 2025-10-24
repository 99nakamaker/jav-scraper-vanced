from argparse import ArgumentParser, RawTextHelpFormatter
from enum import Enum
from typing import Dict, List, Literal, TypeAlias, Union
from confz import BaseConfig, CLArgSource, EnvSource, FileSource
from pydantic import ByteSize, Field, NonNegativeInt, PositiveInt, field_validator
from pydantic_extra_types.pendulum_dt import Duration
from pydantic_core import Url
from pathlib import Path
import os
import re

from javsp.lib import resource_path


def substitute_env_vars(content: str) -> str:
    """
    替换配置文件中的环境变量引用 ${VAR_NAME}

    Args:
        content: YAML 文件内容

    Returns:
        替换后的内容
    """
    def replace_var(match):
        var_name = match.group(1)
        # 从环境变量中获取值，如果不存在则保持原样
        return os.environ.get(var_name, match.group(0))

    # 匹配 ${VAR_NAME} 格式
    pattern = r'\$\{([A-Z_][A-Z0-9_]*)\}'
    return re.sub(pattern, replace_var, content)


def create_env_substituted_config(config_file: str) -> str:
    """
    创建一个临时配置文件，其中的环境变量已被替换

    Args:
        config_file: 原始配置文件路径

    Returns:
        临时配置文件路径
    """
    import tempfile

    # 读取原始文件内容
    with open(config_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 替换环境变量
    content = substitute_env_vars(content)

    # 写入临时文件
    tmp = tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.yml', delete=False)
    tmp.write(content)
    tmp.close()

    return tmp.name


class Scanner(BaseConfig):
    ignored_id_pattern: List[str]
    input_directory: Path | None = None
    filename_extensions: List[str]
    ignored_folder_name_pattern: List[str]
    minimum_size: ByteSize
    skip_nfo_dir: bool
    manual: bool
    auto_confirm: bool = True  # Auto-confirm movie IDs without user interaction

    @field_validator('input_directory', mode='before')
    @classmethod
    def convert_input_directory(cls, v):
        """Convert string to Path for environment variable support"""
        if v is None or v == '' or v == 'null':
            return None
        if isinstance(v, str):
            return Path(v)
        return v

class CrawlerID(str, Enum):
    airav = 'airav'
    avsox = 'avsox'
    avwiki = 'avwiki'
    dl_getchu = 'dl_getchu'
    fanza = 'fanza'
    fc2 = 'fc2'
    fc2fan = 'fc2fan'
    fc2ppvdb = 'fc2ppvdb'
    gyutto = 'gyutto'
    jav321 = 'jav321'
    javbus = 'javbus'
    javdb = 'javdb'
    javlib = 'javlib'
    javmenu = 'javmenu'
    mgstage = 'mgstage'
    njav = 'njav'
    prestige = 'prestige'
    arzon = 'arzon'
    arzon_iv = 'arzon_iv'

class Network(BaseConfig):
    proxy_server: Url | None
    retry: NonNegativeInt = 3
    timeout: Duration
    proxy_free: Dict[CrawlerID, Url]

class CrawlerSelect(BaseConfig):
    def items(self) -> List[tuple[str, list[CrawlerID]]]:
        return [
            ('normal', self.normal),
            ('fc2', self.fc2),
            ('cid', self.cid),
            ('getchu', self.getchu),
            ('gyutto', self.gyutto),
        ]

    def __getitem__(self, index) -> list[CrawlerID]:
        match index:
            case 'normal':
                return self.normal
            case 'fc2':
                return self.fc2
            case 'cid':
                return self.cid
            case 'getchu':
                return self.getchu
            case 'gyutto':
                return self.gyutto
        raise Exception("Unknown crawler type")

    normal: list[CrawlerID]
    fc2: list[CrawlerID]
    cid: list[CrawlerID]
    getchu: list[CrawlerID]
    gyutto: list[CrawlerID]

class MovieInfoField(str, Enum):
    dvdid = 'dvdid'
    cid = 'cid'
    url = 'url'
    plot = 'plot'
    cover = 'cover'
    big_cover = 'big_cover'
    genre = 'genre'
    genre_id = 'genre_id'
    genre_norm = 'genre_norm'
    score = 'score'
    title = 'title'
    ori_title = 'ori_title'
    magnet = 'magnet'
    serial = 'serial'
    actress = 'actress'
    actress_pics = 'actress_pics'
    director = 'director'
    duration = 'duration'
    producer = 'producer'
    publisher = 'publisher'
    uncensored = 'uncensored'
    publish_date = 'publish_date'
    preview_pics = 'preview_pics'
    preview_video = 'preview_video'

class UseJavDBCover(str, Enum):
    yes = "yes"
    no = "no"
    fallback = "fallback"

class Crawler(BaseConfig):
    selection: CrawlerSelect
    required_keys: list[MovieInfoField]
    hardworking: bool
    respect_site_avid: bool
    fc2fan_local_path: Path | None
    sleep_after_scraping: Duration
    use_javdb_cover: UseJavDBCover
    normalize_actress_name: bool

class MovieDefault(BaseConfig):
    title: str
    actress: str
    series: str
    director: str
    producer: str
    publisher: str

class PathSummarize(BaseConfig):
    output_folder_pattern: str
    basename_pattern: str
    length_maximum: PositiveInt
    length_by_byte: bool
    max_actress_count: PositiveInt = 10
    hard_link: bool

class TitleSummarize(BaseConfig):
    remove_trailing_actor_name: bool

class NFOSummarize(BaseConfig):
    basename_pattern: str
    title_pattern: str
    custom_genres_fields: list[str]
    custom_tags_fields: list[str]

class ExtraFanartSummarize(BaseConfig):
    enabled: bool
    scrap_interval: Duration

class SlimefaceEngine(BaseConfig):
    name: Literal['slimeface']

class CoverCrop(BaseConfig):
  engine: SlimefaceEngine | None
  on_id_pattern: list[str]

class CoverSummarize(BaseConfig):
    basename_pattern: str
    highres: bool
    add_label: bool
    crop: CoverCrop

class FanartSummarize(BaseConfig):
    basename_pattern: str

class Summarizer(BaseConfig):
    default: MovieDefault
    censor_options_representation: list[str]
    title: TitleSummarize
    move_files: bool = True
    path: PathSummarize
    nfo: NFOSummarize
    cover: CoverSummarize
    fanart: FanartSummarize
    extra_fanarts: ExtraFanartSummarize

# OpenAI-compatible provider for prioritized list
class OpenAICompatibleProvider(BaseConfig):
    """OpenAI-compatible translation provider (supports OpenAI, Gemini, etc.)"""
    base_url: str
    api_key: str
    model: str
    name: str = "openai-compatible"  # Optional friendly name for logging

class TranslateField(BaseConfig):
    title: bool
    plot: bool

class Translator(BaseConfig):
    # Prioritized list of OpenAI-compatible providers
    # Falls back to Google Translate if all providers fail
    providers: List[OpenAICompatibleProvider] = []
    fields: TranslateField
    # Target language for translation (e.g., 'zh_CN' for Simplified Chinese, 'zh_TW' for Traditional Chinese, 'en' for English)
    target_language: str = 'zh_CN'
    # Whether title translation is mandatory (if all providers fail for title, skip the movie)
    title_mandatory: bool = True
    # Auto-detect if text is already in target language and skip translation
    auto_detect_language: bool = True

class Other(BaseConfig):
    interactive: bool
    check_update: bool
    auto_update: bool

_temp_config_file = None  # Global to track temp file for cleanup

def get_config_source():
    global _temp_config_file

    # Load environment variables from .env file BEFORE setting up config sources
    try:
        from dotenv import load_dotenv, find_dotenv
        # Find and load .env file from current directory or parent directories
        dotenv_path = find_dotenv(usecwd=True)
        if dotenv_path:
            load_dotenv(dotenv_path, override=False)
        else:
            # Fallback: try loading from current directory
            load_dotenv(override=False)
    except Exception:
        pass  # dotenv is optional

    parser = ArgumentParser(prog='JavSP', description='汇总多站点数据的AV元数据刮削器', formatter_class=RawTextHelpFormatter)
    parser.add_argument('-c', '--config', help='使用指定的配置文件')
    args, _ = parser.parse_known_args()
    sources = []
    if args.config is None:
        args.config = resource_path('config.yml')

    # Create a temporary config file with environment variables substituted
    _temp_config_file = create_env_substituted_config(args.config)

    # Use the temporary file
    sources.append(FileSource(file=_temp_config_file))
    sources.append(EnvSource(prefix='JAVSP_', allow_all=True))
    sources.append(CLArgSource(prefix='o'))
    return sources

class Cfg(BaseConfig):
    scanner: Scanner
    network: Network
    crawler: Crawler
    summarizer: Summarizer
    translator: Translator
    other: Other
    CONFIG_SOURCES=get_config_source()


def cleanup_temp_config():
    """清理临时配置文件"""
    global _temp_config_file
    if _temp_config_file and os.path.exists(_temp_config_file):
        try:
            os.unlink(_temp_config_file)
        except:
            pass


# Register cleanup function to run on exit
import atexit
atexit.register(cleanup_temp_config)
