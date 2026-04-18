#!/usr/bin/env python3
"""
用户数据管理模块
负责本地用户数据的存储、缓存和同步
"""

import json
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class UserDataManager:
    """管理用户本地数据的存储和读取"""

    def __init__(self, data_dir: Optional[str] = None):
        if data_dir:
            self.data_dir = Path(data_dir)
        else:
            # 默认数据目录
            app_data = os.environ.get('APPDATA', os.path.expanduser('~'))
            self.data_dir = Path(app_data) / 'WordCraft-Pro'
        
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 子目录
        self.templates_dir = self.data_dir / 'templates'
        self.documents_dir = self.data_dir / 'documents'
        self.cache_dir = self.data_dir / 'cache'
        
        for d in [self.templates_dir, self.documents_dir, self.cache_dir]:
            d.mkdir(exist_ok=True)
        
        # 数据文件
        self.user_file = self.data_dir / 'user.json'
        self.settings_file = self.data_dir / 'settings.json'
        self.recent_files = self.data_dir / 'recent_files.json'
        self.session_file = self.cache_dir / 'session.json'

    # ------------------------------------------------------------------
    #  用户信息管理
    # ------------------------------------------------------------------

    def save_user_info(self, user_data: dict) -> bool:
        """保存用户信息到本地"""
        try:
            user_data['updated_at'] = datetime.now().isoformat()
            with open(self.user_file, 'w', encoding='utf-8') as f:
                json.dump(user_data, f, ensure_ascii=False, indent=2)
            logger.info("用户信息已保存: %s", user_data.get('email', 'unknown'))
            return True
        except Exception as e:
            logger.error("保存用户信息失败: %s", e)
            return False

    def load_user_info(self) -> Optional[dict]:
        """从本地加载用户信息"""
        try:
            if self.user_file.exists():
                with open(self.user_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return None
        except Exception as e:
            logger.error("加载用户信息失败: %s", e)
            return None

    def clear_user_info(self) -> bool:
        """清除用户信息（登出时调用）"""
        try:
            if self.user_file.exists():
                self.user_file.unlink()
            logger.info("用户信息已清除")
            return True
        except Exception as e:
            logger.error("清除用户信息失败: %s", e)
            return False

    # ------------------------------------------------------------------
    #  用户设置管理
    # ------------------------------------------------------------------

    def save_settings(self, settings: dict) -> bool:
        """保存用户设置"""
        try:
            settings['updated_at'] = datetime.now().isoformat()
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error("保存设置失败: %s", e)
            return False

    def load_settings(self) -> dict:
        """加载用户设置"""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return self._default_settings()
        except Exception as e:
            logger.error("加载设置失败: %s", e)
            return self._default_settings()

    def update_setting(self, key: str, value) -> bool:
        """更新单个设置项"""
        settings = self.load_settings()
        settings[key] = value
        return self.save_settings(settings)

    def get_setting(self, key: str, default=None):
        """获取单个设置项"""
        settings = self.load_settings()
        return settings.get(key, default)

    @staticmethod
    def _default_settings() -> dict:
        """返回默认设置"""
        return {
            'theme': 'light',
            'language': 'zh-CN',
            'default_paper_size': 'A4',
            'default_font': '宋体',
            'default_font_size': 12,
            'auto_save_interval': 30,
            'notify_token_warning': True,
            'notify_auto_save': True,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
        }

    # ------------------------------------------------------------------
    #  最近文件列表管理
    # ------------------------------------------------------------------

    def add_recent_file(self, file_path: str, file_name: str) -> bool:
        """添加到最近文件列表"""
        try:
            recent = self.load_recent_files()
            
            # 移除已存在的相同路径
            recent = [f for f in recent if f.get('path') != file_path]
            
            # 添加到开头
            recent.insert(0, {
                'path': file_path,
                'name': file_name,
                'opened_at': datetime.now().isoformat(),
            })
            
            # 只保留最近 10 个
            recent = recent[:10]
            
            with open(self.recent_files, 'w', encoding='utf-8') as f:
                json.dump(recent, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            logger.error("添加最近文件失败: %s", e)
            return False

    def load_recent_files(self) -> list:
        """加载最近文件列表"""
        try:
            if self.recent_files.exists():
                with open(self.recent_files, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception as e:
            logger.error("加载最近文件失败: %s", e)
            return []

    def clear_recent_files(self) -> bool:
        """清除最近文件列表"""
        try:
            if self.recent_files.exists():
                self.recent_files.unlink()
            return True
        except Exception as e:
            logger.error("清除最近文件失败: %s", e)
            return False

    # ------------------------------------------------------------------
    #  模板本地缓存管理
    # ------------------------------------------------------------------

    def cache_template(self, template_id: str, template_data: dict) -> bool:
        """缓存模板数据"""
        try:
            template_file = self.templates_dir / f'{template_id}.json'
            template_data['cached_at'] = datetime.now().isoformat()
            with open(template_file, 'w', encoding='utf-8') as f:
                json.dump(template_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error("缓存模板失败: %s", e)
            return False

    def load_cached_template(self, template_id: str) -> Optional[dict]:
        """加载缓存的模板"""
        try:
            template_file = self.templates_dir / f'{template_id}.json'
            if template_file.exists():
                with open(template_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return None
        except Exception as e:
            logger.error("加载缓存模板失败: %s", e)
            return None

    def delete_cached_template(self, template_id: str) -> bool:
        """删除缓存的模板"""
        try:
            template_file = self.templates_dir / f'{template_id}.json'
            if template_file.exists():
                template_file.unlink()
            return True
        except Exception as e:
            logger.error("删除缓存模板失败: %s", e)
            return False

    def list_cached_templates(self) -> list:
        """列出所有缓存的模板"""
        try:
            templates = []
            for f in self.templates_dir.glob('*.json'):
                with open(f, 'r', encoding='utf-8') as fh:
                    templates.append(json.load(fh))
            return templates
        except Exception as e:
            logger.error("列出缓存模板失败: %s", e)
            return []

    # ------------------------------------------------------------------
    #  文档本地缓存管理
    # ------------------------------------------------------------------

    def save_document_cache(self, doc_id: str, content: str, title: str = "未命名文档") -> bool:
        """缓存文档内容"""
        try:
            doc_file = self.documents_dir / f'{doc_id}.json'
            doc_data = {
                'id': doc_id,
                'title': title,
                'content': content,
                'saved_at': datetime.now().isoformat(),
            }
            with open(doc_file, 'w', encoding='utf-8') as f:
                json.dump(doc_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error("缓存文档失败: %s", e)
            return False

    def load_document_cache(self, doc_id: str) -> Optional[dict]:
        """加载缓存的文档"""
        try:
            doc_file = self.documents_dir / f'{doc_id}.json'
            if doc_file.exists():
                with open(doc_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return None
        except Exception as e:
            logger.error("加载缓存文档失败: %s", e)
            return None

    def delete_document_cache(self, doc_id: str) -> bool:
        """删除缓存的文档"""
        try:
            doc_file = self.documents_dir / f'{doc_id}.json'
            if doc_file.exists():
                doc_file.unlink()
            return True
        except Exception as e:
            logger.error("删除缓存文档失败: %s", e)
            return False

    # ------------------------------------------------------------------
    #  会话管理
    # ------------------------------------------------------------------

    def save_session(self, session_data: dict) -> bool:
        """保存当前会话信息"""
        try:
            session_data['saved_at'] = datetime.now().isoformat()
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error("保存会话失败: %s", e)
            return False

    def load_session(self) -> Optional[dict]:
        """加载当前会话"""
        try:
            if self.session_file.exists():
                with open(self.session_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return None
        except Exception as e:
            logger.error("加载会话失败: %s", e)
            return None

    def clear_session(self) -> bool:
        """清除当前会话"""
        try:
            if self.session_file.exists():
                self.session_file.unlink()
            return True
        except Exception as e:
            logger.error("清除会话失败: %s", e)
            return False

    # ------------------------------------------------------------------
    #  数据清理
    # ------------------------------------------------------------------

    def clear_all_cache(self) -> bool:
        """清除所有缓存数据"""
        try:
            for d in [self.templates_dir, self.documents_dir, self.cache_dir]:
                for f in d.glob('*.json'):
                    f.unlink()
            logger.info("所有缓存已清除")
            return True
        except Exception as e:
            logger.error("清除缓存失败: %s", e)
            return False

    def get_data_size(self) -> dict:
        """获取数据目录大小信息"""
        def dir_size(directory: Path) -> int:
            total = 0
            if directory.exists():
                for f in directory.rglob('*'):
                    if f.is_file():
                        total += f.stat().st_size
            return total

        return {
            'total_size': dir_size(self.data_dir),
            'templates_size': dir_size(self.templates_dir),
            'documents_size': dir_size(self.documents_dir),
            'cache_size': dir_size(self.cache_dir),
        }
