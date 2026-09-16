#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TRAE 每日自动签到脚本
自动从桌面版本地存储解密提取 token，完成每日签到领取积分

使用方法:
    python trae_checkin.py

工作原理:
    1. 从 TRAE 桌面版的 storage.json 读取加密的登录态
    2. 使用 AES-128-CBC 解密提取 accessToken
    3. 调用签到 API 完成每日签到
"""

import json
import os
import sys
import base64
import hashlib
import requests
from datetime import datetime
from pathlib import Path
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

# 配置文件路径
SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "checkin_config.json"
LOG_FILE = SCRIPT_DIR / "checkin.log"

# API 接口
STATUS_URL = "https://api.trae.cn/trae/api/v2/ug/checkin_credits/status"
CLAIM_URL = "https://api.trae.cn/trae/api/v2/ug/checkin_credits/claim"

# 解密相关常量
EM = 6  # header 长度
RV = 32  # key 长度
WP = 16  # IV 长度
RH = 64  # HMAC 长度
VP = 64  # XOR 数组长度

# 固定密钥数组（从 TRAE 代码中提取）
URE = bytes([
    82, 9, 106, 213, 48, 54, 165, 56, 191, 64, 163, 158, 129, 243, 215, 251,
    124, 227, 57, 130, 155, 47, 255, 135, 52, 142, 67, 68, 196, 222, 233, 203,
    84, 123, 148, 50, 166, 194, 35, 61, 238, 76, 149, 11, 66, 250, 195, 78,
    8, 46, 161, 102, 40, 217, 36, 178, 118, 91, 162, 73, 109, 139, 209, 37
])

DRE = bytes([
    31, 221, 168, 51, 136, 7, 199, 49, 177, 18, 16, 89, 39, 128, 236, 95,
    96, 81, 127, 169, 25, 181, 74, 13, 45, 229, 122, 159, 147, 201, 156, 239,
    160, 224, 59, 77, 174, 42, 245, 176, 200, 235, 187, 60, 131, 83, 153, 97,
    23, 43, 4, 126, 186, 119, 214, 38, 225, 105, 20, 99, 85, 33, 12, 125
])


def log(message):
    """记录日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] {message}"
    print(log_msg)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_msg + "\n")
    except Exception:
        pass


def decrypt_auth_data(b64_data):
    """
    解密 TRAE 存储的认证数据
    
    Args:
        b64_data: base64 编码的加密数据
        
    Returns:
        解密后的 JSON 字符串
    """
    # base64 解码
    data = base64.b64decode(b64_data)
    
    # 提取 key（从第 EM 字节开始，共 RV 字节）
    key = data[EM:EM + RV]
    
    # SHA-512 哈希 key
    sha = hashlib.sha512(key).digest()
    
    # URE XOR DRE
    xor_result = bytes(a ^ b for a, b in zip(URE, DRE))
    
    # 拼接 sha + xor
    comb = sha + xor_result
    
    # 再次 SHA-512 得到 AES key 和 IV
    final_hash = hashlib.sha512(comb).digest()
    
    aes_key = final_hash[:16]  # AES-128 key
    iv = final_hash[16:32]     # IV
    
    # 提取密文（跳过 header + key）
    ciphertext = data[EM + RV:]
    
    # AES-128-CBC 解密
    cipher = AES.new(aes_key, AES.MODE_CBC, iv)
    decrypted = cipher.decrypt(ciphertext)
    
    # 去掉 PKCS7 padding
    plaintext = unpad(decrypted, AES.block_size)
    
    # 前 64 字节是 HMAC，跳过
    return plaintext[RH:].decode("utf-8")


def get_token_from_desktop():
    """
    从 TRAE 桌面版本地存储中自动提取 token
    
    Returns:
        (token, user_region) 元组，失败返回 (None, None)
    """
    # 尝试多个可能的存储路径
    possible_paths = [
        Path(os.environ.get("APPDATA", "")) / "TRAE SOLO CN" / "User" / "globalStorage" / "storage.json",
        Path(os.environ.get("APPDATA", "")) / "TRAE CN" / "User" / "globalStorage" / "storage.json",
        Path(os.environ.get("APPDATA", "")) / "TRAE" / "User" / "globalStorage" / "storage.json",
    ]
    
    storage_path = None
    for path in possible_paths:
        if path.exists():
            storage_path = path
            break
    
    if not storage_path:
        log("未找到 TRAE 桌面版存储文件")
        return None, None
    
    log(f"找到存储文件: {storage_path}")
    
    try:
        with open(storage_path, "r", encoding="utf-8") as f:
            storage = json.load(f)
    except Exception as e:
        log(f"读取存储文件失败: {e}")
        return None, None
    
    # 查找认证数据
    auth_key = "iCubeAuthInfo://icube.cloudide"
    if auth_key not in storage:
        log("存储文件中未找到认证数据")
        return None, None
    
    encrypted = storage[auth_key]
    
    try:
        decrypted = decrypt_auth_data(encrypted)
        auth_data = json.loads(decrypted)
    except Exception as e:
        log(f"解密认证数据失败: {e}")
        return None, None
    
    token = auth_data.get("token")
    user_region = auth_data.get("userRegion", {}).get("region")
    
    if not token:
        log("解密后未找到 token")
        return None, None
    
    log(f"成功从桌面版提取 token (长度: {len(token)})")
    return token, user_region


def load_config():
    """加载配置文件"""
    if not CONFIG_FILE.exists():
        return {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(config):
    """保存配置文件"""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def checkin_status(token, user_region=None):
    """检查签到状态"""
    headers = {
        "Authorization": f"Cloud-IDE-JWT {token}",
        "Content-Type": "application/json",
    }
    if user_region:
        headers["X-User-Region"] = user_region
    
    try:
        response = requests.post(STATUS_URL, headers=headers, json={}, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        log(f"检查签到状态失败: {e}")
        return None


def claim_credits(token, user_region=None):
    """领取签到积分"""
    headers = {
        "Authorization": f"Cloud-IDE-JWT {token}",
        "Content-Type": "application/json",
    }
    if user_region:
        headers["X-User-Region"] = user_region
    
    try:
        response = requests.post(CLAIM_URL, headers=headers, json={}, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        log(f"领取积分失败: {e}")
        return None


def main():
    """主函数"""
    log("=" * 50)
    log("开始执行 TRAE 每日签到任务")
    
    token = None
    user_region = None
    
    # 1. 优先从桌面版自动提取
    log("正在从桌面版提取 token...")
    token, user_region = get_token_from_desktop()
    
    # 2. 如果桌面版提取失败，尝试从配置文件读取
    if not token:
        log("桌面版提取失败，尝试从配置文件读取...")
        config = load_config()
        token = config.get("access_token")
        user_region = config.get("user_region")
        if token:
            log(f"从配置文件读取到 token (长度: {len(token)})")
    
    if not token:
        log("错误：无法获取 token")
        log("请确保 TRAE 桌面版已安装并登录")
        log("或者手动配置 token 到 checkin_config.json")
        return 1
    
    # 检查签到状态
    log("正在检查签到状态...")
    status = checkin_status(token, user_region)
    
    if not status:
        log("无法获取签到状态")
        return 1
    
    log(f"签到状态响应: {json.dumps(status, ensure_ascii=False)}")
    
    # 检查 token 是否有效
    if status.get("code") == 1001:
        log("错误：token 无效或已过期")
        log("请在 TRAE 桌面版中重新登录")
        return 1
    
    # 检查是否已签到
    is_claimed = status.get("checked_in", False)
    
    if is_claimed:
        credits = status.get("credits", 200)
        log(f"今日已签到，获得 {credits} 积分")
        log("签到任务结束")
        log("=" * 50)
        return 0
    
    # 未签到，尝试领取
    if not status.get("enable", True):
        log("签到功能未启用")
        return 1
    
    log("今日未签到，正在领取积分...")
    result = claim_credits(token, user_region)
    
    if not result:
        log("签到失败")
        return 1
    
    log(f"签到响应: {json.dumps(result, ensure_ascii=False)}")
    
    # 检查签到结果
    if result.get("code") == 0:
        credits = result.get("data", {}).get("credits", 200)
        log(f"签到成功！获得 {credits} 积分")
        return 0
    else:
        message = result.get("message", "未知错误")
        log(f"签到失败: {message}")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        log("签到任务结束")
        log("=" * 50)
        sys.exit(exit_code)
    except Exception as e:
        log(f"发生未捕获的异常: {e}")
        log("=" * 50)
        sys.exit(1)
