# FCN Monitor 3.0
可部署的 FCN 客戶／多筆產品管理版。

## 已包含
- 客戶名稱與一位客戶多筆 FCN
- FCN 新增、編輯、刪除
- Strike / KI / KO / 本金 / 票息 / 日期
- 持有中、KO 出場、到期現金贖回、到期接股
- 距 KI / Strike / KO、到期倒數
- KI 曾觸及欄位
- 客戶視角總覽
- SQLite 持久化資料

## Railway
將 `app.py`、`requirements.txt`、`Dockerfile` 上傳到 GitHub，Railway 從 GitHub repo 部署即可。
部署成功後，在「服務 → 設定 → 網路 → 公共網路 → 生成域」產生公開網址。
