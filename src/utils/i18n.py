"""
国际化支持模块
提供多语言支持功能，允许在不同语言之间切换
"""
import os
import json
from typing import Dict, Any, Optional
from .logger import get_logger

# 获取日志记录器
logger = get_logger("i18n")

# 支持的语言
SUPPORTED_LANGUAGES = ["en", "zh"]

# 默认语言
DEFAULT_LANGUAGE = "en"

# 当前语言
current_language = DEFAULT_LANGUAGE

# 语言文件目录
LOCALE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "locales")

# 语言文本缓存
_translations: Dict[str, Dict[str, str]] = {}


def set_language(lang_code: str) -> bool:
    """
    设置当前语言
    
    Args:
        lang_code: 语言代码 (例如 'en', 'zh')
    
    Returns:
        bool: 设置是否成功
    """
    global current_language
    
    if lang_code not in SUPPORTED_LANGUAGES:
        logger.warning(f"不支持的语言: {lang_code}, 可用语言: {', '.join(SUPPORTED_LANGUAGES)}")
        return False
    
    current_language = lang_code
    logger.info(f"语言已设置为: {lang_code}")
    return True


def get_current_language() -> str:
    """
    获取当前语言代码
    
    Returns:
        str: 当前语言代码
    """
    return current_language


def _load_language_file(lang_code: str) -> Dict[str, str]:
    """
    加载语言文件
    
    Args:
        lang_code: 语言代码
    
    Returns:
        Dict[str, str]: 语言文本字典
    """
    if lang_code in _translations:
        return _translations[lang_code]
    
    file_path = os.path.join(LOCALE_DIR, f"{lang_code}.json")
    
    try:
        # 确保语言文件目录存在
        if not os.path.exists(LOCALE_DIR):
            os.makedirs(LOCALE_DIR)
            
        # 如果语言文件不存在，创建空文件
        if not os.path.exists(file_path):
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
            logger.warning(f"创建了空语言文件: {file_path}")
            return {}
        
        # 加载语言文件
        with open(file_path, 'r', encoding='utf-8') as f:
            translations = json.load(f)
            _translations[lang_code] = translations
            return translations
            
    except Exception as e:
        logger.error(f"加载语言文件失败: {e}")
        return {}


def _(text_key: str, default: Optional[str] = None, **format_args) -> str:
    """
    获取当前语言的文本
    
    Args:
        text_key: 文本键
        default: 默认文本(如果未找到翻译)
        format_args: 格式化参数
    
    Returns:
        str: 翻译后的文本
    """
    # 加载当前语言文件
    translations = _load_language_file(current_language)
    
    # 获取翻译文本
    translated = translations.get(text_key)
    
    # 如果未找到翻译，使用默认文本或原始键
    if translated is None:
        # 如果是默认语言，并且未找到对应键值，则自动添加到语言文件中
        if current_language == DEFAULT_LANGUAGE and default is not None:
            add_translation(text_key, default)
            translated = default
        else:
            translated = default if default is not None else text_key
            # 记录缺失的翻译
            if current_language != DEFAULT_LANGUAGE:
                logger.debug(f"缺失翻译: {text_key}")
    
    # 应用格式化参数
    if format_args and '{' in translated:
        try:
            return translated.format(**format_args)
        except KeyError as e:
            logger.error(f"格式化文本失败: {e}, 文本: {translated}, 参数: {format_args}")
            return translated
    
    return translated


def add_translation(text_key: str, text_value: str, lang_code: Optional[str] = None) -> bool:
    """
    添加或更新翻译
    
    Args:
        text_key: 文本键
        text_value: 文本值
        lang_code: 语言代码(如果未指定，使用当前语言)
    
    Returns:
        bool: 是否成功
    """
    if lang_code is None:
        lang_code = current_language
    
    if lang_code not in SUPPORTED_LANGUAGES:
        logger.warning(f"不支持的语言: {lang_code}")
        return False
    
    # 加载语言文件
    translations = _load_language_file(lang_code)
    
    # 添加或更新翻译
    translations[text_key] = text_value
    _translations[lang_code] = translations
    
    # 保存到文件
    file_path = os.path.join(LOCALE_DIR, f"{lang_code}.json")
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(translations, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"保存语言文件失败: {e}")
        return False


def load_all_languages() -> None:
    """
    预加载所有支持的语言
    """
    for lang in SUPPORTED_LANGUAGES:
        _load_language_file(lang)
    logger.info(f"已加载所有语言: {', '.join(SUPPORTED_LANGUAGES)}") 