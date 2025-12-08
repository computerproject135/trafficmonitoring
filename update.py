import os
import json
import requests
import base64
from datetime import datetime
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# ---------------------------
# 設定檔案路徑與 GitHub 資訊
LOCAL_JSON = "data/road_data.json"
LOCAL_JSON_RAW = "data/road_data_raw.json"
GITHUB_TOKEN = os.getenv("GH_TOKEN")  # GitHub Actions secret
GITHUB_REPO = "computerproject135/trafficmonitoring"
GITHUB_JSON_PATH = "data/road_data.json"
GITHUB_JSON_PATH_RAW = "data/road_data_raw.json"
DATA_URL = "https://data.moi.gov.tw/MoiOD/System/DownloadFile.aspx?DATA=36384FA8-FACF-432E-BB5B-5F015E7BC1BE"

os.makedirs("data", exist_ok=True)

# ---------------------------
# 設置 requests Session，增加重試機制
session = requests.Session()
retry_strategy = Retry(
    total=5,  # 最大重試次數
    backoff_factor=2,  # 失敗後等待時間指數退避
    status_forcelist=[429, 500, 502, 503, 504],  # 適用於重試的 HTTP 狀態碼
    allowed_methods=["HEAD", "GET", "OPTIONS"]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)
session.mount("http://", adapter)

# ---------------------------
# 下載最新資料
try:
    res = session.get(DATA_URL, timeout=(10, 60), verify=False)  # 連線10秒，讀取60秒
    res.raise_for_status()
    new_content_raw = res.content

    # 寫入原始 JSON
    with open(LOCAL_JSON_RAW, "wb") as f:
        f.write(new_content_raw)
    print("原始資料已更新:", LOCAL_JSON_RAW)

    # 處理 JSON 並加入更新時間
    data = json.loads(new_content_raw)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(data, list):
        data_with_time = {"_last_update": timestamp, "data": data}
    elif isinstance(data, dict):
        data_with_time = data.copy()
        data_with_time["_last_update"] = timestamp
    else:
        raise ValueError("未知 JSON 類型")

    with open(LOCAL_JSON, "w", encoding="utf-8") as f:
        json.dump(data_with_time, f, ensure_ascii=False, indent=2)
    print("已加入最後更新時間:", timestamp)

except Exception as e:
    print("資料下載或處理失敗:", e)
    exit()

# ---------------------------
# 推送到 GitHub
def push_to_github(local_path, github_path):
    if not GITHUB_TOKEN:
        print("GH_TOKEN 未設定，無法推送")
        return

    with open(local_path, "r", encoding="utf-8") as f:
        content = f.read()

    url_get = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{github_path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}

    try:
        response = requests.get(url_get, headers=headers)
        sha = response.json().get("sha") if response.status_code == 200 else None
    except Exception as e:
        print(f"取得 {github_path} SHA 失敗:", e)
        sha = None

    url_put = url_get
    data_payload = {
        "message": f"Update {os.path.basename(github_path)}",
        "content": base64.b64encode(content.encode()).decode(),
    }
    if sha:
        data_payload["sha"] = sha

    try:
        res = requests.put(url_put, headers=headers, json=data_payload)
        if res.status_code in [200, 201]:
            print(f"{os.path.basename(github_path)} 成功推送到 GitHub!")
        else:
            print(f"{os.path.basename(github_path)} 推送失敗:", res.json())
    except Exception as e:
        print(f"{os.path.basename(github_path)} 推送失敗:", e)

# ---------------------------
# 強制推送每個 JSON 檔案
push_to_github(LOCAL_JSON, GITHUB_JSON_PATH)
push_to_github(LOCAL_JSON_RAW, GITHUB_JSON_PATH_RAW)
