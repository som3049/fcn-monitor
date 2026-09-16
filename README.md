# FCN Monitor 3.3
自動行情版。輸入股票代號後，總覽會透過 Yahoo Finance 公開行情介面抓取最新價格；行情快取預設 60 秒，可手動立即更新。

功能：客戶、多筆 FCN、商品代號、最多 3 檔標的、各檔獨立期初價/Strike/KI/KO、WORST-OF、KI/KO 風險提示、到期倒數、搜尋。

Railway：將 app.py、requirements.txt、Dockerfile、README.md 放入原 GitHub repo；建議建立 Volume，Mount Path `/app/data` 保存 SQLite。

注意：公開行情可能延遲、暫停或抓不到。正式 KI/KO 觸發仍以各 FCN Term Sheet 的觀察規則為準；本版是監控用途。
