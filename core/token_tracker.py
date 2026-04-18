#!/usr/bin/env python3
"""
Token 追踪模块
负责记录、管理和统计 AI Token 使用量
"""

import json
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class TokenTracker:
    """管理和追踪 AI Token 使用情况"""

    def __init__(self, data_dir: Optional[str] = None):
        if data_dir:
            self.data_dir = Path(data_dir)
        else:
            # 默认数据目录
            app_data = os.environ.get('APPDATA', os.path.expanduser('~'))
            self.data_dir = Path(app_data) / 'WordCraft-Pro'
        
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 数据文件
        self.quota_file = self.data_dir / 'token_quota.json'
        self.logs_file = self.data_dir / 'token_logs.json'
        
        # 默认配额
        self.default_quota = 100000
        
        # 初始化
        self._init_quota()
        self._init_logs()

    def _init_quota(self):
        """初始化配额文件"""
        if not self.quota_file.exists():
            quota_data = {
                'quota': self.default_quota,
                'used': 0,
                'reset_date': self._get_next_reset_date(),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
            }
            self._save_quota(quota_data)

    def _init_logs(self):
        """初始化日志文件"""
        if not self.logs_file.exists():
            self._save_logs([])

    # ------------------------------------------------------------------
    #  配额管理
    # ------------------------------------------------------------------

    def set_quota(self, quota: int) -> bool:
        """设置 Token 配额"""
        try:
            quota_data = self._load_quota()
            quota_data['quota'] = quota
            quota_data['updated_at'] = datetime.now().isoformat()
            self._save_quota(quota_data)
            logger.info("Token 配额已设置为: %d", quota)
            return True
        except Exception as e:
            logger.error("设置配额失败: %s", e)
            return False

    def get_quota(self) -> dict:
        """获取配额信息"""
        try:
            quota_data = self._load_quota()
            remaining = quota_data['quota'] - quota_data['used']
            usage_percentage = (quota_data['used'] / quota_data['quota'] * 100) if quota_data['quota'] > 0 else 0
            
            return {
                'quota': quota_data['quota'],
                'used': quota_data['used'],
                'remaining': remaining,
                'usage_percentage': round(usage_percentage, 2),
                'reset_date': quota_data.get('reset_date'),
            }
        except Exception as e:
            logger.error("获取配额失败: %s", e)
            return {
                'quota': self.default_quota,
                'used': 0,
                'remaining': self.default_quota,
                'usage_percentage': 0,
                'reset_date': None,
            }

    def reset_quota(self) -> bool:
        """重置配额（清零已用量）"""
        try:
            quota_data = self._load_quota()
            quota_data['used'] = 0
            quota_data['reset_date'] = self._get_next_reset_date()
            quota_data['updated_at'] = datetime.now().isoformat()
            self._save_quota(quota_data)
            logger.info("Token 配额已重置")
            return True
        except Exception as e:
            logger.error("重置配额失败: %s", e)
            return False

    # ------------------------------------------------------------------
    #  用量记录
    # ------------------------------------------------------------------

    def record_usage(self, amount: int, purpose: str = 'unknown', model: str = '',
                     prompt_tokens: int = 0, completion_tokens: int = 0) -> bool:
        """记录 Token 使用"""
        try:
            # 检查配额是否足够
            quota_data = self._load_quota()
            if quota_data['used'] + amount > quota_data['quota']:
                logger.warning("Token 配额不足: 已用 %d + 本次 %d > 配额 %d",
                             quota_data['used'], amount, quota_data['quota'])
                return False
            
            # 更新已用量
            quota_data['used'] += amount
            quota_data['updated_at'] = datetime.now().isoformat()
            self._save_quota(quota_data)
            
            # 记录日志
            logs = self._load_logs()
            log_entry = {
                'id': self._generate_id(),
                'amount': amount,
                'purpose': purpose,
                'model': model,
                'prompt_tokens': prompt_tokens,
                'completion_tokens': completion_tokens,
                'created_at': datetime.now().isoformat(),
            }
            logs.append(log_entry)
            self._save_logs(logs)
            
            logger.info("Token 使用记录: %d tokens (%s)", amount, purpose)
            return True
        except Exception as e:
            logger.error("记录 Token 使用失败: %s", e)
            return False

    # ------------------------------------------------------------------
    #  使用统计
    # ------------------------------------------------------------------

    def get_usage_stats(self, days: int = 30) -> dict:
        """获取使用统计"""
        try:
            logs = self._load_logs()
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # 过滤指定日期范围内的日志
            recent_logs = []
            for log in logs:
                log_date = datetime.fromisoformat(log['created_at'])
                if log_date >= cutoff_date:
                    recent_logs.append(log)
            
            # 计算统计信息
            total_usage = sum(log['amount'] for log in recent_logs)
            total_requests = len(recent_logs)
            avg_usage = total_usage / total_requests if total_requests > 0 else 0
            
            # 按用途分组
            usage_by_purpose = {}
            for log in recent_logs:
                purpose = log.get('purpose', 'unknown')
                if purpose not in usage_by_purpose:
                    usage_by_purpose[purpose] = {'count': 0, 'total': 0}
                usage_by_purpose[purpose]['count'] += 1
                usage_by_purpose[purpose]['total'] += log['amount']
            
            # 按天分组
            usage_by_day = {}
            for log in recent_logs:
                day = log['created_at'][:10]
                if day not in usage_by_day:
                    usage_by_day[day] = {'count': 0, 'total': 0}
                usage_by_day[day]['count'] += 1
                usage_by_day[day]['total'] += log['amount']
            
            return {
                'total_usage': total_usage,
                'total_requests': total_requests,
                'avg_usage': round(avg_usage, 2),
                'usage_by_purpose': usage_by_purpose,
                'usage_by_day': usage_by_day,
                'period_days': days,
            }
        except Exception as e:
            logger.error("获取使用统计失败: %s", e)
            return {
                'total_usage': 0,
                'total_requests': 0,
                'avg_usage': 0,
                'usage_by_purpose': {},
                'usage_by_day': {},
                'period_days': days,
            }

    def get_usage_history(self, limit: int = 50) -> list:
        """获取使用历史记录"""
        try:
            logs = self._load_logs()
            # 返回最新的 limit 条记录
            return logs[-limit:]
        except Exception as e:
            logger.error("获取使用历史失败: %s", e)
            return []

    # ------------------------------------------------------------------
    #  预警机制
    # ------------------------------------------------------------------

    def check_warning(self, threshold: float = 0.8) -> dict:
        """检查是否达到预警阈值"""
        try:
            quota_data = self._load_quota()
            usage_percentage = quota_data['used'] / quota_data['quota'] if quota_data['quota'] > 0 else 0
            
            if usage_percentage >= threshold:
                return {
                    'warning': True,
                    'usage_percentage': round(usage_percentage * 100, 2),
                    'remaining': quota_data['quota'] - quota_data['used'],
                    'message': f'Token 使用量已达 {round(usage_percentage * 100, 1)}%，请及时充值',
                }
            else:
                return {
                    'warning': False,
                    'usage_percentage': round(usage_percentage * 100, 2),
                    'remaining': quota_data['quota'] - quota_data['used'],
                    'message': '',
                }
        except Exception as e:
            logger.error("检查预警失败: %s", e)
            return {
                'warning': False,
                'usage_percentage': 0,
                'remaining': 0,
                'message': '',
            }

    # ------------------------------------------------------------------
    #  数据清理
    # ------------------------------------------------------------------

    def clear_logs(self, keep_days: int = 30) -> bool:
        """清理旧的使用记录"""
        try:
            logs = self._load_logs()
            cutoff_date = datetime.now() - timedelta(days=keep_days)
            
            # 保留指定天数内的记录
            new_logs = []
            for log in logs:
                log_date = datetime.fromisoformat(log['created_at'])
                if log_date >= cutoff_date:
                    new_logs.append(log)
            
            self._save_logs(new_logs)
            logger.info("已清理 Token 使用记录，保留 %d 天内的 %d 条记录", keep_days, len(new_logs))
            return True
        except Exception as e:
            logger.error("清理使用记录失败: %s", e)
            return False

    def clear_all(self) -> bool:
        """清除所有 Token 数据"""
        try:
            self._save_quota({
                'quota': self.default_quota,
                'used': 0,
                'reset_date': self._get_next_reset_date(),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
            })
            self._save_logs([])
            logger.info("Token 数据已清除")
            return True
        except Exception as e:
            logger.error("清除 Token 数据失败: %s", e)
            return False

    # ------------------------------------------------------------------
    #  内部方法
    # ------------------------------------------------------------------

    def _load_quota(self) -> dict:
        """加载配额数据"""
        with open(self.quota_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _save_quota(self, data: dict):
        """保存配额数据"""
        with open(self.quota_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load_logs(self) -> list:
        """加载日志数据"""
        with open(self.logs_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _save_logs(self, logs: list):
        """保存日志数据"""
        with open(self.logs_file, 'w', encoding='utf-8') as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _generate_id() -> str:
        """生成唯一 ID"""
        import uuid
        return str(uuid.uuid4())[:8]

    @staticmethod
    def _get_next_reset_date() -> str:
        """获取下次重置日期（下个月1号）"""
        now = datetime.now()
        if now.month == 12:
            next_month = datetime(now.year + 1, 1, 1)
        else:
            next_month = datetime(now.year, now.month + 1, 1)
        return next_month.isoformat()
