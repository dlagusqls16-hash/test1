"""데이터 저장/불러오기 모듈.

현재는 로컬 JSON 파일을 사용한다. 나중에 외부 DB로 교체할 수 있도록
load_items / save_items 두 함수만 UI에 노출한다.
"""
import json
import os
import threading
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TypeVar
from uuid import uuid4

T = TypeVar("T")

DATA_PATH = Path(__file__).parent / "data" / "items.json"


@dataclass
class Item:
    """쇼핑리스트 아이템 (PRD 6.1)."""

    name: str
    quantity: int = 1
    checked: bool = False
    id: str = field(default_factory=lambda: uuid4().hex)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


def load_items() -> list[Item]:
    """저장된 아이템을 불러온다. 파일이 없거나 깨져 있으면 빈 리스트를 반환한다."""
    try:
        raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        return [Item(**row) for row in raw]
    except (OSError, ValueError, TypeError):
        return []


def save_items(items: list[Item]) -> None:
    """아이템 목록을 JSON 파일에 저장한다. data/ 폴더가 없으면 만든다.

    임시 파일에 쓴 뒤 교체(os.replace)하므로 쓰는 도중 다른 세션이 읽어도 깨진 파일을 보지 않는다.
    """
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = [asdict(item) for item in items]
    tmp = DATA_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, DATA_PATH)


# 모든 세션(브라우저 탭/방문자)이 같은 프로세스에서 같은 파일을 공유하므로 락으로 직렬화한다.
_lock = threading.Lock()


def mutate(fn: Callable[[list[Item]], T]) -> T:
    """파일에서 최신 목록을 읽고 -> fn으로 수정하고 -> 저장하는 과정을 한 번에 수행한다.

    세션이 들고 있던 오래된 목록으로 파일 전체를 덮어쓰면 다른 탭/방문자의 변경이
    사라지므로, 모든 변경은 반드시 이 함수를 거친다. fn의 반환값을 그대로 돌려준다.
    """
    with _lock:
        items = load_items()
        result = fn(items)
        save_items(items)
        return result
