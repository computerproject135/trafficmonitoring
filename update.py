import os
import json
import requests
import base64
from datetime import datetime

# ---------------------------
# 設定本地檔案路徑
LOCAL_JSON = r"data/road_data.json"
LOCAL_JSON_RAW = r"data/road_data_raw.json"

# 從環境變數讀 GitHub Token（不要直接寫在程式裡）
GITHUB_TOKEN = os.getenv("GH_TOKEN")  

# Repo 與 JSON 路徑
GITHUB_REPO = "computerproject135/trafficmonitoring"
GITHUB_JSON_PATH = "data/road_data.json"
GITHUB_JSON_PATH_RAW = "data/road_data_raw.json"

# 政府資料 URL
DATA_URL = "https://data.moi.gov.tw/MoiOD/System/DownloadFile.aspx?DATA=36384FA8-FACF-432E-BB5B-5F015E7BC1BE"

# ---------------------------
# 下載最新資料
os.makedirs("data", exist_ok=True)
print("正在下載最新資料...")

try:
    res = requests.get(DATA_URL, verify=False)
    res.raise_for_status()
    with open(LOCAL_JSON_RAW, "wb") as f:
        f.write(res.content)
    print("原始資料下載完成:", LOCAL_JSON_RAW)

    with open(LOCAL_JSON_RAW, "r", encoding="utf-8") as f:
        data = json.load(f)

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
    with open(local_path, "r", encoding="utf-8") as f:
        content = f.read()

    url_get = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{github_path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    response = requests.get(url_get, headers=headers)
    sha = response.json().get("sha") if response.status_code == 200 else None

    url_put = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{github_path}"
    data_payload = {
        "message": f"Update {os.path.basename(github_path)}",
        "content": base64.b64encode(content.encode()).decode(),
    }
    if sha:
        data_payload["sha"] = sha

    res = requests.put(url_put, headers=headers, json=data_payload)
    if res.status_code in [200, 201]:
        print(f"{os.path.basename(github_path)} 成功推送到 GitHub!")
    else:
        print(f"{os.path.basename(github_path)} 推送失敗:", res.json())

push_to_github(LOCAL_JSON, GITHUB_JSON_PATH)
push_to_github(LOCAL_JSON_RAW, GITHUB_JSON_PATH_RAW)
