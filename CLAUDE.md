# AlpacaBot — 專案記憶文件

> 給 AI 助理 (Claude) 和新加入的開發者快速了解這個專案。

## 專案目的

全自動美股投資系統，透過 Alpaca API 執行 NASDAQ 市值前 10 等權重策略。  
每天台灣時間 06:00 透過 GitHub Actions 自動執行選股、再平衡、發送日報 Email。

## 核心設計決策（不要輕易改動）

1. **策略即 JSON**  
   - 所有投資策略存於 `strategies/*.json`
   - 新增策略**只需新增 JSON 檔**，無需修改 Python
   - `src/engine/strategy_loader.py` 動態載入

2. **報告 Model/View 分離**  
   - `src/report/model.py`：只產資料，儲存為 JSON
   - `src/report/view_email.py`：只渲染樣式，不呼叫 API
   - 互不耦合

3. **只買整數股**  
   - `src/engine/rebalancer.py` 所有買賣量用 `math.floor()`
   - 永不下分數股訂單

4. **多帳戶**  
   - 帳戶設定：`accounts/accounts_index.json`
   - API Key 只存環境變數名稱（實際值在 GitHub Secrets）
   - 每帳戶同時只能使用一個策略（`active_strategy` 欄位）

5. **DRY_RUN 優先**  
   - 預設 `DRY_RUN=true`，需明確設 false 才實際下單
   - GitHub Actions 手動觸發預設 dry_run=true

## 目錄結構速覽

```
strategies/       ← 策略 JSON（只在這裡新增策略）
accounts/         ← 帳戶設定 JSON
reports/          ← 日報 JSON（自動生成）
src/data/         ← 市場資料 (alpaca_client, market_data, pe_ratio, benchmark)
src/engine/       ← 核心引擎 (account_manager, strategy_loader, selector, rebalancer, trader)
src/report/       ← 報告 (model.py, view_email.py)
src/dashboard/    ← Streamlit 儀表板 (app.py)
src/notify/       ← 通知 (email_sender.py, trade_alert.py)
src/tests/        ← 測試 (test_phase1.py ~ test_phase7.py)
main.py           ← 主程式入口（GitHub Actions 呼叫）
```

## Dashboard 雲端化設計（重要）

Dashboard 採用**零 API 呼叫**設計：
- `src/dashboard/data.py`：純 JSON 讀取函式（可單獨測試）
- `src/dashboard/app.py`：Streamlit UI，只讀 JSON，不呼叫 Alpaca/yfinance
- `benchmark_nav_history`（QQQ/SPY 歷史）由 GitHub Actions 預先存入報告 JSON
- 部署至 Streamlit Community Cloud 只需連結 GitHub repo，不需任何 API 金鑰

**Streamlit Cloud 部署步驟：**
1. 前往 https://streamlit.io/cloud → New app
2. 選擇 `itemhsu/aietf` repo，Branch: `main`，Main file: `streamlit_app.py`
3. 點擊 Deploy（無需設定任何 Secrets）

## 快速啟動

```bash
cp .env.example .env    # 填入 Alpaca Key & Gmail
pip install -r requirements.txt
DRY_RUN=true python3 main.py        # 模擬執行
streamlit run src/dashboard/app.py  # 啟動 Dashboard
pytest src/tests/ -v                # 執行所有測試（71 個）
```

## 新增策略步驟

1. 複製 `strategies/top10_marketcap.json`
2. 修改 `strategy_id`（必須唯一）和選股邏輯
3. 在 `accounts/accounts_index.json` 將帳戶的 `active_strategy` 改為新 ID
4. `DRY_RUN=true python main.py` 驗證

## 新增帳戶步驟

1. 複製 `accounts/account_template.json`，填入正確欄位
2. 加入 `accounts/accounts_index.json` 的 `accounts` 陣列
3. 在 GitHub Secrets 設定對應的 API Key 環境變數
4. 設定 `enabled: true`

## 測試階段

| 檔案 | 涵蓋 |
|------|------|
| test_phase1.py | Alpaca 連線、多帳戶、策略載入 |
| test_phase2.py | 市場資料、選股、P/E、基準指數 |
| test_phase3.py | 再平衡邏輯（整數股、容忍帶、新資金）|
| test_phase4.py | 報告 Model/View 分離、歷史儲存 |
| test_phase6.py | Email 通知、即時警報 |
| test_phase7.py | 主程式整合、YAML 語法 |

## 重要環境變數

| 變數 | 說明 |
|------|------|
| `ALPACA_KEY_A` / `ALPACA_SECRET_A` / `ALPACA_URL_A` | 帳戶 A |
| `EMAIL_USER` / `EMAIL_PASS` | Gmail SMTP |
| `DRY_RUN` | `true` = 不下單，`false` = 實際下單 |
| `ACCOUNT_FILTER` | 指定單一帳戶（留空 = 全部）|

## 免責聲明

本系統所有輸出均僅供資訊整理與研究參考，不構成任何投資建議。
