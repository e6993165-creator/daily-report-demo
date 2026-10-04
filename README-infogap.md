# infogap — 全自動資訊差監控與發布系統(骨架)

四個模組:定時抓公開 RSS / API → Claude 判斷資訊差價值 → 推播 Telegram / LINE → 自動產出免費版 / 付費版成稿。

## 目錄結構

```
.
├── main.py                        # 入口:fetch / analyze / notify / publish / cycle / loop
├── requirements.txt
├── config/
│   └── config.example.yaml        # 複製為 config.yaml 後填值(config.yaml 不進版)
├── infogap/
│   ├── config.py                  # YAML + 環境變數載入;缺金鑰直接報錯
│   ├── db.py                      # SQLite:items(去重)、opportunities(狀態機)
│   ├── pipeline.py                # 四模組串接
│   ├── scheduler.py               # 行程內排程(長駐建議改 cron)
│   ├── fetcher/                   # 模組一:rss_fetcher / api_fetcher,註冊制擴充
│   ├── analyzer/                  # 模組二:Claude API + structured outputs
│   ├── notifier/                  # 模組三:Telegram Bot / LINE Messaging API
│   └── publisher/                 # 模組四:免費版 + 付費版 Markdown 成稿
├── data/infogap.db                # 執行後自動生成(不進版)
└── content/                       # 成稿輸出(不進版)
```

## 安裝與啟動

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp config/config.example.yaml config/config.yaml   # 編輯來源清單

export ANTHROPIC_API_KEY=sk-ant-...
export TELEGRAM_BOT_TOKEN=...
export TELEGRAM_CHAT_ID=...

python main.py fetch      # 先單跑一步驗證來源
python main.py cycle      # 抓→析→推 跑一輪
python main.py loop       # 長駐:每 10 分鐘一輪 + 每日 08:00 產稿
```

長駐建議用 cron 取代 `loop`(行程死掉 cron 還在):

```cron
*/10 * * * * cd /path/to/repo && .venv/bin/python main.py cycle >> logs/cycle.log 2>&1
0 8 * * *    cd /path/to/repo && .venv/bin/python main.py publish >> logs/publish.log 2>&1
```

## 部署邊界(寫出來不等於生效)

這套骨架「自動」的範圍到哪裡,如實列出:

| 環節 | 自動化程度 | 什麼觀察值出現才算上線 |
|---|---|---|
| 模組一 抓取 | 全自動 | `data/infogap.db` 的 items 筆數隨每輪增加 |
| 模組二 分析 | 全自動(需 ANTHROPIC_API_KEY) | opportunities 表出現 score ≥ 門檻的列 |
| 模組三 推播 | 全自動(需 bot token / chat_id) | 你的 Telegram / LINE 實際收到第一則訊息 |
| 模組四 產稿 | 自動到「檔案生成」為止 | `content/` 出現兩份 .md |
| 上架 Substack / 方格子 | **人工** | 兩平台皆無公開發文 API,成稿需手動貼上 |

其他已知事實與限制:

- **LINE Notify 已於 2025-03-31 終止服務**,本系統用 LINE Messaging API(官方帳號 push);免費方案每月推播則數有上限。
- 每個抓取來源上線前要自行確認 robots.txt 與使用條款;example.yaml 裡的來源只是格式示範。
- AI 的價差估算是推論不是報價:prompt 已要求沒把握就寫區間或「無法估算」,付費版成稿發出前仍應人工核對數字,錯的價差資訊發到付費訂閱是信用成本。
- 費用:模組二每批一次 API 呼叫(claude-opus-5-5,$4/$20 per MTok)。每 10 分鐘一輪、每批 20 筆短摘要,量級約每日幾十萬 input tokens;要壓成本可把 `analyzer.model` 換成 `claude-sonnet-5-5` 或拉長間隔。
- 分析請求已開 server-side fallback(安全分類器誤擋時 API 端自動換模型重跑);整條鏈都拒答時該批記 log 略過,不會無聲消失。
