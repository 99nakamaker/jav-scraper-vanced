"""网页翻译接口"""
# 由于翻译服务不走代理，而且需要自己的错误处理机制，因此不通过base.py来管理网络请求
import time
import os
from typing import Union, List
import uuid
import random
import logging
from pydantic_core import Url
import requests
from hashlib import md5


__all__ = ['translate', 'translate_movie_info', 'test_translation_providers']


from javsp.config import Cfg, OpenAICompatibleProvider
from javsp.datatype import MovieInfo
from javsp.web.base import read_proxy
from javsp.func import is_chinese, is_japanese


logger = logging.getLogger(__name__)


def should_skip_translation(text: str, target_lang: str) -> bool:
    """
    检测文本是否已经是目标语言，如果是则跳过翻译

    Args:
        text: 要检测的文本
        target_lang: 目标语言代码 (e.g., 'zh_CN', 'zh_TW', 'en')

    Returns:
        True if translation should be skipped, False otherwise
    """
    if not text or len(text.strip()) == 0:
        return True

    # For Chinese target languages
    if target_lang.startswith('zh'):
        # If text is already Chinese and not Japanese, skip translation
        if is_chinese(text) and not is_japanese(text):
            return True

    return False


def translate_movie_info(info: MovieInfo):
    """根据配置翻译影片信息"""
    target_lang = Cfg().translator.target_language
    auto_detect = Cfg().translator.auto_detect_language

    # Print a clear separator for translation section
    print()  # Empty line for visual separation

    # 翻译标题
    if info.title and Cfg().translator.fields.title and info.ori_title is None:
        # Auto-detect if title is already in target language
        if auto_detect and should_skip_translation(info.title, target_lang):
            print(f"  ⊙ 标题已是{target_lang}，跳过翻译")
            print(f"     原文: {info.title}")
        else:
            # Show original text
            print(f"  → 原标题: {info.title}")
            result = translate_with_providers(info.title, info.actress, field_name='标题', target_lang=target_lang)
            if 'trans' in result:
                info.ori_title = info.title
                info.title = result['trans']
                # 如果有的话，附加断句信息
                if 'orig_break' in result:
                    setattr(info, 'ori_title_break', result['orig_break'])
                if 'trans_break' in result:
                    setattr(info, 'title_break', result['trans_break'])
                # Show translated title with provider
                provider_name = result.get('provider', 'unknown')
                print(f"  ✓ 译标题: {info.title} ({provider_name})")
            else:
                error_msg = result.get('error', 'Unknown error')
                print(f"  ✗ 标题翻译失败: {error_msg}")
                # Title is mandatory by default - but don't crash, just warn
                if Cfg().translator.title_mandatory:
                    logger.warning(f"标题翻译失败但继续处理: {error_msg}")

    # 翻译简介
    if info.plot and Cfg().translator.fields.plot:
        # Auto-detect if plot is already in target language
        if auto_detect and should_skip_translation(info.plot, target_lang):
            print(f"  ⊙ 简介已是{target_lang}，跳过翻译")
            plot_preview = info.plot[:60] + '...' if len(info.plot) > 60 else info.plot
            print(f"     原文: {plot_preview}")
        else:
            # Show original plot preview
            plot_preview = info.plot[:60] + '...' if len(info.plot) > 60 else info.plot
            print(f"  → 原简介: {plot_preview}")
            result = translate_with_providers(info.plot, info.actress, field_name='简介', target_lang=target_lang)
            if 'trans' in result:
                # 只有翻译过plot的影片才可能需要ori_plot属性，因此在运行时动态添加，而不添加到类型定义里
                setattr(info, 'ori_plot', info.plot)
                info.plot = result['trans']
                # Show preview of translated plot with provider
                plot_preview = info.plot[:60] + '...' if len(info.plot) > 60 else info.plot
                provider_name = result.get('provider', 'unknown')
                print(f"  ✓ 译简介: {plot_preview} ({provider_name})")
            else:
                error_msg = result.get('error', 'Unknown error')
                print(f"  ⊙ 简介翻译失败，继续处理: {error_msg}")

    return True



def translate_with_openai_compatible(texts: str, provider: OpenAICompatibleProvider, actress=None, target_lang='zh_CN') -> dict:
    """
    使用 OpenAI-compatible API 翻译文本
    支持 OpenAI、Gemini (via OpenAI SDK)、以及其他兼容 OpenAI 格式的服务

    Args:
        texts: 要翻译的文本
        provider: OpenAI兼容的服务提供商配置
        actress: 女优名列表（用于保护不被翻译）
        target_lang: 目标语言代码 (e.g., 'zh_CN', 'zh_TW', 'en')

    Returns:
        dict: 成功: {'trans': '译文'}, 失败: {'error_code': int, 'error_msg': str}
    """
    try:
        from openai import OpenAI
    except ImportError:
        return {"error_code": -10, "error_msg": "openai package not installed"}

    # Handle None actress parameter
    if actress is None:
        actress = []

    # Map language codes to human-readable names
    lang_map = {
        'zh_CN': 'simplified Chinese',
        'zh_TW': 'traditional Chinese',
        'zh-Hans': 'simplified Chinese',
        'zh-Hant': 'traditional Chinese',
        'en': 'English',
        'ja': 'Japanese',
        'ko': 'Korean',
    }
    target_lang_name = lang_map.get(target_lang, target_lang)

    try:
        client = OpenAI(
            api_key=provider.api_key,
            base_url=provider.base_url
        )

        # Protect actress names in the text
        protected_text = texts
        for name in actress:
            # Simple protection - could be enhanced
            protected_text = protected_text.replace(name, f"[ACTRESS:{name}]")

        response = client.chat.completions.create(
            model=provider.model,
            messages=[
                {
                    "role": "system",
                    "content": f"Translate the following Japanese paragraph into {target_lang_name} ({target_lang}), while leaving non-Japanese text, names, or text that does not look like Japanese untranslated. Reply with the translated text only, do not add any text that is not in the original content."
                },
                {
                    "role": "user",
                    "content": protected_text
                }
            ],
            temperature=0,
            max_tokens=1024,
        )

        # Check if response has content
        if not response.choices or not response.choices[0].message.content:
            return {"error_code": -12, "error_msg": "Empty response from API"}

        translated = response.choices[0].message.content.strip()

        # Restore actress names
        for name in actress:
            translated = translated.replace(f"[ACTRESS:{name}]", name)

        return {"trans": translated}
    except Exception as e:
        return {"error_code": -11, "error_msg": repr(e)}


def translate_with_providers(texts: str, actress=None, field_name='', target_lang='zh_CN') -> dict:
    """
    使用配置的 providers 列表按优先级顺序尝试翻译
    所有 providers 失败后自动回退到 Google 翻译

    Args:
        texts: 要翻译的文本
        actress: 女优名列表
        field_name: 字段名称（用于日志）
        target_lang: 目标语言代码

    Returns:
        dict: 成功: {'trans': '译文', 'provider': 'provider_name'}, 失败: {'error': 'error_msg'}
    """
    # Handle None actress parameter
    if actress is None:
        actress = []

    providers = Cfg().translator.providers

    # Try all configured providers first
    if providers:
        errors = []
        for idx, provider in enumerate(providers):
            provider_name = provider.name or f"{provider.model}"
            # Show which provider we're trying (visible to user)
            print(f"     [{idx+1}/{len(providers)}] 尝试 {provider_name}...", end='', flush=True)

            result = translate_with_openai_compatible(texts, provider, actress, target_lang)

            if 'trans' in result:
                result['provider'] = provider_name
                print(f" ✓")  # Success indicator on same line
                return result
            else:
                error_msg = result.get('error_msg', 'Unknown error')
                # Show short error on same line
                short_error = error_msg[:50] + '...' if len(error_msg) > 50 else error_msg
                print(f" ✗ {short_error}")
                errors.append(f"{provider_name}: {error_msg}")

        # All providers failed, log errors
        logger.warning(f"所有 OpenAI 兼容服务均失败: {'; '.join(errors)}")

    # Fallback to Google Translate
    print(f"     [fallback] 尝试 Google 翻译...", end='', flush=True)
    try:
        result = google_trans(texts, to=target_lang)
        # 经测试，翻译成功时会带有'sentences'字段；失败时不带，也没有故障码
        if 'sentences' in result:
            # Google会对句子分组，完整的译文需要自行拼接
            orig_break = [i['orig'] for i in result['sentences']]
            trans_break = [i['trans'] for i in result['sentences']]
            trans = ''.join(trans_break)
            print(f" ✓")
            return {'trans': trans, 'orig_break': orig_break, 'trans_break': trans_break, 'provider': 'Google'}
        else:
            error_msg = f"{result.get('error_code', 'unknown')}: {result.get('error_msg', 'unknown error')}"
            print(f" ✗ {error_msg}")
            return {'error': error_msg}
    except Exception as e:
        error_msg = repr(e)
        print(f" ✗ {error_msg}")
        return {'error': f"Google: {error_msg}"}


def test_translation_providers() -> List[dict]:
    """
    测试所有配置的翻译服务提供商
    用于启动时的 dry-run 检查

    Returns:
        List[dict]: 每个 provider 的测试结果
    """
    test_text = "こんにちは"
    target_lang = Cfg().translator.target_language
    results = []

    providers = Cfg().translator.providers
    if providers:
        for idx, provider in enumerate(providers):
            provider_name = provider.name or f"{provider.model}@{provider.base_url}"
            logger.info(f"测试翻译服务 [{idx+1}/{len(providers)}]: {provider_name}")

            result = translate_with_openai_compatible(test_text, provider, [], target_lang)

            if 'trans' in result:
                results.append({
                    'provider': provider_name,
                    'status': 'success',
                    'translation': result['trans']
                })
                logger.info(f"✓ {provider_name} 测试成功: {test_text} → {result['trans']}")
            else:
                results.append({
                    'provider': provider_name,
                    'status': 'failed',
                    'error': f"{result.get('error_code')}: {result.get('error_msg')}"
                })
                logger.warning(f"✗ {provider_name} 测试失败: {result.get('error_msg')}")
    
    # Always test Google Translate as fallback
    logger.info("测试 Google 翻译 (fallback)")
    try:
        result = google_trans(test_text, to=target_lang)
        if 'sentences' in result:
            trans = ''.join([i['trans'] for i in result['sentences']])
            results.append({
                'provider': 'Google',
                'status': 'success',
                'translation': trans
            })
            logger.info(f"✓ Google 测试成功: {test_text} → {trans}")
        else:
            results.append({
                'provider': 'Google',
                'status': 'failed',
                'error': 'No sentences in response'
            })
            logger.warning("✗ Google 测试失败")
    except Exception as e:
        results.append({
            'provider': 'Google',
            'status': 'failed',
            'error': repr(e)
        })
        logger.warning(f"✗ Google 测试失败: {repr(e)}")

    return results



_google_trans_wait = 60
def google_trans(texts, to='zh_CN'):
    """使用Google翻译文本（默认翻译为简体中文）"""
    # API: https://www.jianshu.com/p/ce35d89c25c3
    # client参数的选择: https://github.com/lmk123/crx-selection-translate/issues/223#issue-184432017
    global _google_trans_wait
    url = f"https://translate.google.com.hk/translate_a/single?client=gtx&dt=t&dj=1&ie=UTF-8&sl=auto&tl={to}&q={texts}"
    proxies = read_proxy()
    r = requests.get(url, proxies=proxies)
    while r.status_code == 429:
        logger.warning(f"HTTP {r.status_code}: {r.reason}: Google翻译请求超限，将等待{_google_trans_wait}秒后重试")
        time.sleep(_google_trans_wait)
        r = requests.get(url, proxies=proxies)
        if r.status_code == 429:
            _google_trans_wait += random.randint(60, 90)
    if r.status_code == 200:
        result = r.json()
    else:
        result = {'error_code': r.status_code, 'error_msg': r.reason}
    time.sleep(4) # Google翻译的API有QPS限制，因此需要等待一段时间
    return result


