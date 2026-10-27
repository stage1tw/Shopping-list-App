# 🛒 쇼핑 리스트

아이템 추가·수정·삭제·체크 기능이 있는 가벼운 쇼핑 리스트 웹 앱입니다. Streamlit으로 만들었습니다.
자세한 요구사항은 [PRD.md](PRD.md)를 참고하세요.

## 로컬 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

브라우저에서 http://localhost:8501 로 접속합니다.

## 데이터 저장

아이템은 `data/shopping_list.json`에 저장됩니다(앱 실행 시 자동 생성).
Streamlit Community Cloud에서는 재시작·재배포 시 이 파일이 초기화될 수 있습니다.
