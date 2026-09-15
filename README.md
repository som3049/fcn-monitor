# FCN Monitor 3.2
客戶 × 商品代號 × 最多三檔連結標的的 Streamlit FCN 監控。

功能：
- 一客戶多筆 FCN
- 商品代號
- 最多 3 檔連結標的
- 每檔獨立期初價、Strike、KI、KO、目前價格
- WORST-OF
- KI / 接近 KI / KO 提示
- 到期倒數
- 客戶 / 商品 / 標的搜尋
- SQLite 資料庫

Railway：
1. 用本 ZIP 內四個檔案取代 GitHub repo 的 app.py、requirements.txt、Dockerfile、README.md。
2. Commit / Push。
3. Railway 會自動部署。
4. 建議建立 Volume，Mount Path：/app/data，保存 SQLite 資料。

注意：目前價格是手動輸入。正式 KI 是否觸發，仍應以每檔 FCN 的正式 Term Sheet（盤中、收盤或指定觀察時點）為準。
