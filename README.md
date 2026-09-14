# FCN Monitor

手機友善的 FCN 客戶/多筆產品管理第一版。

## 功能
- 客戶名稱
- 一位客戶多筆 FCN
- Strike / KI / KO / 票息 / 本金 / 日期
- 持有中、KO、到期現金贖回、到期接股
- 距 KI / KO 與到期天數
- SQLite 資料保存

## Railway 部署
1. 建立 GitHub repository。
2. 上傳本資料夾內的 4 個檔案。
3. Railway → New Project → Deploy from GitHub Repo。
4. Railway 會依 Dockerfile 建置。
5. 設定公開網域後即可使用。

注意：Railway 的單機 SQLite 適合個人測試/小量使用。正式多人使用建議改 PostgreSQL。
