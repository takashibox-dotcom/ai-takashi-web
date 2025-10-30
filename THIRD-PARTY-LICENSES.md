# サードパーティライブラリ ライセンス情報

このドキュメントは、AI_takashiプロジェクトで使用しているサードパーティライブラリのライセンス情報を記録しています。

## 使用ライブラリ一覧

### PyQt5
- **バージョン:** 5.15.x
- **ライセンス:** GPL v3 / Commercial License
- **用途:** GUI framework
- **ライセンス詳細:** [PyQt5 License](https://www.riverbankcomputing.com/software/pyqt/license)
- **商用利用:** Commercial Licenseが必要

### google-generativeai
- **バージョン:** 最新
- **ライセンス:** Apache License 2.0
- **用途:** Google Generative AI API クライアント
- **ライセンス詳細:** [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0)
- **商用利用:** 可能

### matplotlib
- **バージョン:** 3.x
- **ライセンス:** Matplotlib License (based on PSF License)
- **用途:** グラフ描画
- **ライセンス詳細:** [Matplotlib License](https://matplotlib.org/stable/users/license.html)
- **商用利用:** 可能

### numpy
- **バージョン:** 1.x
- **ライセンス:** BSD 3-Clause License
- **用途:** 数値計算（matplotlibの依存関係）
- **ライセンス詳細:** [NumPy License](https://numpy.org/doc/stable/license.html)
- **商用利用:** 可能

### python-dotenv
- **バージョン:** 1.x
- **ライセンス:** BSD 3-Clause License
- **用途:** 環境変数管理
- **ライセンス詳細:** [python-dotenv License](https://github.com/theskumar/python-dotenv/blob/main/LICENSE)
- **商用利用:** 可能

### cryptography
- **バージョン:** 最新
- **ライセンス:** Apache License 2.0 / BSD 3-Clause License
- **用途:** 暗号化・復号化
- **ライセンス詳細:** [Cryptography License](https://github.com/pyca/cryptography/blob/main/LICENSE)
- **商用利用:** 可能

### pandas (オプション)
- **バージョン:** 2.x
- **ライセンス:** BSD 3-Clause License
- **用途:** データ処理
- **ライセンス詳細:** [Pandas License](https://pandas.pydata.org/pandas-docs/stable/getting_started/overview.html#license)
- **商用利用:** 可能

### openpyxl (オプション)
- **バージョン:** 3.x
- **ライセンス:** MIT License
- **用途:** Excel ファイル処理
- **ライセンス詳細:** [openpyxl License](https://openpyxl.readthedocs.io/en/stable/#licence)
- **商用利用:** 可能

### reportlab (オプション)
- **バージョン:** 4.x
- **ライセンス:** BSD 3-Clause License
- **用途:** PDF生成
- **ライセンス詳細:** [ReportLab License](https://www.reportlab.com/software/licence/)
- **商用利用:** 可能

## ライセンス分析

### 商用利用可能なライブラリ
- google-generativeai (Apache License 2.0)
- matplotlib (Matplotlib License)
- numpy (BSD 3-Clause)
- python-dotenv (BSD 3-Clause)
- cryptography (Apache License 2.0 / BSD 3-Clause)
- pandas (BSD 3-Clause)
- openpyxl (MIT License)
- reportlab (BSD 3-Clause)

### 商用利用に制限があるライブラリ
- **PyQt5**: GPL v3ライセンスのため、商用利用にはCommercial Licenseが必要
  - 代替案: PySide6 (Qt for Python) - LGPL License (商用利用可能)
  - 代替案: tkinter (Python標準ライブラリ) - Python Software Foundation License

## 推奨事項

### 商用利用のための対策
1. **PyQt5の代替検討:**
   - PySide6への移行を推奨
   - 同様の機能を提供しLGPLライセンスで商用利用可能

2. **ライセンス表記:**
   - アプリケーションのAboutダイアログにライセンス情報を表示
   - 配布時にライセンス情報を含める

3. **定期的なライセンス確認:**
   - 依存関係の更新時にライセンス変更を確認
   - 新しいライブラリ追加時の事前確認

## ライセンス遵守のための実装

### 1. About ダイアログの追加
```python
def show_about_dialog(self):
    about_text = """
    AI_takashi v1.1
    
    このソフトウェアは以下のオープンソースライブラリを使用しています：
    - PyQt5 (GPL v3)
    - google-generativeai (Apache License 2.0)
    - matplotlib (Matplotlib License)
    - cryptography (Apache License 2.0)
    
    詳細なライセンス情報は THIRD-PARTY-LICENSES.md をご参照ください。
    """
    QtWidgets.QMessageBox.about(self, "About", about_text)
```

### 2. ライセンス情報の配布
- 実行ファイルと同じディレクトリにライセンス情報を配置
- インストーラーにライセンス情報を含める

### 3. 継続的なライセンス監視
- 新しい依存関係追加時の自動チェック
- ライセンス変更の定期的な確認

## 更新履歴

| 日付 | 更新内容 | 担当者 |
|------|----------|--------|
| 2024-12-19 | 初版作成 | 開発チーム |

---

**注意:** このドキュメントは定期的に更新される必要があります。新しいライブラリの追加や既存ライブラリのアップデート時には、ライセンス情報を確認し、この文書を更新してください。 