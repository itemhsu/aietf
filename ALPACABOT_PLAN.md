# AlpacaBot — 全自動美股投資系統 開發計劃

**版本：** 1.0.0  
**日期：** 2026-05-24  
**作者：** itemhsu@gmail.com  
**⚠️ 免責聲明：本系統僅供資訊整理與研究參考，不構成任何投資建議。**

---

## 目錄

1. [專案概覽](#1-專案概覽)
2. [系統架構](#2-系統架構)
3. [目錄結構](#3-目錄結構)
4. [JSON 策略格式規範](#4-json-策略格式規範)
5. [JSON 報告 Model 規範](#5-json-報告-model-規範)
6. [多帳戶管理設計](#6-多帳戶管理設計)
7. [開發階段與測試計劃](#7-開發階段與測試計劃)
8. [GitHub Actions 工作流程](#8-github-actions-工作流程)
9. [Dashboard 設計規格](#9-dashboard-設計規格)
10. [Email 通知規格](#10-email-通知規格)
11. [再平衡邏輯](#11-再平衡邏輯)
12. [風險與限制](#12-風險與限制)
13. [開發者快速上手](#13-開發者快速上手)

---

## 1. 專案概覽

### 1.1 系統目標

建立一套**全自動美股投資系統**，具備以下核心能力：

| 能力 | 說明 |
|------|------|
| 🤖 自動下單 | 透過 Alpaca API 執行買賣，只買整數股 |
| 📊 視覺化儀表板 | Streamlit Dashboard，展示帳戶狀態與績效 |
| 📧 每日 Email | 每天早上 6:00 發送日報（P&L、Top 10、持倉） |
| 🔔 即時通知 | 有交易發生時立即通知 |
| 📋 歷史報告 | 所有日報以 JSON 儲存，可回查 |
| 👥 多帳戶 | 支援多帳戶，每帳戶同時只能使用一個策略 |
| 🧩 策略可插拔 | 策略以 JSON 描述，新增策略不需改 Python 程式碼 |

### 1.2 技術棧

| 元件 | 技術 |
|------|------|
| 交易 API | Alpaca Markets (paper / live) |
| 後端語言 | Python 3.11 |
| 儀表板 | Streamlit |
| 排程 | GitHub Actions (cron) |
| 通知 | Gmail SMTP / SendGrid |
| 資料儲存 | JSON 檔案 + GitHub Repository |
| 市場資料 | Alpaca Data API + yfinance (P/E ratio) |
| 比對基準 | NASDAQ (QQQ) / S&P500 (SPY) |

---

## 2. 系統架構

```
┌──────────────────────────────────────────────────────────────────┐
│                     GitHub Repository                            │
│                                                                  │
│  strategies/          accounts/           reports/              │
│  ├ top10_momentum.json ├ account_A.json   ├ 2026-05-24/          │
│  ├ top10_marketcap.json├ account_B.json   │  ├ model.json        │
│  └ conservative.json   └ ...              │  └ email.html        │
│                                           └ history_index.json  │
│                                                                  │
│  src/                                                            │
│  ├ engine/        # 核心引擎（策略執行、帳戶管理）              │
│  ├ data/          # 資料擷取（市價、市值、P/E）                 │
│  ├ report/        # 報告生成（model.py、view_email.py）         │
│  ├ dashboard/     # Streamlit 儀表板                            │
│  ├ notify/        # Email & 即時通知                            │
│  └ tests/         # 所有測試                                    │
└──────────────────────────────────────────────────────────────────┘
          │ GitHub Actions (cron / event trigger)
          ▼
┌─────────────────────────┐    ┌──────────────┐    ┌────────────┐
│   daily_workflow.yml    │───►│  Alpaca API  │    │  Gmail     │
│  （走過所有帳戶）       │    │  Trading     │    │  SMTP      │
│   1. 取市場資料         │    │  Data        │    │  06:00每日 │
│   2. 選前10檔           │    └──────────────┘    └────────────┘
│   3. 計算再平衡         │
│   4. 執行下單           │
│   5. 生成報告 JSON      │
│   6. 發送 Email         │
│   7. Commit & Push      │
└─────────────────────────┘
```

---

## 3. 目錄結構

```
alpacabot/
├── .github/
│   └── workflows/
│       ├── daily_workflow.yml      # 每日主工作流程
│       └── rebalance_trigger.yml   # 手動觸發再平衡
│
├── strategies/                     # 策略 JSON（新策略只加這裡）
│   ├── top10_marketcap.json
│   ├── top10_momentum.json
│   └── conservative_blend.json
│
├── accounts/                       # 帳戶設定（不含 API Key）
│   ├── account_template.json
│   └── accounts_index.json         # 帳戶清單與所選策略
│
├── reports/                        # 歷史報告
│   ├── history_index.json          # 所有報告索引
│   └── 2026-05-24/
│       ├── model_account_A.json    # 報告資料 model
│       └── email_account_A.html    # Email view
│
├── src/
│   ├── engine/
│   │   ├── account_manager.py      # 多帳戶管理
│   │   ├── strategy_loader.py      # 載入 JSON 策略
│   │   ├── selector.py             # 選股邏輯（依策略）
│   │   ├── rebalancer.py           # 再平衡計算
│   │   └── trader.py               # Alpaca 下單執行
│   │
│   ├── data/
│   │   ├── market_data.py          # 股價、市值
│   │   ├── benchmark.py            # QQQ / SPY 基準資料
│   │   ├── pe_ratio.py             # P/E 本益比計算
│   │   └── alpaca_client.py        # Alpaca API 封裝
│   │
│   ├── report/
│   │   ├── model.py                # 生成 report model.json
│   │   └── view_email.py           # 從 model.json 渲染 HTML email
│   │
│   ├── dashboard/
│   │   └── app.py                  # Streamlit 儀表板主程式
│   │
│   ├── notify/
│   │   ├── email_sender.py         # 發送 Email
│   │   └── trade_alert.py          # 即時交易通知
│   │
│   └── tests/                      # 測試（見第 7 節）
│
├── main.py                         # 主程式（GitHub Actions 呼叫）
├── requirements.txt
├── CLAUDE.md                       # 專案記憶文件（開發者快速上手）
└── README.md
```

---

## 4. JSON 策略格式規範

> 📌 **核心設計**：新增策略只需新增一個 JSON 檔案，不需修改任何 Python 程式碼。

### 4.1 策略 JSON 結構

```json
{
  "strategy_id": "top10_marketcap_v1",
  "name": "NASDAQ 市值前十等權重",
  "description": "每日選出 NASDAQ 市值最大前 10 檔，等權重 10% 持倉，只買整數股",
  "version": "1.0",
  "universe": {
    "exchange": "NASDAQ",
    "min_market_cap_B": 10,
    "exclude_symbols": ["BRKB"]
  },
  "selection": {
    "method": "market_cap",
    "top_n": 10,
    "ranking_field": "market_cap",
    "direction": "desc"
  },
  "allocation": {
    "method": "equal_weight",
    "weight_per_stock": 0.10,
    "share_type": "integer_only",
    "cash_buffer_pct": 0.01
  },
  "rebalance": {
    "monthly_first_day": true,
    "on_new_capital": true,
    "tolerance_pct": 0.02
  },
  "watchlist_categories": {
    "ai_tech":    ["NVDA", "MSFT", "GOOGL", "META", "AMZN"],
    "semicon":    ["TSM", "ASML", "AVGO", "AMD", "QCOM"],
    "growth":     ["NFLX", "UBER", "SNOW", "PLTR", "CRM"]
  },
  "notification": {
    "trade_alert": true,
    "daily_email": true,
    "email_time": "06:00",
    "timezone": "Asia/Taipei"
  },
  "risk_disclaimer": "本策略僅供研究參考，不構成投資建議。"
}
```

### 4.2 策略欄位說明

| 欄位 | 說明 |
|------|------|
| `strategy_id` | 唯一識別碼，帳戶設定中引用此 ID |
| `universe` | 選股範圍（交易所、最低市值篩選） |
| `selection.method` | 選股方法：`market_cap` / `momentum` / `custom` |
| `allocation.share_type` | `integer_only`（只買整數股） |
| `rebalance.tolerance_pct` | 偏差超過此值才再平衡（降低無謂交易） |
| `watchlist_categories` | 三大關注類別，顯示於 Dashboard 下方 |

---

## 5. JSON 報告 Model 規範

> 📌 **設計原則**：Model（資料）與 View（呈現）分離。報告資料儲存為 JSON，展示樣式（Email HTML、Dashboard）另行渲染。

### 5.1 日報 Model JSON

```json
{
  "report_id": "2026-05-24_account_A",
  "account_id": "account_A",
  "strategy_id": "top10_marketcap_v1",
  "date": "2026-05-24",
  "generated_at": "2026-05-24T06:00:00+08:00",

  "account_summary": {
    "nav": 102345.67,
    "cash": 1023.45,
    "cash_pct": 0.010,
    "equity": 101322.22,
    "daily_pnl": 1234.56,
    "daily_pnl_pct": 1.22,
    "total_return_pct": 2.35,
    "drawdown_pct": -1.50,
    "max_drawdown_pct": -3.20
  },

  "positions": [
    {
      "symbol": "AAPL",
      "qty": 54,
      "avg_entry_price": 185.42,
      "current_price": 192.35,
      "market_value": 10386.90,
      "weight_pct": 10.15,
      "unrealized_pnl": 374.22,
      "unrealized_pnl_pct": 3.74,
      "pe_ratio": 28.5,
      "perf_1d_pct": 0.82,
      "perf_1w_pct": 2.15,
      "perf_1m_pct": 5.43
    }
  ],

  "top10_today": [
    { "rank": 1, "symbol": "AAPL",  "market_cap_B": 2950, "selected": true },
    { "rank": 2, "symbol": "MSFT",  "market_cap_B": 2870, "selected": true }
  ],

  "trades_executed": [
    {
      "symbol": "NVDA",
      "action": "BUY",
      "qty": 10,
      "price": 875.20,
      "reason": "new_entrant",
      "executed_at": "2026-05-24T15:16:00Z"
    }
  ],

  "benchmark": {
    "qqq_1d_pct": 0.95,
    "spy_1d_pct": 0.70,
    "qqq_1m_pct": 3.20,
    "spy_1m_pct": 2.10
  },

  "nav_history": [
    { "date": "2026-05-01", "nav": 100000 },
    { "date": "2026-05-24", "nav": 102345.67 }
  ],

  "watchlist": {
    "ai_tech":  [{ "symbol": "NVDA", "price": 875.2, "1d_pct": 1.5 }],
    "semicon":  [{ "symbol": "TSM",  "price": 165.3, "1d_pct": 0.8 }],
    "growth":   [{ "symbol": "PLTR", "price": 24.5,  "1d_pct": 2.1 }]
  },

  "disclaimer": "本報告僅供資訊整理與研究參考，不構成投資建議。"
}
```

### 5.2 歷史報告索引

```json
{
  "last_updated": "2026-05-24",
  "reports": [
    { "date": "2026-05-24", "account_id": "account_A", "path": "reports/2026-05-24/model_account_A.json", "nav": 102345.67 },
    { "date": "2026-05-23", "account_id": "account_A", "path": "reports/2026-05-23/model_account_A.json", "nav": 101111.11 }
  ]
}
```

---

## 6. 多帳戶管理設計

### 6.1 帳戶索引（accounts/accounts_index.json）

```json
{
  "accounts": [
    {
      "account_id": "account_A",
      "display_name": "主帳戶",
      "alpaca_key_env": "ALPACA_KEY_A",
      "alpaca_secret_env": "ALPACA_SECRET_A",
      "alpaca_base_url_env": "ALPACA_URL_A",
      "active_strategy": "top10_marketcap_v1",
      "email_recipient": "itemhsu@gmail.com",
      "enabled": true
    },
    {
      "account_id": "account_B",
      "display_name": "測試帳戶",
      "alpaca_key_env": "ALPACA_KEY_B",
      "alpaca_secret_env": "ALPACA_SECRET_B",
      "alpaca_base_url_env": "ALPACA_URL_B",
      "active_strategy": "top10_momentum_v1",
      "email_recipient": "itemhsu@gmail.com",
      "enabled": true
    }
  ]
}
```

### 6.2 多帳戶規則

| 規則 | 說明 |
|------|------|
| 同時只用一策略 | 每帳戶的 `active_strategy` 指向一個策略 ID |
| 切換策略 | 只需修改 `active_strategy` 欄位，下次執行自動生效 |
| API Key 安全 | Key 以環境變數名稱儲存，實際值存於 GitHub Secrets |
| 帳戶停用 | `enabled: false` 可暫停帳戶，不影響其他帳戶 |

---

## 7. 開發階段與測試計劃

> 📌 **原則**：每個階段必須通過所有測試案例，才能進入下一階段。

---

### Phase 1 — 基礎建設與 Alpaca 連線（Week 1）

**交付物：**
- 專案目錄結構
- `alpaca_client.py`：封裝所有 API 呼叫
- `account_manager.py`：載入多帳戶設定
- `strategy_loader.py`：載入並驗證策略 JSON

**測試案例（tests/test_phase1.py）：**

| 測試名稱 | 驗證項目 |
|----------|----------|
| `test_alpaca_connection` | 能成功連線並取得帳戶資訊 |
| `test_get_account_nav` | NAV 為正數 float |
| `test_get_positions` | 回傳 list，每筆含 symbol/qty/price |
| `test_multi_account_load` | 正確載入 2 個帳戶設定 |
| `test_strategy_load_valid` | 載入合法策略 JSON 不報錯 |
| `test_strategy_load_invalid` | 缺少必填欄位時 raise ValueError |
| `test_account_strategy_binding` | account_A 綁定正確的策略 ID |
| `test_is_trading_day` | 週末回傳 False，交易日回傳 True |

---

### Phase 2 — 市場資料與選股（Week 2）

**交付物：**
- `market_data.py`：取得收盤價、市值
- `pe_ratio.py`：計算個股本益比（P/E）
- `benchmark.py`：取得 QQQ、SPY 基準資料
- `selector.py`：依策略 JSON 選出前 N 檔

**測試案例（tests/test_phase2.py）：**

| 測試名稱 | 驗證項目 |
|----------|----------|
| `test_fetch_prices_batch` | 25 個 symbol 一次呼叫取得收盤價 |
| `test_market_cap_calc` | market_cap = price × shares |
| `test_top10_selection_marketcap` | 正確依市值排序取前 10 |
| `test_top10_no_duplicate` | 結果無重複 symbol |
| `test_pe_ratio_positive` | P/E 為正數（或標示 N/A） |
| `test_benchmark_qqq_spy` | 能取得 QQQ、SPY 1d/1w/1m 報酬 |
| `test_watchlist_prices` | 三大類別各股票均能取得最新報價 |
| `test_missing_price_handling` | 無報價時排除該股，以次名補位 |

---

### Phase 3 — 持倉管理與再平衡（Week 3）

**交付物：**
- `rebalancer.py`：計算再平衡指令
- 支援：月初再平衡、新資金再平衡、容忍帶判斷
- 只買整數股邏輯

**測試案例（tests/test_phase3.py）：**

| 測試名稱 | 驗證項目 |
|----------|----------|
| `test_rebalance_integer_shares_only` | 計算出的 qty 均為整數 |
| `test_rebalance_no_change_within_tolerance` | 偏差 < tolerance → orders 為空 |
| `test_rebalance_exit_top10` | 不在前 10 名的持股生成全賣訂單 |
| `test_rebalance_new_entrant` | 新進前 10 名生成買入訂單 |
| `test_rebalance_new_capital` | 新資金進入時觸發再平衡 |
| `test_monthly_rebalance_trigger` | 每月 1 日觸發再平衡 |
| `test_equal_weight_10pct` | 每檔目標權重為 10% ±2% |
| `test_sell_before_buy` | 賣單排在買單之前 |
| `test_cash_buffer_maintained` | 下單後保留至少 1% 現金 |
| `test_multi_account_independent` | 兩帳戶再平衡互不干擾 |

---

### Phase 4 — 報告生成（Model / View 分離）（Week 4）

**交付物：**
- `report/model.py`：生成 `model_ACCOUNT.json`
- `report/view_email.py`：從 model JSON 渲染 Email HTML
- 歷史報告儲存至 `reports/YYYY-MM-DD/`
- `history_index.json` 自動更新

**測試案例（tests/test_phase4.py）：**

| 測試名稱 | 驗證項目 |
|----------|----------|
| `test_report_model_schema` | model JSON 包含所有必填欄位 |
| `test_report_nav_matches_alpaca` | NAV 誤差 < $0.01 |
| `test_report_pnl_calculation` | daily_pnl 計算正確 |
| `test_report_drawdown_calc` | drawdown 為負值，不超過 max_drawdown |
| `test_report_benchmark_included` | QQQ/SPY 數據存在於 model |
| `test_view_email_renders` | HTML email 不含未替換的模板變數 |
| `test_history_index_updated` | 每次生成後 history_index.json 更新 |
| `test_history_report_retrievable` | 可依日期查詢歷史報告 |
| `test_duplicate_date_overwrite` | 同日期重複生成時覆蓋，不重複 |
| `test_model_view_independence` | view 只讀 model JSON，不直接呼叫 API |

---

### Phase 5 — Streamlit Dashboard（Week 5）

**交付物：**
- `dashboard/app.py`：完整儀表板
- 現金水位、持倉表、績效圖表
- NAV vs QQQ/SPY 比對折線圖（可勾選）
- 三大類別關注股票區塊

**測試案例（tests/test_phase5.py）：**

| 測試名稱 | 驗證項目 |
|----------|----------|
| `test_dashboard_loads` | Streamlit app 啟動不報錯 |
| `test_cash_display` | 現金水位正確顯示 |
| `test_positions_table` | 持倉表有 1d/1w/1m 績效欄位 |
| `test_nav_chart_data` | NAV 歷史資料長度 ≥ 1 |
| `test_benchmark_toggle` | QQQ/SPY 可獨立勾選顯示 |
| `test_drawdown_chart` | 回撤圖負值朝下顯示 |
| `test_watchlist_section` | 三大類別各股票均顯示 |
| `test_multi_account_selector` | 可切換帳戶 |
| `test_history_report_selector` | 可回查歷史日期 |

---

### Phase 6 — Email 通知與即時警報（Week 6）

**交付物：**
- `notify/email_sender.py`：每日 6:00 發送 Email
- `notify/trade_alert.py`：有交易時即時通知
- Email 內容：P&L、Top 10、持倉、關注股、免責聲明

**測試案例（tests/test_phase6.py）：**

| 測試名稱 | 驗證項目 |
|----------|----------|
| `test_email_renders_from_model` | 從 model JSON 正確渲染 Email |
| `test_email_contains_disclaimer` | Email 含免責聲明文字 |
| `test_email_pnl_positive_green` | 正收益顯示綠色 |
| `test_email_pnl_negative_red` | 負收益顯示紅色 |
| `test_trade_alert_on_buy` | 買入後 trade_alert 被呼叫 |
| `test_trade_alert_on_sell` | 賣出後 trade_alert 被呼叫 |
| `test_email_send_mock` | Mock SMTP 不實際發信，驗證呼叫正確 |
| `test_multi_account_separate_email` | 兩帳戶各自發送各自的 Email |

---

### Phase 7 — GitHub Actions 整合（Week 7）

**交付物：**
- `.github/workflows/daily_workflow.yml`
- 走過所有帳戶，依各帳戶策略執行完整流程
- 手動觸發再平衡 workflow

**測試案例（tests/test_phase7.py）：**

| 測試名稱 | 驗證項目 |
|----------|----------|
| `test_main_dry_run_all_accounts` | DRY_RUN=true 走過所有帳戶不下單 |
| `test_main_skips_non_trading_day` | 非交易日不執行，exit 0 |
| `test_main_report_committed` | 執行後 reports/ 有新檔案 |
| `test_main_history_index_updated` | history_index.json 有今日記錄 |
| `test_workflow_yml_syntax` | YAML 語法正確（用 yamllint） |

---

### Phase 8 — Paper Trading 驗證（Week 8-10）

**目標：** 連續 15 個交易日 Paper 運行，無異常後才考慮 Live。

| 驗證項目 | 通過標準 |
|----------|----------|
| GitHub Actions 每日觸發 | 無失敗 run |
| NAV 計算 | 與 Alpaca 帳戶誤差 < $0.01 |
| Email 每日收到 | 6:00 準時到達 |
| 交易即時通知 | 有下單時 5 分鐘內收到 |
| 歷史報告可查 | 所有日期均有 JSON 存檔 |
| Dashboard 可瀏覽 | 所有圖表正常顯示 |

---

## 8. GitHub Actions 工作流程

### 8.1 daily_workflow.yml 流程

```yaml
name: AlpacaBot Daily Workflow

on:
  schedule:
    # 台灣時間 06:00 = UTC 22:00（前一天）
    - cron: '0 22 * * 0-4'
  workflow_dispatch:
    inputs:
      dry_run:
        description: '僅模擬不下單'
        default: 'true'
      account_filter:
        description: '指定帳戶 ID（留空 = 全部）'
        default: ''

jobs:
  run-all-accounts:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r requirements.txt
      - name: Run AlpacaBot
        env:
          ALPACA_KEY_A:    ${{ secrets.ALPACA_KEY_A }}
          ALPACA_SECRET_A: ${{ secrets.ALPACA_SECRET_A }}
          ALPACA_URL_A:    ${{ secrets.ALPACA_URL_A }}
          ALPACA_KEY_B:    ${{ secrets.ALPACA_KEY_B }}
          ALPACA_SECRET_B: ${{ secrets.ALPACA_SECRET_B }}
          ALPACA_URL_B:    ${{ secrets.ALPACA_URL_B }}
          EMAIL_USER:      ${{ secrets.EMAIL_USER }}
          EMAIL_PASS:      ${{ secrets.EMAIL_PASS }}
          DRY_RUN:         ${{ inputs.dry_run || 'false' }}
          ACCOUNT_FILTER:  ${{ inputs.account_filter || '' }}
        run: python main.py
      - name: Commit reports
        run: |
          git config user.name "AlpacaBot"
          git config user.email "actions@github.com"
          git add reports/ accounts/
          git diff --staged --quiet || git commit -m "📊 Daily report $(date -u +%Y-%m-%d)"
          git push
```

### 8.2 main.py 執行流程（走過所有帳戶）

```
for 每個 enabled 帳戶:
  1. 載入帳戶設定 → 取得 active_strategy
  2. 載入策略 JSON
  3. 確認今日為交易日
  4. 取得市場資料（前 10 名 NASDAQ）
  5. 計算再平衡指令
  6. 執行下單（DRY_RUN=false 時）
  7. 有交易 → 發送即時通知
  8. 生成 report model JSON
  9. 渲染 Email HTML（view）
  10. 發送 Email
  11. 更新 history_index.json
```

---

## 9. Dashboard 設計規格

### 9.1 頁面結構

```
┌─────────────────────────────────────────────────────┐
│  🤖 AlpacaBot Dashboard  [帳戶選擇 ▼]  [日期選擇 ▼] │
├─────────────────────────────────────────────────────┤
│  💰 現金水位      📈 今日 P&L    📊 總報酬率         │
│  $1,023  (1%)     +$1,234(+1.2%)   +2.35%           │
├─────────────────────────────────────────────────────┤
│  NAV 歷史折線圖（可勾選：■ 我的 NAV ■ QQQ ■ SPY）  │
│  [回撤圖]（可勾選：■ 我的 ■ QQQ ■ SPY）            │
├─────────────────────────────────────────────────────┤
│  持倉表格                                           │
│  股票 | 股數 | 均價 | 現價 | 市值 | P/E | 1d% | 1w% | 1m% │
├─────────────────────────────────────────────────────┤
│  今日 NASDAQ 市值前 10（前 10 名醒目標示）           │
├─────────────────────────────────────────────────────┤
│  關注類別（來自策略 JSON watchlist_categories）      │
│  [AI 科技] NVDA MSFT GOOGL META AMZN                │
│  [半導體]  TSM ASML AVGO AMD QCOM                   │
│  [成長股]  NFLX UBER SNOW PLTR CRM                 │
└─────────────────────────────────────────────────────┘
```

---

## 10. Email 通知規格

### 10.1 每日 Email 內容（早上 6:00 台灣時間）

```
主旨：📊 AlpacaBot 日報 2026-05-24 | NAV: $102,345 | 今日 +1.22%

━━━ 帳戶總覽 ━━━
💰 NAV：$102,345.67
📈 今日損益：+$1,234.56（+1.22%）
🏦 現金水位：$1,023.45（1.0%）
📉 最大回撤：-3.20%

━━━ 持倉前 5 名（依市值） ━━━
1. AAPL  54 股  $10,386 | 今日 +0.82% | 1週 +2.15%
2. MSFT  38 股  $10,298 | 今日 +1.05% | 1週 +3.20%
...

━━━ 今日執行交易 ━━━
✅ 買入 NVDA × 10 股 @ $875.20

━━━ NASDAQ 市值前 10 ━━━
1. AAPL  $2,950B  2. MSFT  $2,870B  ...

━━━ 我的關注股 ━━━
[AI 科技] NVDA +1.5%  MSFT +1.1%  ...
[半導體]  TSM +0.8%  ASML +0.5%  ...
[成長股]  PLTR +2.1%  NFLX -0.3% ...

━━━ 與大盤比較 ━━━
我的 NAV：+1.22% | QQQ：+0.95% | SPY：+0.70%

⚠️ 本報告僅供資訊整理與研究參考，不構成投資建議。
```

---

## 11. 再平衡邏輯

### 11.1 觸發條件

| 觸發 | 條件 |
|------|------|
| 每月初 | 每月 1 日（或最近交易日）強制再平衡 |
| 新資金 | 帳戶現金超過 NAV 的 5% 時觸發 |
| 容忍帶 | 任一持股偏差超過 ±2% 時觸發調整 |

### 11.2 計算規則

```
目標每檔價值 = NAV × 10%
可買股數 = floor( 目標每檔價值 / 股價 )   ← 只買整數股

賣出邏輯：先賣出不在前 10 名的持股（全數賣出）
買入邏輯：依賣出後的現金計算可買整數股數
保留緩衝：每次下單後保留 1% 現金
```

---

## 12. 風險與限制

| 項目 | 說明 |
|------|------|
| ⚠️ 非投資建議 | 所有輸出均為資訊整理，不構成投資建議 |
| 靜態流通股數 | 市值計算依賴靜態資料，每季需手動更新 |
| P/E 資料延遲 | yfinance P/E 非即時，僅供參考 |
| 整數股限制 | 只買整數股可能造成小幅權重誤差 |
| 非交易日 | 非交易日 workflow 自動跳過 |
| Paper 優先 | 強烈建議至少 Paper 運行 4 週再考慮 Live |

---

## 13. 開發者快速上手

> 本節同步寫入 `CLAUDE.md`，確保 AI 輔助工具與人類開發者都能快速掌握專案狀態。

### 13.1 關鍵設計決策

1. **策略即 JSON**：策略邏輯描述於 `strategies/*.json`，`selector.py` 動態讀取，新增策略零程式碼修改
2. **Model/View 分離**：`report/model.py` 只產資料，`report/view_email.py` 只管樣式，互不耦合
3. **多帳戶由 workflow 串接**：`main.py` 讀取 `accounts_index.json`，依序執行每個帳戶
4. **只買整數股**：`rebalancer.py` 所有計算結果套用 `math.floor()`
5. **GitHub Secrets 管理 Key**：帳戶 JSON 只存環境變數名稱，不存實際 Key

### 13.2 快速啟動指令

```bash
# 安裝
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 複製環境變數範本
cp .env.example .env  # 填入 Alpaca Key

# DRY_RUN 測試（不下單）
DRY_RUN=true python main.py

# 執行測試
pytest src/tests/ -v --tb=short

# 啟動 Dashboard
streamlit run src/dashboard/app.py
```

### 13.3 新增策略步驟

1. 複製 `strategies/top10_marketcap.json`
2. 修改 `strategy_id`、`selection.method` 等欄位
3. 在 `accounts_index.json` 中將目標帳戶的 `active_strategy` 改為新 ID
4. 執行 `DRY_RUN=true python main.py` 驗證

---

## 附錄 A：requirements.txt

```txt
alpaca-py>=0.26.0
yfinance>=0.2.40
streamlit>=1.35.0
pandas>=2.2.0
plotly>=5.20.0
requests>=2.31.0
python-dotenv>=1.0.0
jinja2>=3.1.0
pytest>=8.0.0
pytest-cov>=5.0.0
responses>=0.25.0
yamllint>=1.35.0
```

## 附錄 B：GitHub Secrets 清單

| Secret 名稱 | 說明 |
|-------------|------|
| `ALPACA_KEY_A` | 帳戶 A 的 Alpaca API Key |
| `ALPACA_SECRET_A` | 帳戶 A 的 Alpaca Secret Key |
| `ALPACA_URL_A` | 帳戶 A 的 Base URL (paper/live) |
| `ALPACA_KEY_B` | 帳戶 B（依需求增加） |
| `EMAIL_USER` | 發信 Gmail 帳號 |
| `EMAIL_PASS` | Gmail App Password |

---

*AlpacaBot v1.0.0 · 最後更新 2026-05-24 · itemhsu@gmail.com*  
*⚠️ 本計劃文件及系統所有輸出，均僅供資訊整理與研究參考，不構成任何投資建議。*
