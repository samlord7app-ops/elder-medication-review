# 已匯入的公開資料與使用界線

使用者已於 2026-10-18 確認 Beers 2023、STOPP/START v3、PIM-Taiwan 2018 可匯入為參考文獻。確認記錄與當時檔案 SHA-256 保存在 `public_reference/reference-approvals.json`。介面僅在當前檔案雜湊一致時顯示「已確認可匯入」；來源更新改變版本後會重新顯示待確認。此確認不等同完整規則已實作或完成臨床驗證，也不改變原文使用授權。

## 手動版本檢核與更新

工作台新增「檢查公開資料更新」。只在按鈕觸發時下載八個固定公開來源，檢查本機檔案 SHA-256。TFDA 與健保目錄另計算新增、移除及內容變動的分組：TFDA 依許可證與完整中英文品名；健保依藥碼與生效起迄。同組多筆資料保留為集合，比較的是群組內容，不是病人或獨立藥品數。

檢查只寫入 `public_reference/update-staging/<checkId>/`，不改動現用檔案。不相同／新增的來源才可勾選，必須再確認才更新；相同或下載失敗的來源不可選。失敗不代表已是最新。更新前會檢查本機自檢核後是否被改動、驗證暫存檔雜湊；目錄更新先於暫存區完成索引與公開資料壓縮包重建。全部舊檔集中到 `public_reference/已不參考/<時間與批次>/`，保留原檔及更新記錄後才替換；替換失敗會嘗試復原。該資料夾及暫存區均不納入 Git、不參與目錄查詢。更新期間暫停評估 API。

這是相同 URL 的快照差異檢查：不保證發現新出版的 Beers／STOPP／PIM-Taiwan 版本。仿單與技術網頁的動態 HTML 也可能造成雜湊變動，須人工確認，不能據此宣稱準則更新。文獻檔更新不會自動新增或啟用任何臨床規則。本版來源設定為固定白名單，無法由病歷文字指定下載網址。檢核／更新請求只接受工作 ID 與公開來源 ID，不接受個案欄位。

匯入日：2026-10-18（Asia/Taipei）。所有下載僅取得公開資料，更新程式不讀取個案，也不由評估 API 觸發。完整來源、下載雜湊及時間保存在 `public_reference/*-manifest.json`。

|來源|本機內容|啟用狀態|
|---|---|---|
|TFDA 全部藥品許可證 https://data.gov.tw/dataset/9122|72,074 原始列；去重後 66,512 筆|已接本機 API 精確辨識|
|健保署品項 https://data.gov.tw/dataset/23715|224,896 原始列；含歷史給付異動|已接本機 API 精確辨識|
|AGS Beers 2023 DOI 10.1111/jgs.18372|30 頁原文 PDF；大學公開典藏副本 https://geriatrictoolkit.missouri.edu/drug/Beers-Criteria-AGS-2023.pdf|文獻參考；仍只有原先三項示範規則|
|STOPP/START version 3 DOI 10.1007/s41999-023-00777-y|Europe PMC 全文 XML、表格、準則 PDF 附件及參考文獻附件|文獻參考／待藥師覆核；尚未啟用為規則|
|PIM-Taiwan 2018（2019 發表） DOI 10.1177/2040622319879602|Europe PMC 全文 XML、純文字與五個表格|文獻參考／待覆核；尚未啟用為規則|
|DailyMed Lipitor 仿單|本機 HTML 快照|辨識來源，不當成 Beers 風險規則|
|Microsoft Windows OCR 文件|本機 HTML 快照|技術參考|

STOPP/START 原文與附件的作者、出版及 CC BY 4.0 授權資訊保留在原始文件與 manifest 中。PIM-Taiwan 為 CC BY-NC 4.0，Beers 請依原出版授權使用。本機文獻快取不推送至 GitHub，避免把僅供查閱與允許再散布混為一談。Beers 的 Europe PMC XML 下載失敗仍如實保留在 literature manifest；成功取得的 PDF 另列在 extra manifest。健保署主站附件下載被拒，使用官方開放資料 CSV；版本以實際快照與 SHA-256 為準，不能聲稱是每天即時更新。

## GitHub 與新裝置

GitHub 納入 `public_reference/public-catalog.zip`：只含白名單中的 TFDA CSV、健保 CSV 與來源 manifest，兩目錄均由政府資料開放授權條款第1版提供（https://data.gov.tw/license）。沒有個案資料。原始官方欄位保持完整，只有匯入 SQLite 時移除重複項並建立索引，沒有改寫官方來源。其餘來源文章檔案留在本機。

新裝置執行 `python import_public_data.py --from-bundle` 即可離線重建索引；更新公開目錄則明確執行 `python import_public_data.py --download`。文獻快照可執行 `python fetch_references.py` 與 `python fetch_extra_references.py` 重新下載；失敗會留在 manifest，不視為成功。STOPP/START 出版社附件可能無法下載，已由 Europe PMC supplementaryFiles 取得，現有本機 PDF 可直接閱讀。此一步驟不會啟用任何新臨床規則。

## 辨識範圍

索引 291,408 筆目錄紀錄、1,218,827 筆別名鍵，這不是現行有效藥品數：包含已註銷及歷史給付紀錄。以完整品名、許可證或健保碼精確匹配；只有少量人工維護的品牌縮寫。縮寫、部分名及 OCR 拼字錯誤只提供候選，仍需人工確認。同名成分不同或超過 100 筆匹配會標為 ambiguous，絕不挑第一筆。多個成分保留，不以第一個成分取代複方。

鹽類與劑量的成分標準化只對五個原有成分明確列舉，其餘保留官方原文；未知鹽類、不同資料源寫法可能使同名品項要求人工釐清，屬保守處理。商品劑型、規格及歷史狀態在結果詳細資料顯示，不自動宣稱仍在市售或給付。API 的官方目錄尚未接到獨立開啟的舊 `index.html` 字典。

藥品目錄匯入不等於臨床規則完整。Beers、STOPP/START、PIM-Taiwan 須逐條結構化、保留條件與例外、經臨床驗證後才能啟用。目前檢驗與診斷仍不參與條件式評估，複方也尚未逐成分執行完整規則。
