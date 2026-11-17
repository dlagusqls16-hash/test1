"""쇼핑리스트 비즈니스 로직. Streamlit에 의존하지 않아 단독으로 테스트할 수 있다.

변경 함수는 items 리스트를 직접 수정하고, 입력 검증이 필요한 함수는
오류 메시지(문자열)를 반환한다. 성공하면 None을 반환한다.
"""
import re

from storage import Item

MAX_NAME_LEN = 50
MIN_QTY = 1
MAX_QTY = 999

FILTERS = ("전체", "미완료", "완료")


def validate(name: str, quantity: int) -> str | None:
    """이름/수량 검증. 문제가 있으면 안내 메시지를, 없으면 None을 반환한다."""
    if not name.strip():
        return "아이템 이름을 입력해주세요."
    if len(name.strip()) > MAX_NAME_LEN:
        return f"이름은 {MAX_NAME_LEN}자 이하로 입력해주세요."
    if not (MIN_QTY <= quantity <= MAX_QTY):
        return f"수량은 {MIN_QTY}~{MAX_QTY} 사이로 입력해주세요."
    return None


def add_item(items: list[Item], name: str, quantity: int) -> str | None:
    error = validate(name, quantity)
    if error:
        return error
    items.append(Item(name=name.strip(), quantity=int(quantity)))
    return None


def update_item(items: list[Item], item_id: str, name: str, quantity: int) -> str | None:
    error = validate(name, quantity)
    if error:
        return error
    for item in items:
        if item.id == item_id:
            item.name = name.strip()
            item.quantity = int(quantity)
            return None
    return "수정할 항목을 찾을 수 없어요."


def delete_item(items: list[Item], item_id: str) -> None:
    items[:] = [item for item in items if item.id != item_id]


def toggle_item(items: list[Item], item_id: str, checked: bool) -> None:
    for item in items:
        if item.id == item_id:
            item.checked = checked
            return


def clear_checked(items: list[Item]) -> int:
    """체크된 항목을 모두 삭제하고 삭제한 개수를 반환한다."""
    before = len(items)
    items[:] = [item for item in items if not item.checked]
    return before - len(items)


def progress(items: list[Item]) -> tuple[int, int]:
    """(완료 개수, 전체 개수)."""
    return sum(item.checked for item in items), len(items)


def visible_items(items: list[Item], view: str) -> list[Item]:
    """필터를 적용하고, 체크된 항목을 하단으로 정렬한다(등록 순서는 유지)."""
    if view == "미완료":
        items = [i for i in items if not i.checked]
    elif view == "완료":
        items = [i for i in items if i.checked]
    return sorted(items, key=lambda i: i.checked)


def md_escape(text: str) -> str:
    """사용자 입력이 마크다운/LaTeX/이모지 코드로 해석되지 않도록 이스케이프한다."""
    return re.sub(r"([\\`*_{}\[\]()#+\-.!~$:<>|&])", r"\\\1", text)
