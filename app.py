from pathlib import Path

import streamlit as st

import logic
import storage

st.set_page_config(page_title="쇼핑리스트", page_icon="🛒", layout="centered")

st.session_state.setdefault("editing_id", None)  # 수정 중인 항목 id
st.session_state.setdefault("flash", None)  # {"where": "add" | 항목 id, "msg": str}

# 목록은 세션에 복사해 두지 않고 매 실행마다 파일에서 읽는다.
# (세션별 사본을 들고 있다가 저장하면 다른 탭/방문자의 변경을 덮어쓰게 된다)
items: list[storage.Item] = storage.load_items()


# 범위를 벗어난 수량은 Streamlit이 서버로 보내지 않아 앱에서 경고할 수 없으므로 범위를 미리 알려준다
QTY_HELP = f"{logic.MIN_QTY}~{logic.MAX_QTY} 사이의 정수를 입력하세요. 범위를 벗어난 값은 무시됩니다."


def load_css() -> None:
    css = (Path(__file__).parent / "style.css").read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


# ---------- 콜백: 상태 변경 -> 저장 (콜백 뒤에 Streamlit이 자동으로 재실행한다) ----------
def run(fn, where: str = "add") -> bool:
    """storage.mutate로 변경을 적용한다. 검증 오류(문자열)가 있으면 발생 위치와 함께 남기고 False를 반환한다."""
    result = storage.mutate(fn)
    error = result if isinstance(result, str) else None
    st.session_state["flash"] = {"where": where, "msg": error} if error else None
    return error is None


def on_add() -> None:
    name, qty = st.session_state["new_name"], st.session_state["new_qty"]
    run(lambda items: logic.add_item(items, name, qty), "add")


def on_toggle(item_id: str) -> None:
    checked = st.session_state[f"chk_{item_id}"]
    run(lambda items: logic.toggle_item(items, item_id, checked))


def on_delete(item_id: str) -> None:
    if st.session_state["editing_id"] == item_id:
        st.session_state["editing_id"] = None
    run(lambda items: logic.delete_item(items, item_id))


def on_edit_start(item_id: str) -> None:
    # 편집 입력창의 초기값은 렌더링할 때 value=로 채운다 (필터 등으로 잠시 사라져도 복구되도록)
    st.session_state["editing_id"] = item_id
    st.session_state["flash"] = None


def on_edit_save(item_id: str) -> None:
    name = st.session_state[f"edit_name_{item_id}"]
    qty = st.session_state[f"edit_qty_{item_id}"]
    if run(lambda items: logic.update_item(items, item_id, name, qty), item_id):
        st.session_state["editing_id"] = None


def on_edit_cancel() -> None:
    st.session_state["editing_id"] = None
    st.session_state["flash"] = None


def on_clear_checked() -> None:
    run(lambda items: logic.clear_checked(items))


def show_flash(where: str) -> None:
    """오류 안내는 발생한 위치(추가 폼 또는 해당 행)에서만 보여준다."""
    flash = st.session_state["flash"]
    if flash and flash["where"] == where:
        st.warning(flash["msg"], icon="⚠️")


# ---------- 화면 ----------
load_css()
st.title("🛒 쇼핑리스트")

# F-07 진행 현황
done, total = logic.progress(items)
st.markdown(
    f'<div class="summary"><span class="summary-num">{done} / {total}</span> 완료</div>',
    unsafe_allow_html=True,
)
st.progress(done / total if total else 0.0)

# F-01 추가 폼 (Enter로도 제출)
with st.container(key="add_card"):  # 카드 스타일용 래퍼 (st.form은 key 클래스를 붙이지 않는다)
    with st.form("add_form", clear_on_submit=True, border=False):
        col_name, col_qty, col_btn = st.columns([5, 2.3, 2.2], vertical_alignment="bottom")
        col_name.text_input(
            "아이템 이름", key="new_name", max_chars=logic.MAX_NAME_LEN, placeholder="예: 우유"
        )
        col_qty.number_input(
            "수량", key="new_qty", min_value=logic.MIN_QTY, max_value=logic.MAX_QTY,
            value=1, step=1, help=QTY_HELP,
        )
        col_btn.form_submit_button(
            "추가", on_click=on_add, type="primary", use_container_width=True
        )
        show_flash("add")

# F-08 보기 전환
view = st.segmented_control(
    "보기", logic.FILTERS, default=logic.FILTERS[0], key="view", label_visibility="collapsed"
) or logic.FILTERS[0]  # 같은 버튼을 다시 눌러 선택이 해제되면 "전체"로 되돌린다

# 목록
shown = logic.visible_items(items, view)
if not items:
    st.markdown(
        '<div class="empty-state"><div class="icon">🛒</div>'
        "아직 항목이 없어요.<br>첫 아이템을 추가해보세요!</div>",
        unsafe_allow_html=True,
    )
elif not shown:
    st.markdown(
        f'<div class="empty-state"><div class="icon">🔍</div>\'{view}\' 항목이 없어요.</div>',
        unsafe_allow_html=True,
    )

for item in shown:
    editing = st.session_state["editing_id"] == item.id
    # key 접두사로 상태를 구분해 style.css에서 스타일을 지정한다
    row_key = f"rowedit_{item.id}" if editing else (
        f"rowdone_{item.id}" if item.checked else f"row_{item.id}"
    )
    with st.container(key=row_key):
        if editing:
            # F-02 인라인 수정
            c_name, c_qty = st.columns([5, 2.3])
            c_name.text_input(
                "이름", value=item.name, key=f"edit_name_{item.id}", max_chars=logic.MAX_NAME_LEN
            )
            c_qty.number_input(
                "수량",
                value=item.quantity,
                key=f"edit_qty_{item.id}",
                min_value=logic.MIN_QTY,
                max_value=logic.MAX_QTY,
                step=1,
                help=QTY_HELP,
            )
            show_flash(item.id)
            c_save, c_cancel = st.columns(2)
            c_save.button("저장", key=f"save_{item.id}", on_click=on_edit_save,
                          args=(item.id,), type="primary", use_container_width=True)
            c_cancel.button("취소", key=f"cancel_{item.id}", on_click=on_edit_cancel,
                            use_container_width=True)
        else:
            c_chk, c_qty, c_edit, c_del = st.columns(
                [6, 1.6, 1, 1], vertical_alignment="center"
            )
            safe_name = logic.md_escape(item.name)
            # 다른 탭/방문자가 바꾼 체크 상태가 있어도 파일 기준으로 맞춘다
            st.session_state[f"chk_{item.id}"] = item.checked
            # F-04 체크: 체크되면 취소선
            c_chk.checkbox(
                f"~~{safe_name}~~" if item.checked else safe_name,
                key=f"chk_{item.id}",
                on_change=on_toggle,
                args=(item.id,),
            )
            c_qty.markdown(f'<span class="qty-badge">x{item.quantity}</span>',
                           unsafe_allow_html=True)
            c_edit.button("✏️", key=f"edit_{item.id}", on_click=on_edit_start,
                          args=(item.id,), help="수정")
            c_del.button("🗑️", key=f"del_{item.id}", on_click=on_delete,
                         args=(item.id,), help="삭제")

# F-06 체크된 항목 일괄 삭제
if items:
    with st.container(key="clear_wrap"):
        st.button(
            "체크된 항목 모두 삭제",
            on_click=on_clear_checked,
            disabled=done == 0,
            use_container_width=True,
        )
