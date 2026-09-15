#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TRAE 每日自动签到脚本
自动调用 TRAE API 完成每日签到，领取积分
"""

import json
import os
import sys
import requests
from datetime import datetime
from pathlib import Path

# 配置文件路径
SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "checkin_config.json"
LOG_FILE = SCRIPT_DIR / "checkin.log"

# API 接口
STATUS_URL = "https://api.trae.cn/trae/api/v2/ug/checkin_credits/status"
CLAIM_URL = "https://api.trae.cn/trae/api/v2/ug/checkin_credits/claim"


def load_config():
    """加载配置文件"""
    if not CONFIG_FILE.exists():
        return None
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"读取配置文件失败: {e}")
        return None


def save_config(config):
    """保存配置文件"""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


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


def checkin_status(access_token):
    """检查签到状态"""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "User-Agent": "TraeWork/2.0 (Windows)"
    }
    
    try:
        response = requests.post(STATUS_URL, headers=headers, json={}, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data
    except Exception as e:
        log(f"检查签到状态失败: {e}")
        return None


def claim_credits(access_token):
    """领取签到积分"""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "User-Agent": "TraeWork/2.0 (Windows)"
    }
    
    try:
        response = requests.post(CLAIM_URL, headers=headers, json={}, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data
    except Exception as e:
        log(f"领取积分失败: {e}")
        return None


def try_get_token_from_storage():
    """尝试从本地存储中获取token（需要解密，预留接口）"""
    # 这里预留自动解密功能
    # 目前需要用户手动配置token
    return None


def main():
    """主函数"""
    log("=" * 50)
    log("开始执行 TRAE 每日签到任务")
    
    # 加载配置
    config = load_config()
    
    if not config or not config.get("access_token"):
        # 尝试自动获取token
        token = try_get_token_from_storage()
        if token:
            config = {"access_token": token}
            save_config(config)
            log("已从本地存储自动获取 token")
        else:
            log("错误：未找到 access_token，请先配置")
            log("请按以下步骤获取 token：")
            log("1. 打开浏览器，登录 https://www.trae.cn/work")
            log("2. 按 F12 打开开发者工具")
            log("3. 切换到 Network (网络) 标签")
            log("4. 在页面上点击签到按钮")
            log("5. 找到 checkin 相关的请求")
            log("6. 在请求头中找到 Authorization，复制 Bearer 后面的 token")
            log(f"7. 将 token 填入配置文件: {CONFIG_FILE}")
            return 1
    
    access_token = config["access_token"]
    
    # 验证token格式
    if not access_token or len(access_token) < 20 or "在这里" in access_token or "填入" in access_token:
        log("错误：access_token 未正确配置，请检查配置文件")
        log(f"配置文件路径: {CONFIG_FILE}")
        log("请按照使用说明获取并填入正确的 access_token")
        return 1
    
    # 检查签到状态
    log("正在检查签到状态...")
    status = checkin_status(access_token)
    
    if not status:
        log("无法获取签到状态，请检查 token 是否有效")
        return 1
    
    log(f"签到状态响应: {json.dumps(status, ensure_ascii=False)}")
    
    # 检查token是否有效
    if status.get("code") == 1001 or not status.get("enable", True):
        log("错误：token 无效或已过期，请重新获取 token")
        return 1
    
    # 检查是否已签到
    is_claimed = status.get("checked_in", False) or status.get("claimed", False)
    
    # 检查不同的返回格式
    data = status.get("data", status)
    if isinstance(data, dict):
        is_claimed = is_claimed or data.get("checked_in", False) or data.get("claimed", False)
        if "checkin_status" in data:
            is_claimed = is_claimed or data["checkin_status"].get("claimed", False)
    
    if is_claimed:
        credits = status.get("credits", 0) or data.get("credits", 0) or data.get("work_credits", 200)
        if credits == 0:
            credits = 200  # 默认值
        log(f"今日已签到，获得 {credits} 积分")
        return 0
    
    # 未签到，尝试领取
    log("今日未签到，正在领取积分...")
    result = claim_credits(access_token)
    
    if not result:
        log("签到失败，请检查 token 是否有效")
        return 1
    
    log(f"签到响应: {json.dumps(result, ensure_ascii=False)}")
    
    # 检查签到结果
    success = result.get("success", False) or result.get("code") == 0
    result_data = result.get("data", result)
    if isinstance(result_data, dict):
        success = success or result_data.get("success", False)
    
    if success:
        credits = result.get("credits", 0) or result_data.get("credits", 0) or result_data.get("work_credits", 200)
        if credits == 0:
            credits = 200
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
