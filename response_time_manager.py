import json
import logging
import statistics
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from pathlib import Path

class ResponseTimeEntry:
    """応答時間エントリー"""
    
    def __init__(self, response_time: float, user_text_length: int = 0, 
                 ai_text_length: int = 0, timestamp: datetime = None):
        self.response_time = response_time
        self.user_text_length = user_text_length
        self.ai_text_length = ai_text_length
        self.timestamp = timestamp or datetime.now()
    
    def to_dict(self) -> Dict:
        """辞書形式に変換"""
        return {
            'response_time': self.response_time,
            'user_text_length': self.user_text_length,
            'ai_text_length': self.ai_text_length,
            'timestamp': self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ResponseTimeEntry':
        """辞書からインスタンスを作成"""
        return cls(
            response_time=data['response_time'],
            user_text_length=data.get('user_text_length', 0),
            ai_text_length=data.get('ai_text_length', 0),
            timestamp=datetime.fromisoformat(data['timestamp'])
        )

class ResponseTimeManager:
    """応答時間管理クラス"""
    
    def __init__(self, history_file: str = None):
        if history_file is None:
            # ユーザーのホームディレクトリに設定ファイルを作成
            home_dir = Path.home()
            ai_config_dir = home_dir / ".ai_takashi_config"
            ai_config_dir.mkdir(exist_ok=True)
            history_file = ai_config_dir / "response_time_history.json"
        self.history_file = str(history_file)
        self.history: List[ResponseTimeEntry] = []
        self.max_history_days = 90  # 90日分の履歴を保持
        self.max_history_count = 1000  # 最大1000件の履歴
        
        # 警告しきい値設定
        self.warning_threshold = 10.0  # 10秒以上で警告
        self.slow_threshold = 20.0     # 20秒以上で低速警告
        
        # 統計情報キャッシュ
        self._stats_cache = {}
        self._stats_cache_time = None
        self._cache_validity_minutes = 5
        
        self.load_history()
    
    def load_history(self):
        """応答時間履歴を読み込み"""
        try:
            if Path(self.history_file).exists():
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.history = [ResponseTimeEntry.from_dict(entry) for entry in data]
                
                # 古い履歴を削除
                self.cleanup_old_history()
                
                logging.info(f"応答時間履歴{len(self.history)}件を読み込みました")
            else:
                self.history = []
                logging.info("新しい応答時間履歴ファイルを作成します")
                
        except FileNotFoundError:
            self.history = []
            logging.info("応答時間履歴ファイルが見つかりません。新規作成します。")
        except json.JSONDecodeError as e:
            self.history = []
            logging.error(f"応答時間履歴ファイルのJSON解析エラー: {e}")
        except PermissionError as e:
            self.history = []
            logging.warning(f"権限エラーで応答時間履歴を読み込めません: {e}")
        except Exception as e:
            self.history = []
            logging.error(f"予期しない応答時間履歴読み込みエラー: {e}", exc_info=True)
    
    def save_history(self):
        """応答時間履歴を保存"""
        try:
            data = [entry.to_dict() for entry in self.history]
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logging.debug(f"応答時間履歴{len(self.history)}件を保存しました")
            
        except PermissionError as e:
            logging.warning(f"権限エラーで応答時間履歴を保存できません: {e}")
        except Exception as e:
            logging.error(f"応答時間履歴保存エラー: {e}")
    
    def add_response_time(self, response_time: float, user_text: str = "", 
                         ai_text: str = "") -> bool:
        """応答時間を記録"""
        try:
            entry = ResponseTimeEntry(
                response_time=response_time,
                user_text_length=len(user_text),
                ai_text_length=len(ai_text)
            )
            
            self.history.append(entry)
            
            # 最大件数チェック
            if len(self.history) > self.max_history_count:
                self.history = self.history[-self.max_history_count:]
            
            # 統計キャッシュをクリア
            self._stats_cache = {}
            self._stats_cache_time = None
            
            self.save_history()
            
            logging.debug(f"応答時間を記録しました: {response_time:.2f}秒")
            return True
            
        except Exception as e:
            logging.error(f"応答時間記録エラー: {e}")
            return False
    
    def cleanup_old_history(self):
        """古い履歴を削除"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.max_history_days)
            
            before_count = len(self.history)
            self.history = [entry for entry in self.history if entry.timestamp > cutoff_date]
            after_count = len(self.history)
            
            if before_count > after_count:
                logging.info(f"古い応答時間履歴{before_count - after_count}件を削除しました")
                self.save_history()
                
        except Exception as e:
            logging.error(f"古い履歴削除エラー: {e}")
    
    def get_statistics(self, days: int = 7) -> Dict:
        """応答時間統計を取得"""
        try:
            # キャッシュチェック
            cache_key = f"stats_{days}"
            if (self._stats_cache_time and 
                datetime.now() - self._stats_cache_time < timedelta(minutes=self._cache_validity_minutes) and
                cache_key in self._stats_cache):
                return self._stats_cache[cache_key]
            
            # 指定期間内の履歴を取得
            cutoff_date = datetime.now() - timedelta(days=days)
            recent_history = [entry for entry in self.history if entry.timestamp > cutoff_date]
            
            if not recent_history:
                return {
                    'total_count': 0,
                    'average_time': 0,
                    'median_time': 0,
                    'min_time': 0,
                    'max_time': 0,
                    'std_deviation': 0,
                    'warning_count': 0,
                    'slow_count': 0,
                    'fast_responses': 0,  # 3秒以下
                    'period_days': days
                }
            
            response_times = [entry.response_time for entry in recent_history]
            
            # 基本統計
            total_count = len(response_times)
            average_time = statistics.mean(response_times)
            median_time = statistics.median(response_times)
            min_time = min(response_times)
            max_time = max(response_times)
            std_deviation = statistics.stdev(response_times) if len(response_times) > 1 else 0
            
            # しきい値ベースの統計
            warning_count = len([t for t in response_times if t > self.warning_threshold])
            slow_count = len([t for t in response_times if t > self.slow_threshold])
            fast_responses = len([t for t in response_times if t <= 3.0])
            
            stats = {
                'total_count': total_count,
                'average_time': average_time,
                'median_time': median_time,
                'min_time': min_time,
                'max_time': max_time,
                'std_deviation': std_deviation,
                'warning_count': warning_count,
                'slow_count': slow_count,
                'fast_responses': fast_responses,
                'period_days': days,
                'warning_percentage': (warning_count / total_count) * 100 if total_count > 0 else 0,
                'slow_percentage': (slow_count / total_count) * 100 if total_count > 0 else 0,
                'fast_percentage': (fast_responses / total_count) * 100 if total_count > 0 else 0
            }
            
            # キャッシュに保存
            self._stats_cache[cache_key] = stats
            self._stats_cache_time = datetime.now()
            
            return stats
            
        except Exception as e:
            logging.error(f"応答時間統計取得エラー: {e}")
            return {}
    
    def get_hourly_statistics(self, days: int = 7) -> List[Dict]:
        """時間帯別統計を取得"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            recent_history = [entry for entry in self.history if entry.timestamp > cutoff_date]
            
            # 時間別にグループ化
            hourly_data = {}
            for entry in recent_history:
                hour = entry.timestamp.hour
                if hour not in hourly_data:
                    hourly_data[hour] = []
                hourly_data[hour].append(entry.response_time)
            
            # 各時間の統計を計算
            hourly_stats = []
            for hour in range(24):
                if hour in hourly_data:
                    times = hourly_data[hour]
                    hourly_stats.append({
                        'hour': hour,
                        'count': len(times),
                        'average_time': statistics.mean(times),
                        'min_time': min(times),
                        'max_time': max(times)
                    })
                else:
                    hourly_stats.append({
                        'hour': hour,
                        'count': 0,
                        'average_time': 0,
                        'min_time': 0,
                        'max_time': 0
                    })
            
            return hourly_stats
            
        except Exception as e:
            logging.error(f"時間帯別統計取得エラー: {e}")
            return []
    
    def get_performance_trend(self, days: int = 30) -> List[Dict]:
        """パフォーマンストレンドを取得"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            recent_history = [entry for entry in self.history if entry.timestamp > cutoff_date]
            
            # 日別にグループ化
            daily_data = {}
            for entry in recent_history:
                date_key = entry.timestamp.date()
                if date_key not in daily_data:
                    daily_data[date_key] = []
                daily_data[date_key].append(entry.response_time)
            
            # 日別統計を生成
            trend_data = []
            for i in range(days):
                date = (datetime.now() - timedelta(days=days-1-i)).date()
                if date in daily_data:
                    times = daily_data[date]
                    trend_data.append({
                        'date': date.isoformat(),
                        'count': len(times),
                        'average_time': statistics.mean(times),
                        'min_time': min(times),
                        'max_time': max(times)
                    })
                else:
                    trend_data.append({
                        'date': date.isoformat(),
                        'count': 0,
                        'average_time': 0,
                        'min_time': 0,
                        'max_time': 0
                    })
            
            return trend_data
            
        except Exception as e:
            logging.error(f"パフォーマンストレンド取得エラー: {e}")
            return []
    
    def check_performance_warnings(self, response_time: float) -> List[str]:
        """パフォーマンス警告をチェック"""
        warnings = []
        
        try:
            if response_time > self.slow_threshold:
                warnings.append(f"応答時間が非常に遅いです: {response_time:.2f}秒 (しきい値: {self.slow_threshold}秒)")
            elif response_time > self.warning_threshold:
                warnings.append(f"応答時間が遅いです: {response_time:.2f}秒 (しきい値: {self.warning_threshold}秒)")
            
            # 最近の平均と比較
            recent_stats = self.get_statistics(days=7)
            if recent_stats.get('total_count', 0) > 5:
                avg_time = recent_stats['average_time']
                if response_time > avg_time * 2:
                    warnings.append(f"最近の平均より大幅に遅いです: {response_time:.2f}秒 (平均: {avg_time:.2f}秒)")
            
        except Exception as e:
            logging.error(f"パフォーマンス警告チェックエラー: {e}")
        
        return warnings
    
    def get_detailed_report(self, days: int = 30) -> str:
        """詳細レポートを生成"""
        try:
            stats = self.get_statistics(days)
            
            if stats.get('total_count', 0) == 0:
                return f"過去{days}日間の応答時間データがありません。"
            
            report = []
            report.append("=" * 50)
            report.append(f"応答時間レポート (過去{days}日間)")
            report.append("=" * 50)
            report.append(f"レポート生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            report.append("")
            
            # 基本統計
            report.append("【基本統計】")
            report.append(f"総応答数: {stats['total_count']}件")
            report.append(f"平均応答時間: {stats['average_time']:.2f}秒")
            report.append(f"中央値応答時間: {stats['median_time']:.2f}秒")
            report.append(f"最短応答時間: {stats['min_time']:.2f}秒")
            report.append(f"最長応答時間: {stats['max_time']:.2f}秒")
            report.append(f"標準偏差: {stats['std_deviation']:.2f}秒")
            report.append("")
            
            # パフォーマンス分析
            report.append("【パフォーマンス分析】")
            report.append(f"高速応答 (≤3秒): {stats['fast_responses']}件 ({stats['fast_percentage']:.1f}%)")
            report.append(f"警告レベル (>{self.warning_threshold}秒): {stats['warning_count']}件 ({stats['warning_percentage']:.1f}%)")
            report.append(f"低速レベル (>{self.slow_threshold}秒): {stats['slow_count']}件 ({stats['slow_percentage']:.1f}%)")
            report.append("")
            
            # 推奨事項
            report.append("【推奨事項】")
            if stats['warning_percentage'] > 20:
                report.append("- 警告レベルの応答が多いです。システムリソースを確認してください。")
            if stats['slow_percentage'] > 5:
                report.append("- 低速応答が頻発しています。ネットワーク接続を確認してください。")
            if stats['average_time'] > 8:
                report.append("- 平均応答時間が長いです。API設定を見直してください。")
            
            if stats['warning_percentage'] <= 10 and stats['average_time'] <= 5:
                report.append("- 良好なパフォーマンスです。")
            
            report.append("=" * 50)
            
            return "\n".join(report)
            
        except Exception as e:
            logging.error(f"詳細レポート生成エラー: {e}")
            return "レポートの生成に失敗しました。"
    
    def update_settings(self, warning_threshold: float = None, 
                       slow_threshold: float = None,
                       max_history_days: int = None):
        """設定を更新"""
        try:
            if warning_threshold is not None:
                self.warning_threshold = warning_threshold
            
            if slow_threshold is not None:
                self.slow_threshold = slow_threshold
                
            if max_history_days is not None:
                self.max_history_days = max_history_days
                self.cleanup_old_history()
            
            logging.info("応答時間管理設定を更新しました")
            return True
            
        except Exception as e:
            logging.error(f"設定更新エラー: {e}")
            return False

# グローバル応答時間マネージャーインスタンス
response_time_manager = ResponseTimeManager() 