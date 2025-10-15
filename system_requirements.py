import sys
import platform
import psutil
import logging
from typing import Dict, List, Tuple
from datetime import datetime

class SystemRequirements:
    """システム要件チェッククラス"""
    
    def __init__(self):
        # 必要システム要件
        self.min_python_version = (3, 8)
        self.supported_os = ["Windows"]
        self.min_windows_version = "10"
        self.min_memory_gb = 4
        self.recommended_memory_gb = 8
        self.warning_memory_usage_percent = 80
        
        # システム情報
        self.system_info = {}
        self.requirements_met = {}
        
        self.check_system_requirements()
    
    def check_system_requirements(self):
        """システム要件をチェック"""
        try:
            # システム情報を取得
            self.system_info = self.get_system_info()
            
            # 要件チェック
            self.requirements_met = {
                'python_version': self.check_python_version(),
                'operating_system': self.check_operating_system(),
                'memory': self.check_memory(),
                'disk_space': self.check_disk_space()
            }
            
            logging.info("システム要件チェック完了")
            
        except Exception as e:
            logging.error(f"システム要件チェックエラー: {e}")
    
    def get_system_info(self) -> Dict:
        """システム情報を取得"""
        try:
            # Python情報
            python_version = sys.version_info
            python_version_str = f"{python_version.major}.{python_version.minor}.{python_version.micro}"
            
            # OS情報
            os_name = platform.system()
            os_version = platform.version()
            os_release = platform.release()
            architecture = platform.architecture()[0]
            
            # メモリ情報
            memory = psutil.virtual_memory()
            total_memory_gb = memory.total / (1024**3)
            available_memory_gb = memory.available / (1024**3)
            memory_usage_percent = memory.percent
            
            # ディスク情報
            disk_usage = psutil.disk_usage('.')
            total_disk_gb = disk_usage.total / (1024**3)
            free_disk_gb = disk_usage.free / (1024**3)
            disk_usage_percent = (disk_usage.used / disk_usage.total) * 100
            
            # CPU情報
            cpu_count = psutil.cpu_count()
            cpu_percent = psutil.cpu_percent(interval=1)
            
            return {
                'python_version': python_version,
                'python_version_str': python_version_str,
                'os_name': os_name,
                'os_version': os_version,
                'os_release': os_release,
                'architecture': architecture,
                'total_memory_gb': total_memory_gb,
                'available_memory_gb': available_memory_gb,
                'memory_usage_percent': memory_usage_percent,
                'total_disk_gb': total_disk_gb,
                'free_disk_gb': free_disk_gb,
                'disk_usage_percent': disk_usage_percent,
                'cpu_count': cpu_count,
                'cpu_percent': cpu_percent
            }
            
        except Exception as e:
            logging.error(f"システム情報取得エラー: {e}")
            return {}
    
    def check_python_version(self) -> Dict:
        """Pythonバージョンをチェック"""
        try:
            current_version = self.system_info['python_version']
            min_version = self.min_python_version
            
            is_compatible = current_version >= min_version
            
            return {
                'passed': is_compatible,
                'current': f"{current_version.major}.{current_version.minor}.{current_version.micro}",
                'required': f"{min_version[0]}.{min_version[1]}以上",
                'message': "OK" if is_compatible else f"Python {min_version[0]}.{min_version[1]}以上が必要です"
            }
            
        except Exception as e:
            logging.error(f"Pythonバージョンチェックエラー: {e}")
            return {
                'passed': False,
                'current': "不明",
                'required': f"{self.min_python_version[0]}.{self.min_python_version[1]}以上",
                'message': "Pythonバージョンの確認に失敗しました"
            }
    
    def check_operating_system(self) -> Dict:
        """オペレーティングシステムをチェック"""
        try:
            os_name = self.system_info['os_name']
            os_version = self.system_info['os_version']
            os_release = self.system_info['os_release']
            
            is_supported = os_name in self.supported_os
            
            # Windows固有のバージョンチェック
            if os_name == "Windows":
                try:
                    # Windows 10以上かチェック
                    release_number = int(os_release)
                    is_version_ok = release_number >= 10
                    is_supported = is_supported and is_version_ok
                except:
                    is_version_ok = True  # バージョン判定失敗時は通す
            
            return {
                'passed': is_supported,
                'current': f"{os_name} {os_release}",
                'required': f"{', '.join(self.supported_os)} {self.min_windows_version}以上",
                'message': "OK" if is_supported else f"サポートされていないOSです"
            }
            
        except Exception as e:
            logging.error(f"OSチェックエラー: {e}")
            return {
                'passed': False,
                'current': "不明",
                'required': f"{', '.join(self.supported_os)} {self.min_windows_version}以上",
                'message': "OSの確認に失敗しました"
            }
    
    def check_memory(self) -> Dict:
        """メモリをチェック"""
        try:
            total_memory_gb = self.system_info['total_memory_gb']
            available_memory_gb = self.system_info['available_memory_gb']
            memory_usage_percent = self.system_info['memory_usage_percent']
            
            # メモリ容量チェック
            is_memory_sufficient = total_memory_gb >= self.min_memory_gb
            is_memory_recommended = total_memory_gb >= self.recommended_memory_gb
            
            # メモリ使用量警告
            is_memory_usage_ok = memory_usage_percent < self.warning_memory_usage_percent
            
            # 総合判定
            passed = is_memory_sufficient and is_memory_usage_ok
            
            # メッセージ生成
            if not is_memory_sufficient:
                message = f"メモリ不足です（最小{self.min_memory_gb}GB必要）"
            elif not is_memory_usage_ok:
                message = f"メモリ使用量が高いです（{memory_usage_percent:.1f}%）"
            elif not is_memory_recommended:
                message = f"OK（推奨{self.recommended_memory_gb}GB）"
            else:
                message = "OK"
            
            return {
                'passed': passed,
                'current': f"{total_memory_gb:.1f}GB（使用率{memory_usage_percent:.1f}%）",
                'required': f"{self.min_memory_gb}GB以上（推奨{self.recommended_memory_gb}GB）",
                'message': message,
                'available_gb': available_memory_gb,
                'usage_percent': memory_usage_percent
            }
            
        except Exception as e:
            logging.error(f"メモリチェックエラー: {e}")
            return {
                'passed': False,
                'current': "不明",
                'required': f"{self.min_memory_gb}GB以上",
                'message': "メモリの確認に失敗しました"
            }
    
    def check_disk_space(self) -> Dict:
        """ディスク容量をチェック"""
        try:
            total_disk_gb = self.system_info['total_disk_gb']
            free_disk_gb = self.system_info['free_disk_gb']
            disk_usage_percent = self.system_info['disk_usage_percent']
            
            # 最低1GB以上の空き容量が必要
            min_free_space_gb = 1
            is_disk_sufficient = free_disk_gb >= min_free_space_gb
            
            # ディスク使用量警告（90%以上）
            warning_disk_usage_percent = 90
            is_disk_usage_ok = disk_usage_percent < warning_disk_usage_percent
            
            passed = is_disk_sufficient and is_disk_usage_ok
            
            # メッセージ生成
            if not is_disk_sufficient:
                message = f"ディスク容量不足です（最小{min_free_space_gb}GB必要）"
            elif not is_disk_usage_ok:
                message = f"ディスク使用量が高いです（{disk_usage_percent:.1f}%）"
            else:
                message = "OK"
            
            return {
                'passed': passed,
                'current': f"{free_disk_gb:.1f}GB空き（使用率{disk_usage_percent:.1f}%）",
                'required': f"{min_free_space_gb}GB以上の空き容量",
                'message': message,
                'free_gb': free_disk_gb,
                'usage_percent': disk_usage_percent
            }
            
        except Exception as e:
            logging.error(f"ディスクチェックエラー: {e}")
            return {
                'passed': False,
                'current': "不明",
                'required': "1GB以上の空き容量",
                'message': "ディスク容量の確認に失敗しました"
            }
    
    def get_overall_status(self) -> Dict:
        """全体のステータスを取得"""
        try:
            all_passed = all(req['passed'] for req in self.requirements_met.values())
            
            failed_requirements = [
                name for name, req in self.requirements_met.items() 
                if not req['passed']
            ]
            
            warnings = []
            
            # メモリ使用量警告
            if ('memory' in self.requirements_met and 
                self.requirements_met['memory'].get('usage_percent', 0) > 70):
                warnings.append("メモリ使用量が高いです")
            
            # ディスク使用量警告
            if ('disk_space' in self.requirements_met and 
                self.requirements_met['disk_space'].get('usage_percent', 0) > 80):
                warnings.append("ディスク使用量が高いです")
            
            return {
                'all_passed': all_passed,
                'failed_requirements': failed_requirements,
                'warnings': warnings,
                'total_requirements': len(self.requirements_met),
                'passed_requirements': len([req for req in self.requirements_met.values() if req['passed']])
            }
            
        except Exception as e:
            logging.error(f"全体ステータス取得エラー: {e}")
            return {
                'all_passed': False,
                'failed_requirements': [],
                'warnings': ["システムステータスの確認に失敗しました"],
                'total_requirements': 0,
                'passed_requirements': 0
            }
    
    def get_detailed_report(self) -> str:
        """詳細レポートを取得"""
        try:
            report = []
            report.append("=" * 50)
            report.append("システム要件チェック結果")
            report.append("=" * 50)
            
            # システム情報
            report.append(f"チェック日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            report.append("")
            report.append("【システム情報】")
            report.append(f"Python: {self.system_info.get('python_version_str', '不明')}")
            report.append(f"OS: {self.system_info.get('os_name', '不明')} {self.system_info.get('os_release', '')}")
            report.append(f"アーキテクチャ: {self.system_info.get('architecture', '不明')}")
            report.append(f"CPU: {self.system_info.get('cpu_count', '不明')}コア")
            report.append(f"メモリ: {self.system_info.get('total_memory_gb', 0):.1f}GB")
            report.append("")
            
            # 要件チェック結果
            report.append("【要件チェック結果】")
            
            for name, req in self.requirements_met.items():
                status = "✓" if req['passed'] else "✗"
                report.append(f"{status} {name}: {req['message']}")
                report.append(f"  現在値: {req['current']}")
                report.append(f"  必要値: {req['required']}")
                report.append("")
            
            # 全体ステータス
            overall = self.get_overall_status()
            report.append("【総合結果】")
            report.append(f"要件適合: {overall['passed_requirements']}/{overall['total_requirements']}")
            report.append(f"ステータス: {'合格' if overall['all_passed'] else '不合格'}")
            
            if overall['warnings']:
                report.append("警告:")
                for warning in overall['warnings']:
                    report.append(f"  - {warning}")
            
            report.append("=" * 50)
            
            return "\n".join(report)
            
        except Exception as e:
            logging.error(f"詳細レポート生成エラー: {e}")
            return "詳細レポートの生成に失敗しました"
    
    def monitor_system_resources(self) -> Dict:
        """システムリソースを監視"""
        try:
            # 現在のリソース使用状況を取得
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('.')
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 警告レベルチェック
            warnings = []
            
            if memory.percent > 80:
                warnings.append(f"メモリ使用量が高いです: {memory.percent:.1f}%")
            
            if (disk.used / disk.total) * 100 > 90:
                warnings.append(f"ディスク使用量が高いです: {(disk.used / disk.total) * 100:.1f}%")
            
            if cpu_percent > 90:
                warnings.append(f"CPU使用量が高いです: {cpu_percent:.1f}%")
            
            return {
                'memory_percent': memory.percent,
                'disk_percent': (disk.used / disk.total) * 100,
                'cpu_percent': cpu_percent,
                'warnings': warnings,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logging.error(f"システムリソース監視エラー: {e}")
            return {
                'memory_percent': 0,
                'disk_percent': 0,
                'cpu_percent': 0,
                'warnings': ["システムリソースの監視に失敗しました"],
                'timestamp': datetime.now().isoformat()
            }

# グローバルシステム要件チェッカーインスタンス
system_requirements = SystemRequirements() 