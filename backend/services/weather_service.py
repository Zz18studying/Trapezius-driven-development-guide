# -*- coding: utf-8 -*-
"""
天气服务 - 调用和风天气API获取实时天气
"""

import os
import sys
import requests
import json
from typing import Optional, Dict

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, BACKEND_DIR)

import config


class WeatherService:
    def __init__(self):
        self.api_key = config.WEATHER_API_KEY
        self.api_url = config.WEATHER_API_URL
        self.city_url = config.WEATHER_CITY_URL
        self.default_city = config.DEFAULT_CITY
        # 简单缓存，避免频繁调用API
        self._cache = {}

    def _get_city_id(self, city: str) -> Optional[str]:
        """获取城市ID"""
        if not self.api_key:
            return None
        try:
            resp = requests.get(
                self.city_url,
                params={"location": city, "key": self.api_key},
                timeout=5
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == "200" and data.get("location"):
                    return data["location"][0]["id"]
        except Exception as e:
            print(f"[Weather] 获取城市ID失败: {e}")
        return None

    def get_weather(self, city: str = None, use_cache: bool = True) -> Dict:
        """
        获取实时天气
        
        返回:
            {
                "success": bool,
                "city": str,
                "weather": str,      # 天气状况（晴/多云/小雨等）
                "temp": str,         # 温度（℃）
                "humidity": str,     # 湿度（%）
                "wind": str,         # 风向风力
                "text": str,         # 完整天气描述
                "error": Optional[str]
            }
        """
        if not self.api_key:
            return {"success": False, "error": "未配置天气API Key"}

        city = city or self.default_city
        cache_key = f"{city}"

        # 检查缓存（5分钟内有效）
        if use_cache and cache_key in self._cache:
            cached = self._cache[cache_key]
            import time
            if time.time() - cached.get("_timestamp", 0) < 300:  # 5分钟
                return cached

        try:
            # 获取城市ID
            city_id = self._get_city_id(city)
            if not city_id:
                return {"success": False, "error": f"未找到城市: {city}"}

            # 获取实时天气
            resp = requests.get(
                self.api_url,
                params={"location": city_id, "key": self.api_key},
                timeout=10
            )

            if resp.status_code != 200:
                return {"success": False, "error": f"API请求失败: {resp.status_code}"}

            data = resp.json()
            if data.get("code") != "200":
                return {"success": False, "error": data.get("code", "未知错误")}

            now = data.get("now", {})
            result = {
                "success": True,
                "city": city,
                "weather": now.get("text", ""),
                "temp": now.get("temp", ""),
                "humidity": now.get("humidity", ""),
                "wind": now.get("windDir", "") + now.get("windSpeed", ""),
                "text": f"{now.get('text', '')}，气温{now.get('temp', '')}℃",
                "error": None
            }

            # 缓存结果
            if use_cache:
                result["_timestamp"] = __import__('time').time()
                self._cache[cache_key] = result

            return result

        except requests.exceptions.Timeout:
            return {"success": False, "error": "天气服务请求超时"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_weather_summary(self, city: str = None) -> str:
        """获取天气摘要（用于注入System Prompt）"""
        result = self.get_weather(city)
        if not result["success"]:
            return ""
        return f"当前{city}天气：{result['text']}，湿度{result['humidity']}%"


_weather_service = None

def get_weather_service():
    global _weather_service
    if _weather_service is None:
        _weather_service = WeatherService()
    return _weather_service