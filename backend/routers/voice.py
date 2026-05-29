# -*- coding: utf-8 -*-
"""
语音服务路由 - 百度智能云 TTS
"""

import os
import json
import time
import random
import requests
from fastapi import APIRouter, File, UploadFile
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/voice", tags=["语音服务"])

# 百度云配置
BAIDU_API_KEY = os.environ.get("BAIDU_API_KEY", "")
BAIDU_SECRET_KEY = os.environ.get("BAIDU_SECRET_KEY", "")

# 全局 token 缓存
_access_token = None
_token_expire_time = 0


def get_access_token():
    """获取百度 access_token（带缓存）"""
    global _access_token, _token_expire_time
    
    # 检查缓存的 token 是否还有效（提前5分钟刷新）
    if _access_token and time.time() < _token_expire_time - 300:
        return _access_token
    
    url = "https://aip.baidubce.com/oauth/2.0/token"
    params = {
        "grant_type": "client_credentials",
        "client_id": BAIDU_API_KEY,
        "client_secret": BAIDU_SECRET_KEY,
    }
    
    try:
        resp = requests.post(url, params=params, timeout=10)
        result = resp.json()
        
        if "access_token" in result:
            _access_token = result["access_token"]
            expires_in = result.get("expires_in", 2592000)  # 默认30天
            _token_expire_time = time.time() + expires_in
            return _access_token
        else:
            print(f"获取 access_token 失败: {result}")
            return None
    except Exception as e:
        print(f"获取 access_token 异常: {e}")
        return None


class TTSRequest(BaseModel):
    text: str
    voice_type: Optional[int] = 0  # 0:女声, 1:男声


@router.post("/tts")
async def text_to_speech(request: TTSRequest):
    """
    百度智能云语音合成接口
    """
    if not BAIDU_API_KEY or not BAIDU_SECRET_KEY:
        return {"success": False, "error": "未配置百度云密钥"}
    
    # 获取 access_token
    token = get_access_token()
    if not token:
        return {"success": False, "error": "获取 access_token 失败，请检查密钥配置"}
    
    try:
        # 调用百度 TTS API
        url = "https://tsn.baidu.com/text2audio"
        data = {
            "tex": request.text,
            "tok": token,
            "cuid": "lingshan_guide",
            "ctp": 1,
            "lan": "zh",
            "aue": 3,              # mp3 格式
            "per": request.voice_type,
            "spd": 5,
            "pit": 5,
            "vol": 9,
        }
        
        response = requests.post(url, data=data, timeout=10)
        
        # 检查是否返回音频（成功时 Content-Type 是 audio/mp3）
        if response.headers.get("Content-Type") == "audio/mp3":
            # 保存音频文件
            session_id = f"{int(time.time())}-{random.randint(100000, 999999)}"
            audio_filename = f"tts_{session_id}.mp3"
            audio_dir = "/var/www/Trapezius-driven-development-guide/backend/audio"
            os.makedirs(audio_dir, exist_ok=True)
            audio_path = os.path.join(audio_dir, audio_filename)
            
            with open(audio_path, "wb") as f:
                f.write(response.content)
            
            audio_url = f"http://110.42.246.141:8000/audio/{audio_filename}"
            return {"success": True, "audio_url": audio_url}
        else:
            # 失败返回错误信息
            error_data = response.json()
            error_msg = error_data.get("err_msg", "合成失败")
            return {"success": False, "error": error_msg}
            
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/asr")
async def speech_recognition(audio: UploadFile = File(...)):
    """
    语音识别接口（待实现）
    """
    return {"success": False, "error": "语音识别功能开发中"}
