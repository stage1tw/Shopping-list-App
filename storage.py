"""쇼핑 리스트 데이터 저장소. 저장 방식을 바꿀 때는 이 파일만 고치면 된다."""
import json
import os
import threading
import uuid
from datetime import datetime
from pathlib import Path

import streamlit as st

DATA_DIR = Path(__file__).parent / "data"
DATA_FILE = DATA_DIR / "shopping_list.json"
MAX_NAME = 50
MAX_QTY = 99


@st.cache_resource
def file_lock():
    """모든 세션이 공유하는 잠금. 동시에 읽고-쓰기 하다 덮어쓰는 것을 막는다."""
    return threading.Lock()


def clean_item(raw, index):
    """파일에서 읽은 아이템을 검증·정리한다. 쓸 수 없는 항목이면 None."""
    if not isinstance(raw, dict) or not isinstance(raw.get("name"), str):
        return None
    name = raw["name"].strip()[:MAX_NAME]
    if not name:
        return None
    try:
        quantity = min(max(int(raw.get("quantity", 1)), 1), MAX_QTY)
    except (TypeError, ValueError):
        quantity = 1
    return {
        # id가 없으면 실행할 때마다 같은 값이 나오도록 위치·이름으로 만든다
        "id": str(raw.get("id") or uuid.uuid5(uuid.NAMESPACE_OID, f"{index}:{name}")),
        "name": name,
        "quantity": quantity,
        "checked": bool(raw.get("checked", False)),
        "created_at": str(raw.get("created_at", "")),
    }


def load_items():
    """JSON 파일에서 아이템 목록을 불러온다. 파일이 없거나 깨진 항목은 건너뛴다."""
    try:
        raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError, OSError):
        return []
    if not isinstance(raw, list):
        return []
    items, seen = [], set()
    for index, entry in enumerate(raw):
        item = clean_item(entry, index)
        if item and item["id"] not in seen:
            seen.add(item["id"])
            items.append(item)
    return items


def save_items(items):
    """임시 파일에 쓴 뒤 교체한다. 저장 도중 중단돼도 기존 파일이 깨지지 않는다."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = DATA_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, DATA_FILE)


def update_items(change):
    """파일의 최신 목록에 change(items)를 적용해 저장하고, change의 반환값을 돌려준다."""
    with file_lock():
        items = load_items()
        result = change(items)
        save_items(items)
    return result


def new_item(name, quantity=1):
    """새 아이템 딕셔너리를 만든다."""
    return {
        "id": str(uuid.uuid4()),
        "name": name,
        "quantity": quantity,
        "checked": False,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }


def find_item(items, item_id):
    """id로 아이템을 찾는다. 없으면 None."""
    return next((i for i in items if i["id"] == item_id), None)
