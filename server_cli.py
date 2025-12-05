import requests
import json, sys, os, time, uuid, random

ENDPOINT = "https://ask-saju-42xetdarfa-uc.a.run.app"

# 기본 세션/이름
USER_NAME  = "홍승창"
SESSION_ID = "single_global_session"   # 필요시 다른 값으로 변경

# 새로운 경로 구조용 (선택사항)
# 앱 UID가 있으면: gs://bucket/users/<앱UID>/profiles/<user_id>.json
# 없으면 기존 방식으로 폴백: gs://bucket/<user_id>.json
# user_id는 make_user_id_from_name(user_name)으로 자동 생성됨
APP_UID = "hsc6320"      # 예: "firebase-auth-uid-123" 또는 None

BASE_PAYLOAD = {
    "name": USER_NAME,
    "question": "",
    "sajuganji": {"년주": "무진", "월주": "기미", "일주": "임신", "시주": "무신"},
    "yearGan" : "무", "yearJi"  : "진",
    "wolGan"  : "계", "wolJi"   : "미",
    "ilGan"   : "임", "ilJi"    : "신",
    "siGan"   : "무", "siJi"    : "신",
    "daewoon": "경신, 신유, 임술, 계해, 갑자, 을축",
    "currentDaewoon": "계해",
    "currDaewoonGan" : "계", "currDaewoonJi" : "해",
    "reset" : "false",
    # 새로운 경로 구조용 (APP_UID가 설정되어 있으면 자동 포함)
    **({"app_uid": APP_UID} if APP_UID else {}),
}

# ---------- 공통 POST: 429/5xx 지수 백오프 ----------
def post_raw(payload: dict, *, max_retries: int = 3, base_sleep: float = 0.8):
    # 매 요청에 세션/이름을 자동 포함 (BASE_PAYLOAD에 이미 app_uid 포함됨)
    payload = {"session_id": SESSION_ID, **payload}
    last_err = None

    for attempt in range(max_retries + 1):
        try:
            r = requests.post(ENDPOINT, json=payload, timeout=60)

            # 429/5xx는 재시도
            if r.status_code == 429 or 500 <= r.status_code < 600:
                if attempt == max_retries:
                    # 마지막 시도면 에러 본문 포함해서 반환
                    return {
                        "_error": True,
                        "status": r.status_code,
                        "headers": dict(r.headers),
                        "text": r.text[:2000],
                    }
                # Retry-After 우선 존중
                retry_after = r.headers.get("Retry-After")
                if retry_after:
                    try:
                        delay = float(retry_after)
                    except ValueError:
                        delay = base_sleep * (2 ** attempt)
                else:
                    delay = base_sleep * (2 ** attempt) + random.uniform(0, 0.3)
                time.sleep(delay)
                continue

            # 그 외 상태코드 처리
            if r.status_code >= 400:
                return {
                    "_error": True,
                    "status": r.status_code,
                    "headers": dict(r.headers),
                    "text": r.text[:2000],
                }

            # 정상 응답
            try:
                return r.json()
            except Exception:
                return {"_raw_text": r.text}

        except requests.RequestException as e:
            last_err = e
            if attempt == max_retries:
                return {"_error": True, "exception": str(e)}
            delay = base_sleep * (2 ** attempt) + random.uniform(0, 0.3)
            time.sleep(delay)

    # 여기 오지 않지만 안전망
    return {"_error": True, "exception": str(last_err) if last_err else "unknown"}

# ---------- 기능 함수들 ----------
# def send_reset_only(val: str | None = None) -> str:
#     """대화방 삭제/초기화 신호만 전송. 기본값 reset='true'."""
#     v = val if val is not None else "true"
#     data = post_raw({"reset": v})
#     return json.dumps(data, ensure_ascii=False, indent=2)

# def delete_conversation() -> str:
#     """가독성 별칭: reset=true"""
#     return send_reset_only("true")

def send_reset_only(val: str | None = None) -> str:
    """
    대화방 삭제/초기화 신호 전송.
    - reset: True (bool)
    - name, app_uid 같이 보내서 저장되는 프로필과 동일한 키로 초기화
    """
    v = val if val is not None else True  # 문자열 대신 bool 권장

    payload = {
        "reset": v,
        "name": USER_NAME,
    }

    # APP_UID가 있으면 같이 전송 (저장도 이 기준으로 되어 있기 때문)
    if APP_UID:
        payload["app_uid"] = APP_UID

    data = post_raw(payload)
    return json.dumps(data, ensure_ascii=False, indent=2)


def delete_conversation() -> str:
    """가독성 별칭: reset=true"""
    return send_reset_only(True)


# def fetch_history_only() -> str:
#     """대화 불러오기 전용: fetch_history=true 만 전송"""
#     data = post_raw({"fetch_history": "true"})
#     if isinstance(data, dict) and "history" in data:
#         return json.dumps(data["history"], ensure_ascii=False, indent=2)
#     return json.dumps(data, ensure_ascii=False, indent=2)

def fetch_history_only() -> str:
    """
    대화 불러오기 전용: fetch_history=true 전송.
    app_uid / name도 같이 보내서 서버가 같은 프로필 JSON을 찾을 수 있게 함.
    """
    payload = {
        "fetch_history": "true",
        "name": USER_NAME,
    }

    # APP_UID가 설정되어 있다면 같이 전송 (저장할 때도 이걸로 경로를 만들기 때문)
    if APP_UID:
        payload["app_uid"] = APP_UID

    data = post_raw(payload)

    if isinstance(data, dict) and "history" in data:
        return json.dumps(data["history"], ensure_ascii=False, indent=2)
    return json.dumps(data, ensure_ascii=False, indent=2)

def ask_server(q: str) -> str:
    """일반 질문: BASE + question (세션/이름은 post_raw에서 자동 포함)"""
    p = dict(BASE_PAYLOAD)
    p["question"] = q
    data = post_raw(p)
    # 서버가 {"answer": "..."} 형태로 준다고 가정
    if isinstance(data, dict) and data.get("_error"):
        # 에러면 상태/본문까지 보여주기
        return json.dumps(data, ensure_ascii=False, indent=2)
    if isinstance(data, dict):
        return data.get("answer") or json.dumps(data, ensure_ascii=False, indent=2)
    return str(data)

# ---------- 메인 ----------
def main():
    print("🗣  사주/점괘 테스트 CLI (종료: Ctrl+C)\n")

    # 시작 시 서버 히스토리 요청(실패해도 계속 진행)
    print("📥 서버에서 이전 대화 불러오는 중...")
    hist = fetch_history_only()
    print(hist)

    while True:
        try:
            q = input("질문> ").strip()
            if not q:
                continue

            # 즉시 초기화 명령
            if q.lower() == "/reset":
                print("🧹 대화방 삭제 요청 중...")
                print(delete_conversation())
                continue

            ans = ask_server(q)
            print("\n--- 응답 ---")
            print(ans)
            print("------------\n")

        except (KeyboardInterrupt, EOFError):
            print("\n종료합니다.")
            sys.exit(0)

if __name__ == "__main__":
    main()
