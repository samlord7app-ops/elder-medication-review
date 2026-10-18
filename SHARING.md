# 雲端入口與本機服務

雲端入口只發布 `cloud-ui/`。圖片、Excel、OCR、核對、臨床篩檢及結果全部在使用者電腦的 http://127.0.0.1:18743/ 完成。雲端頁面用新分頁開啟本機工作台，沒有跨站 API、iframe、病人輸入欄位、分析追蹤或個案回傳。GitHub 存放程式與公開目錄，不提供臨床比對 API。新增的選用雲端藥名功能由本機服務在人工確認後連至 NLM RxNav；只送藥名，不送臨床內容。

## 給使用者

1. 從 GitHub Releases 下載 `ElderMedicationReview-Windows-x64.zip` 及 `SHA256SUMS.txt`。可執行 `Get-FileHash .\ElderMedicationReview-Windows-x64.zip -Algorithm SHA256` 比對雜湊。
2. 解壓縮整個資料夾至有寫入權限、非 OneDrive 等同步目錄的位置，不可直接在 ZIP 裡執行。適用 Windows 10/11 x64；無須另裝 Python。套件尚無程式碼簽章，系統可能顯示發行者未驗證，機構可先審查原始碼及建置流程。
3. 執行 `ElderMedicationReview.exe`。首次啟動建立本機藥品索引需要數分鐘，完成後自動開啟本機頁面。若 18743 連接埠被占用，先確認既有服務；勿停用不明程式。
4. 文獻全文不隨包散布。在本機工作台按公開資料檢核，勾選需要的文獻並確認更新；只有公開參考網址會連網。下載失敗或來源雜湊與規則包不符時，相關臨床規則保持停用，請查閱來源狀態。切勿把「已辨識」視為安全。
5. Windows OCR 需要對應的本機語言辨識元件；辨識結果須人工確認。沒有 OCR 元件時仍可手動輸入或匯入 Excel。
6. 服務視窗須保持開啟；關閉視窗或 Ctrl+C 結束服務。每個人各自在自己的電腦執行，並不共享案件或統計。

目前引擎只有 90 個條件分支，非完整準則，也未經機構臨床驗證。整合工作台可在評估後確認保存至此瀏覽器，並依日期、藥品、類別及覆核狀態匯出明細、統計與藥品不適切性分析表 CSV。備份 JSON 可合併還原及匯入舊版備份；同一網址、同一瀏覽器的紀錄可延續使用。紀錄不含圖片、Excel、原文、診斷或檢驗明細，仍屬敏感健康資訊；請定期備份，不使用共用帳號或無痕視窗。歷史規則快照不隨更新改寫。沒有跨人員共用資料庫。正式共同紀錄及評鑑統計需要另設院內資料庫與存取權限。

## 維護者部署

- GitHub 儲存庫 Settings → Pages → Build and deployment 的 Source 選 **GitHub Actions**。推送 cloud-ui 變更後，`Deploy cloud entry` 工作流程會僅上傳該資料夾。實際網址以工作流程的 github-pages 部署結果為準。
- 在 Actions 執行 `Build Windows local service` 可取得需登入 GitHub 的建置 artifact。要提供 Releases 下載，推送 `local-v` 開頭的版本標籤，例如 `local-v2026.10.18.1`；測試與建置成功才會發布 ZIP 和 SHA256SUMS。
- 套件採明確檔案清單：只含程式、UI、公開藥品目錄、來源清單與執行依賴。不得加入文獻全文、病例、暫存圖片、Excel、SQLite、個案匯出或已不參考資料夾。
- 公開／私人儲存庫的頁面與 Release 可用性取決於 GitHub 方案與存取設定；不要為了分享而把任何個案檔案提交 Git。
- Windows exe 由 GitHub Actions 的乾淨環境建置，無需在臨床工作站安裝建置工具。套件目前未簽章，正式配發前需由機構驗證與簽章。

## 本機開發

安裝 Python 3.13、openpyxl 3.1.5、pypdf 6.1.1 後執行 `python local_api.py`；手動開啟本機網址。建置另需 PyInstaller 6.16.0，再執行 `python packaging/build_windows.py`。建置輸出均忽略於 Git。
