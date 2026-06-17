# -*- coding: utf-8 -*-
"""
语音服务路由 - 百度智能云 TTS + ASR
"""

import os
import time
import random
import base64
import tempfile
import subprocess
import requests
from fastapi import APIRouter, File, UploadFile
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/voice", tags=["语音服务"])

# 百度云配置
BAIDU_API_KEY = os.environ.get("BAIDU_API_KEY", "")
BAIDU_SECRET_KEY = os.environ.get("BAIDU_SECRET_KEY", "")

# Token 缓存
_access_token = None
_token_expire_time = 0


def get_access_token():
    """获取百度 access_token（带缓存）"""
    global _access_token, _token_expire_time

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
            _token_expire_time = time.time() + result.get("expires_in", 2592000)
            print(f"[Token] 获取成功")
            return _access_token
        else:
            print(f"[Token] 获取失败: {result}")
            return None
    except Exception as e:
        print(f"[Token] 异常: {e}")
        return None


# ==================== TTS 语音合成 ====================
class TTSRequest(BaseModel):
    text: str
    voice_type: Optional[int] = 0  # 0:女声, 1:男声


@router.post("/tts")
async def text_to_speech(request: TTSRequest):
    """语音合成 - 百度 TTS"""
    if not BAIDU_API_KEY or not BAIDU_SECRET_KEY:
        return {"success": False, "error": "未配置百度云密钥"}

    token = get_access_token()
    if not token:
        return {"success": False, "error": "获取 access_token 失败"}

    try:
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

        if response.headers.get("Content-Type") == "audio/mp3":
            session_id = f"{int(time.time())}-{random.randint(100000, 999999)}"
            audio_filename = f"tts_{session_id}.mp3"
            audio_dir = "/var/www/Trapezius-driven-development-guide/backend/audio"
            os.makedirs(audio_dir, exist_ok=True)
            audio_path = os.path.join(audio_dir, audio_filename)

            with open(audio_path, "wb") as f:
                f.write(response.content)

            # 返回相对路径（解决 HTTPS 混合内容问题）
            audio_url = f"/audio/{audio_filename}"
            print(f"[TTS] 合成成功: {audio_url}")
            return {"success": True, "audio_url": audio_url}
        else:
            print(f"[TTS] 合成失败: {response.text}")
            return {"success": False, "error": "合成失败"}
    except Exception as e:
        print(f"[TTS] 异常: {e}")
        return {"success": False, "error": str(e)}


# ==================== ASR 语音识别 ====================
@router.post("/asr")
async def speech_recognition(audio: UploadFile = File(...)):
    """
    语音识别 - 百度 ASR
    自动将 WebM/MP3 转换为 PCM 格式
    """
    if not BAIDU_API_KEY or not BAIDU_SECRET_KEY:
        return {"success": False, "error": "未配置百度云密钥"}

    token = get_access_token()
    if not token:
        return {"success": False, "error": "获取 access_token 失败"}

    tmp_in_path = None
    tmp_pcm_path = None

    try:
        # 1. 读取音频数据
        audio_data = await audio.read()
        print(f"[ASR] 原始音频大小: {len(audio_data)} bytes")

        # 2. 保存为临时文件（浏览器录音通常是 webm 或 mp3）
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp_in:
            tmp_in.write(audio_data)
            tmp_in_path = tmp_in.name
        print(f"[ASR] 临时文件: {tmp_in_path}")

        # 3. 使用 ffmpeg 转换为 PCM（16kHz, 单声道, 16bit）
        tmp_pcm_path = tempfile.NamedTemporaryFile(suffix=".pcm", delete=False).name
        cmd = f"ffmpeg -i {tmp_in_path} -ar 16000 -ac 1 -f s16le {tmp_pcm_path} -y"
        result = subprocess.run(cmd, shell=True, capture_output=True)

        if result.returncode != 0:
            print(f"[ASR] ffmpeg 转换失败: {result.stderr.decode()}")
            return {"success": False, "error": "音频格式转换失败"}

        # 4. 读取 PCM 数据
        with open(tmp_pcm_path, "rb") as f:
            pcm_data = f.read()
        print(f"[ASR] 转换后 PCM 大小: {len(pcm_data)} bytes")

        # 5. 调用百度 ASR API
        audio_base64 = base64.b64encode(pcm_data).decode()

        url = "https://vop.baidu.com/server_api"
        payload = {
            "format": "pcm",
            "rate": 16000,
            "channel": 1,
            "cuid": "lingshan_guide",
            "token": token,
            "speech": audio_base64,
            "len": len(pcm_data)
        }

        response = requests.post(url, json=payload, timeout=10)
        result = response.json()

        print(f"[ASR] 百度返回: {result}")

        if result.get("err_no") == 0:
            text = result.get("result", [""])[0]
            if text:
                return {"success": True, "text": text}
            else:
                return {"success": False, "error": "未识别到语音"}
        else:
            error_msg = result.get("err_msg", "识别失败")
            return {"success": False, "error": error_msg}

    except Exception as e:
        print(f"[ASR] 异常: {e}")
        return {"success": False, "error": str(e)}

    finally:
        # 清理临时文件
        if tmp_in_path and os.path.exists(tmp_in_path):
            try:
                os.unlink(tmp_in_path)
            except:
                pass
        if tmp_pcm_path and os.path.exists(tmp_pcm_path):
            try:
                os.unlink(tmp_pcm_path)
            except:
                pass