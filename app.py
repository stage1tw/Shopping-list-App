import html
from pathlib import Path

import streamlit as st

from storage import MAX_NAME, MAX_QTY, find_item, load_items, new_item, update_items

CSS_FILE = Path(__file__).parent / "style.css"
# 이름 표시 시 마크다운 서식·자동 링크로 해석되지 않도록 문자 참조로 바꿀 문자
MD_SPECIAL = set("\\`*_{}[]()#+-.!|~<>:@")


# ---------- 헬퍼 ----------

def validate_name(raw):
    """앞뒤 공백을 지우고 검증한다. (이름, 오류 메시지 또는 None)을 돌려준다."""
    name = raw.strip()
    if not name:
        return name, "아이템 이름을 입력해주세요."
    if len(name) > MAX_NAME:
        return name, f"이름은 {MAX_NAME}자까지 입력할 수 있어요. (현재 {len(name)}자)"
    return name, None


def escape_name(text):
    """이름을 HTML·마크다운 안에서 글자 그대로 보이게 바꾼다."""
    return "".join(
        f"&#{ord(c)};" if c in MD_SPECIAL else c for c in html.escape(text, quote=False)
    )


def notify(message):
    """다음 렌더링 때 띄울 토스트 메시지를 예약한다."""
    st.session_state.toast = message


def init_state():
    """화면 상태를 초기화한다. 아이템 목록은 세션이 아니라 파일이 기준이다."""
    defaults = {
        "editing_id": None,
        "edit_error": None,
        "add_error": None,
        "confirm_clear": False,
        "toast": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


# ---------- 콜백 ----------

def add_item():
    """추가 폼 제출 시 아이템을 추가한다. 오류가 있으면 입력값을 그대로 둔다."""
    name, error = validate_name(st.session_state.new_name)
    st.session_state.add_error = error
    if error:
        return
    quantity = int(st.session_state.new_qty)
    update_items(lambda items: items.append(new_item(name, quantity)))
    st.session_state.new_name = ""
    st.session_state.new_qty = 1
    notify(f"'{escape_name(name)}' 추가됨")


def toggle_item(item_id):
    """체크박스 상태를 아이템에 반영한다."""
    checked = st.session_state[f"chk_{item_id}"]

    def change(items):
        item = find_item(items, item_id)
        if item:
            item["checked"] = checked

    update_items(change)


def delete_item(item_id):
    """아이템 하나를 삭제한다."""
    def change(items):
        item = find_item(items, item_id)
        if item:
            items.remove(item)
        return item

    item = update_items(change)
    if st.session_state.editing_id == item_id:
        cancel_edit()
    if item:
        notify(f"'{escape_name(item['name'])}' 삭제됨")


def start_edit(item_id):
    """수정 모드로 전환한다. 이전 입력값이 남지 않게 수정용 위젯 상태를 지운다."""
    for key in (f"edit_name_{item_id}", f"edit_qty_{item_id}"):
        st.session_state.pop(key, None)
    st.session_state.editing_id = item_id
    st.session_state.edit_error = None


def save_edit(item_id):
    """수정 내용을 검증 후 저장한다. 오류가 있으면 수정 모드를 유지한다."""
    name, error = validate_name(st.session_state[f"edit_name_{item_id}"])
    if error:
        st.session_state.edit_error = error
        return
    quantity = int(st.session_state[f"edit_qty_{item_id}"])

    def change(items):
        item = find_item(items, item_id)
        if item:
            item.update(name=name, quantity=quantity)

    update_items(change)
    cancel_edit()


def cancel_edit():
    """수정 모드를 종료한다."""
    st.session_state.editing_id = None
    st.session_state.edit_error = None


def delete_checked():
    """완료된 아이템을 모두 삭제한다."""
    def change(items):
        before = len(items)
        items[:] = [i for i in items if not i["checked"]]
        return before - len(items)

    notify(f"완료 항목 {update_items(change)}개 삭제됨")


def clear_all():
    """전체 아이템을 삭제한다."""
    update_items(lambda items: items.clear())
    st.session_state.confirm_clear = False
    cancel_edit()
    notify("전체 삭제됨")


def set_confirm_clear(value):
    """전체 삭제 확인 단계를 켜거나 끈다."""
    st.session_state.confirm_clear = value


# ---------- 화면 ----------

def render_progress(items):
    """완료 개수와 진행 바를 표시한다."""
    total = len(items)
    done = sum(i["checked"] for i in items)
    st.caption(f"{total}개 중 {done}개 완료")
    st.progress(done / total if total else 0.0)


def render_add_form():
    """[이름 | 수량 | 추가] 한 줄 폼 (Enter로도 제출, 성공 시 입력창 초기화)."""
    with st.form("add_form", border=False):
        col_name, col_qty, col_btn = st.columns([5, 2, 2], vertical_alignment="bottom")
        col_name.text_input(
            "아이템 이름", placeholder="예: 우유", key="new_name", label_visibility="collapsed"
        )
        col_qty.number_input(
            "수량", min_value=1, max_value=MAX_QTY, step=1,  # 기본값은 min_value(1)
            key="new_qty", label_visibility="collapsed",
        )
        col_btn.form_submit_button(
            "추가", on_click=add_item, type="primary", use_container_width=True
        )
    if st.session_state.add_error:
        st.warning(st.session_state.add_error)
        st.session_state.add_error = None


def render_edit_row(item):
    """수정 중인 아이템 행. 테두리로 다른 행과 구분한다."""
    item_id = item["id"]
    with st.container(border=True):
        col_name, col_qty = st.columns([3, 1])
        col_name.text_input("이름", value=item["name"], key=f"edit_name_{item_id}")
        col_qty.number_input(
            "수량", min_value=1, max_value=MAX_QTY, value=item["quantity"], step=1,
            key=f"edit_qty_{item_id}",
        )
        if st.session_state.edit_error:
            st.warning(st.session_state.edit_error)
        col_save, col_cancel = st.columns(2)
        col_save.button(
            "저장", key=f"save_{item_id}", on_click=save_edit, args=(item_id,),
            type="primary", use_container_width=True,
        )
        col_cancel.button(
            "취소", key=f"cancel_{item_id}", on_click=cancel_edit, use_container_width=True
        )


def render_item_row(item, editing_other):
    """일반 아이템 행: 체크박스 | 이름·수량 | 수정 | 삭제."""
    item_id = item["id"]
    # 다른 탭에서 바뀐 체크 상태도 반영되도록 매번 파일 값으로 맞춘다
    st.session_state[f"chk_{item_id}"] = item["checked"]
    with st.container(key=f"row-{item_id}"):
        col_chk, col_name, col_edit, col_del = st.columns(
            [1, 6, 1, 1], gap="small", vertical_alignment="center"
        )
        col_chk.checkbox(
            "완료", key=f"chk_{item_id}", on_change=toggle_item, args=(item_id,),
            label_visibility="collapsed",
        )
        done = " item-done" if item["checked"] else ""
        col_name.markdown(
            f'<div class="item-line{done}">'
            f'<span class="item-name">{escape_name(item["name"])}</span>'
            f'<span class="item-qty">x{item["quantity"]}</span></div>',
            unsafe_allow_html=True,
        )
        # 다른 아이템을 수정 중이면 입력 내용이 사라지지 않게 수정 버튼을 막는다
        col_edit.button(
            "✏️", key=f"edit_{item_id}", on_click=start_edit, args=(item_id,),
            type="tertiary", help="수정", disabled=editing_other,
        )
        col_del.button(
            "🗑️", key=f"del_{item_id}", on_click=delete_item, args=(item_id,),
            type="tertiary", help="삭제",
        )


def render_list(items):
    """미완료 → 완료 순으로 목록을 표시한다 (그룹 내에서는 추가 순서 유지)."""
    editing_id = st.session_state.editing_id
    if editing_id and not find_item(items, editing_id):
        cancel_edit()  # 수정 중이던 아이템이 다른 곳에서 삭제됨
        editing_id = None
    if not items:
        st.info("아직 아이템이 없어요. 위에서 추가해보세요!")
        return
    for item in sorted(items, key=lambda i: i["checked"]):
        if item["id"] == editing_id:
            render_edit_row(item)
        else:
            render_item_row(item, editing_other=editing_id is not None)


def render_bulk_actions(items):
    """완료 항목 일괄 삭제와 전체 삭제(확인 단계 포함)."""
    if not items:
        st.session_state.confirm_clear = False
        return
    st.write("")
    if not st.session_state.confirm_clear:
        col_checked, col_all = st.columns(2)
        col_checked.button(
            "완료 항목 삭제", on_click=delete_checked, use_container_width=True,
            disabled=not any(i["checked"] for i in items),
        )
        col_all.button(
            "전체 삭제", on_click=set_confirm_clear, args=(True,), use_container_width=True
        )
    else:
        st.warning("모든 아이템을 삭제할까요?")
        col_yes, col_no = st.columns(2)
        col_yes.button("삭제", on_click=clear_all, type="primary", use_container_width=True)
        col_no.button(
            "취소", key="cancel_clear", on_click=set_confirm_clear, args=(False,),
            use_container_width=True,
        )


st.set_page_config(page_title="쇼핑 리스트", page_icon="🛒")
st.markdown(f"<style>{CSS_FILE.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
init_state()
items = load_items()  # 매 실행마다 파일에서 읽어 다른 탭·사용자의 변경을 반영

if st.session_state.toast:
    st.toast(st.session_state.toast)
    st.session_state.toast = None

st.title("🛒 쇼핑 리스트")
render_progress(items)
render_add_form()
render_list(items)
render_bulk_actions(items)
