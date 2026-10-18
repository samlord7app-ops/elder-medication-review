# 本機匯入與評估 API

## 啟動

需要 Python 3.10+、openpyxl（Excel 唯讀解析）、Windows 10/11 及已安裝的 Windows OCR 語言。此裝置已有 Python 和 openpyxl，可在 PowerShell 執行 `./start-local.ps1`；或執行 `python local_api.py`。其他裝置請先由管理員安裝 `openpyxl>=3.1.5`。

開啟 http://127.0.0.1:18743/ 。不要直接開啟 intake.html；它需要同來源的本機服務。結束服務可在終端按 Ctrl+C。服務只綁定 loopback，不開放院內其他裝置。不可直接改為 0.0.0.0 部署；院內正式版需另加 TLS、登入授權、使用者隔離與資安驗證。

GitHub 只存放程式碼，不接收個案資料。本機 API 並未部署到 GitHub、Render 或其他雲端。

## 流程與資料邊界

1. 圖片貼上／選檔後，使用者按本機擷取；原圖以二進位送到同一裝置的 `/api/extract/image`。Windows OCR 在本機 Temp 暫存圖片，成功或失敗均嘗試刪除；不是安全抹除，程式異常終止可能留暫存。系統不使用雲端 OCR。
2. `.xlsx` 以二進位送到同機 `/api/extract/excel`，記憶體唯讀解析，不執行公式／巨集、不追蹤外部連結；圖片、圖表與隱藏工作表不解析。舊版 `.xls` 不支援。最多 10 MB，解壓總量 40 MB，2000 筆非空白列、每表最多 2001 列與 50 欄。第一列視為標題，UI 預設所有欄皆略過。
3. 自由文字依「藥品：」「年齡：」「診斷：」「檢驗：」標籤建立候選。未知原文預設略過。這是有限格式擷取，並非通用病歷理解或完整藥品辨識。OCR 不確定字元須人工修正。
4. 所有候選預設未勾選。需校正、選類別、逐項勾選。請一次僅處理一位個案；Excel 不自動分人。
5. 產生完整 JSON 預覽後，另外勾選「不含個資」才可送出。任何原文／欄位修改、重新匯入或切表皆撤銷確認；處理中修改資料會捨棄舊結果。
6. `/api/evaluate` 僅接受以下四種頂層欄位；額外欄位一律拒絕。原圖、檔名、表名、原文、案件碼不納入請求。

姓名無法透過正則可靠辨識，因此必須由人工確認。伺服器拒絕常見證號、電話、email 及個資標籤，但不能宣稱全面自動去識別。診斷及用藥本身仍是敏感健康資料。本版不儲存個案、請求或回傳結果，不輸出個案日誌；作業系統、瀏覽器及端點防護仍可能留有裝置層紀錄。請在核准裝置處理資料，勿把原始檔放進 OneDrive 專案或 Git。

## POST /api/evaluate

前端先取得 `GET /api/session` 的記憶體 session token，POST 必須帶 `X-Local-Token`，且 Host、Origin 必須與固定本機來源一致。沒有跨網域 CORS 授權，不允許任意遠端網址或重新導向。這是同機請求防護，不是多使用者登入機制。

```json
{
  "age": 78,
  "medications": ["Valium", "Metformin"],
  "labs": [{"name": "eGFR", "value": 45, "unit": "mL/min/1.73m2"}],
  "diagnoses": ["高血壓"]
}
```

年齡為 65–120 歲整數，每類最多 100 項；檢驗項目需數值與單位。用藥至少一項。檢驗／檢查目前只支援數值型，敘述性影像報告不可直接貼入請求。

成功回傳包含 `version`、`clinicalUseReady: false`、`results`、`context` 與 `limitations`。每個結果含輸入藥品、辨識成分、狀態、類別、原因及來源。狀態包括 `potentially_inappropriate`、`no_rule_hit`、`unrecognized`。輸入錯誤回傳 400，來源／token 不符 403，過大請求 413。

目前僅四種成分辨識及三項 AGS Beers 2023 示範摘要；API 與舊介面自訂規則尚未共用。檢驗與診斷僅驗證格式，不參與臨床判讀；沒有完整台灣商品名、中文名、健保碼與許可證資料。此限制會顯示在介面與回傳結果，不能用於正式醫療判斷或評鑑。

## 驗證

`python -m unittest test_local_api` 驗證後端輸入白名單、數值邊界、個資線索、Excel 公式略過。

`node test-intake.cjs` 驗證候選預設排除、年齡歧義及請求組裝。`node verify.cjs` 驗證舊介面。

`test-browser.cjs` 需本機服務、Playwright 及 Edge；驗證確認前無評估請求、請求內容、修改後撤銷確認、token 防護及無外部請求。測試資料皆為虛構。

Windows OCR 官方說明：https://learn.microsoft.com/en-us/uwp/api/windows.media.ocr.ocrengine 。示範用藥規則來源：https://pmc.ncbi.nlm.nih.gov/articles/PMC12478568/ 。
