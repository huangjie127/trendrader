# coding=utf-8
"""
AI 翻译器模块

对推送内容进行多语言翻译
使用共享的 AI 模型配置
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class TranslationResult:
    """翻译结果"""
    translated_text: str = ""       # 翻译后的文本
    original_text: str = ""         # 原始文本
    success: bool = False           # 是否成功
    error: str = ""                 # 错误信息


@dataclass
class BatchTranslationResult:
    """批量翻译结果"""
    results: List[TranslationResult] = field(default_factory=list)
    success_count: int = 0
    fail_count: int = 0
    total_count: int = 0


class AITranslator:
    """AI 翻译器"""

    def __init__(self, translation_config: Dict[str, Any], ai_config: Dict[str, Any]):
        """
        初始化 AI 翻译器

        Args:
            translation_config: AI 翻译配置 (AI_TRANSLATION)
            ai_config: AI 模型共享配置 (AI)
        """
        self.translation_config = translation_config
        self.ai_config = ai_config

        # 翻译配置
        self.enabled = translation_config.get("ENABLED", False)
        self.target_language = translation_config.get("LANGUAGE", "English")

        # 从共享配置获取模型参数
        self.api_key = ai_config.get("API_KEY") or os.environ.get("AI_API_KEY", "")
        self.provider = ai_config.get("PROVIDER", "deepseek")
        self.model = ai_config.get("MODEL", "deepseek-chat")
        self.base_url = ai_config.get("BASE_URL", "")
        self.timeout = ai_config.get("TIMEOUT", 90)

        # AI 参数配置
        self.temperature = ai_config.get("TEMPERATURE", 1.0)
        self.max_tokens = ai_config.get("MAX_TOKENS", 5000)

        # 额外参数
        self.extra_params = ai_config.get("EXTRA_PARAMS", {})
        if isinstance(self.extra_params, str) and self.extra_params.strip():
            try:
                self.extra_params = json.loads(self.extra_params)
            except json.JSONDecodeError:
                print(f"[翻译] 解析 extra_params 失败，将忽略: {self.extra_params}")
                self.extra_params = {}

        if not isinstance(self.extra_params, dict):
            self.extra_params = {}

        # 加载提示词模板
        self.system_prompt, self.user_prompt_template = self._load_prompt_template(
            translation_config.get("PROMPT_FILE", "ai_translation_prompt.txt")
        )

    def _load_prompt_template(self, prompt_file: str) -> tuple:
        """加载提示词模板"""
        config_dir = Path(__file__).parent.parent.parent / "config"
        prompt_path = config_dir / prompt_file

        if not prompt_path.exists():
            print(f"[翻译] 提示词文件不存在: {prompt_path}")
            return "", ""

        content = prompt_path.read_text(encoding="utf-8")

        # 解析 [system] 和 [user] 部分
        system_prompt = ""
        user_prompt = ""

        if "[system]" in content and "[user]" in content:
            parts = content.split("[user]")
            system_part = parts[0]
            user_part = parts[1] if len(parts) > 1 else ""

            if "[system]" in system_part:
                system_prompt = system_part.split("[system]")[1].strip()

            user_prompt = user_part.strip()
        else:
            user_prompt = content

        return system_prompt, user_prompt

    def translate(self, text: str) -> TranslationResult:
        """
        翻译单条文本

        Args:
            text: 要翻译的文本

        Returns:
            TranslationResult: 翻译结果
        """
        result = TranslationResult(original_text=text)

        if not self.enabled:
            result.error = "翻译功能未启用"
            return result

        if not self.api_key:
            result.error = "未配置 AI API Key"
            return result

        if not text or not text.strip():
            result.translated_text = text
            result.success = True
            return result

        try:
            # 构建提示词
            user_prompt = self.user_prompt_template
            user_prompt = user_prompt.replace("{target_language}", self.target_language)
            user_prompt = user_prompt.replace("{content}", text)

            # 调用 AI API
            response = self._call_ai_api(user_prompt)
            result.translated_text = response.strip()
            result.success = True

        except Exception as e:
            import requests
            error_type = type(e).__name__
            error_msg = str(e)

            if isinstance(e, requests.exceptions.Timeout):
                result.error = f"翻译请求超时（{self.timeout}秒）"
            elif isinstance(e, requests.exceptions.ConnectionError):
                result.error = f"无法连接到 AI API"
            elif isinstance(e, requests.exceptions.HTTPError):
                status_code = e.response.status_code if hasattr(e, 'response') and e.response else "未知"
                if status_code == 401:
                    result.error = "API 认证失败"
                elif status_code == 429:
                    result.error = "API 请求频率过高"
                else:
                    result.error = f"API 错误 (HTTP {status_code})"
            else:
                if len(error_msg) > 100:
                    error_msg = error_msg[:100] + "..."
                result.error = f"翻译失败 ({error_type}): {error_msg}"

        return result

    def translate_batch(self, texts: List[str]) -> BatchTranslationResult:
        """
        批量翻译文本（单次 API 调用）

        Args:
            texts: 要翻译的文本列表

        Returns:
            BatchTranslationResult: 批量翻译结果
        """
        batch_result = BatchTranslationResult(total_count=len(texts))

        if not self.enabled:
            for text in texts:
                batch_result.results.append(TranslationResult(
                    original_text=text,
                    error="翻译功能未启用"
                ))
            batch_result.fail_count = len(texts)
            return batch_result

        if not self.api_key:
            for text in texts:
                batch_result.results.append(TranslationResult(
                    original_text=text,
                    error="未配置 AI API Key"
                ))
            batch_result.fail_count = len(texts)
            return batch_result

        if not texts:
            return batch_result

        # 过滤空文本
        non_empty_indices = []
        non_empty_texts = []
        for i, text in enumerate(texts):
            if text and text.strip():
                non_empty_indices.append(i)
                non_empty_texts.append(text)

        # 初始化结果列表
        for text in texts:
            batch_result.results.append(TranslationResult(original_text=text))

        # 空文本直接标记成功
        for i, text in enumerate(texts):
            if not text or not text.strip():
                batch_result.results[i].translated_text = text
                batch_result.results[i].success = True
                batch_result.success_count += 1

        if not non_empty_texts:
            return batch_result

        try:
            # 构建批量翻译内容（使用编号格式）
            batch_content = self._format_batch_content(non_empty_texts)

            # 构建提示词
            user_prompt = self.user_prompt_template
            user_prompt = user_prompt.replace("{target_language}", self.target_language)
            user_prompt = user_prompt.replace("{content}", batch_content)

            # 调用 AI API
            response = self._call_ai_api(user_prompt)

            # 解析批量翻译结果
            translated_texts = self._parse_batch_response(response, len(non_empty_texts))

            # 填充结果
            for idx, translated in zip(non_empty_indices, translated_texts):
                batch_result.results[idx].translated_text = translated
                batch_result.results[idx].success = True
                batch_result.success_count += 1

        except Exception as e:
            error_msg = f"批量翻译失败: {type(e).__name__}: {str(e)[:100]}"
            for idx in non_empty_indices:
                batch_result.results[idx].error = error_msg
            batch_result.fail_count = len(non_empty_indices)

        return batch_result

    def _format_batch_content(self, texts: List[str]) -> str:
        """格式化批量翻译内容"""
        lines = []
        for i, text in enumerate(texts, 1):
            lines.append(f"[{i}] {text}")
        return "\n".join(lines)

    def _parse_batch_response(self, response: str, expected_count: int) -> List[str]:
        """
        解析批量翻译响应

        Args:
            response: AI 响应文本
            expected_count: 期望的翻译数量

        Returns:
            List[str]: 翻译结果列表
        """
        results = []
        lines = response.strip().split("\n")

        current_idx = None
        current_text = []

        for line in lines:
            # 尝试匹配 [数字] 格式
            stripped = line.strip()
            if stripped.startswith("[") and "]" in stripped:
                bracket_end = stripped.index("]")
                try:
                    idx = int(stripped[1:bracket_end])
                    # 保存之前的内容
                    if current_idx is not None:
                        results.append((current_idx, "\n".join(current_text).strip()))
                    current_idx = idx
                    current_text = [stripped[bracket_end + 1:].strip()]
                except ValueError:
                    if current_idx is not None:
                        current_text.append(line)
            else:
                if current_idx is not None:
                    current_text.append(line)

        # 保存最后一条
        if current_idx is not None:
            results.append((current_idx, "\n".join(current_text).strip()))

        # 按索引排序并提取文本
        results.sort(key=lambda x: x[0])
        translated = [text for _, text in results]

        # 如果解析结果数量不匹配，尝试简单按行分割
        if len(translated) != expected_count:
            # 回退：按行分割（去除编号）
            translated = []
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("[") and "]" in stripped:
                    bracket_end = stripped.index("]")
                    translated.append(stripped[bracket_end + 1:].strip())
                elif stripped:
                    translated.append(stripped)

        # 确保返回正确数量
        while len(translated) < expected_count:
            translated.append("")

        return translated[:expected_count]

    def _call_ai_api(self, user_prompt: str) -> str:
        """调用 AI API"""
        if self.provider == "gemini":
            return self._call_gemini(user_prompt)
        return self._call_openai_compatible(user_prompt)

    def _get_api_url(self) -> str:
        """获取完整 API URL"""
        if self.base_url:
            return self.base_url

        urls = {
            "deepseek": "https://api.deepseek.com/v1/chat/completions",
            "openai": "https://api.openai.com/v1/chat/completions",
        }
        url = urls.get(self.provider)
        if not url:
            raise ValueError(f"{self.provider} 需要配置 base_url")
        return url

    def _call_openai_compatible(self, user_prompt: str) -> str:
        """调用 OpenAI 兼容接口"""
        import requests

        url = self._get_api_url()

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
        }

        if self.max_tokens:
            payload["max_tokens"] = self.max_tokens

        if self.extra_params:
            payload.update(self.extra_params)

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()

        data = response.json()
        return data["choices"][0]["message"]["content"]

    def _call_gemini(self, user_prompt: str) -> str:
        """调用 Google Gemini API"""
        import requests

        model = self.model or "gemini-1.5-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"

        headers = {
            "Content-Type": "application/json",
        }

        payload = {
            "contents": [{
                "role": "user",
                "parts": [{"text": user_prompt}]
            }],
            "generationConfig": {
                "temperature": self.temperature,
            },
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
        }

        if self.system_prompt:
            payload["system_instruction"] = {
                "parts": [{"text": self.system_prompt}]
            }

        if self.max_tokens:
            payload["generationConfig"]["maxOutputTokens"] = self.max_tokens

        if self.extra_params:
            payload["generationConfig"].update(self.extra_params)

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()

        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
