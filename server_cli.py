import requests
import json, sys, os, time, uuid


ENDPOINT = "https://ask-saju-42xetdarfa-uc.a.run.app"
   
   
# 기본 세션/이름
USER_NAME  = "김지은"
SESSION_ID = "single_global_session"  # 필요시 /session 명령으로 변경 가능
                
BASE_PAYLOAD = {
    "name": USER_NAME,
    "question": "",
    "sajuganji": {"년주": "무진", "월주": "기미", "일주": "임신", "시주": "무신"},
    "yearGan" : "무",
    "yearJi"  : "진", 
    "wolGan"  : "계",
    "wolJi"   : "미",
    "ilGan"   : "임",
    "ilJi"    : "신",
    "siGan"   : "무",
    "siJi"    : "신",
    "daewoon": "경신, 신유, 임술, 계해, 갑자, 을축",
    "currentDaewoon": "계해",
    "currDaewoonGan" : "계",
    "currDaewoonJi" : "해",
    "reset" : "false",
}

def post_raw(payload: dict) -> dict | str:
    try:
        r = requests.post(ENDPOINT, json=payload, timeout=60)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return f"[요청 실패] {e}"
    

def send_reset_only(val: str | None = None) -> str:
    """reset만 전송(대화방 삭제/초기화 신호). 기본값은 true."""
    v = val if val is not None else "true"
    payload = {"reset": "true", "session_id": SESSION_ID, "name": USER_NAME}
    #data = post_raw({"reset": v})
    data = post_raw(payload)
    return json.dumps(data, ensure_ascii=False, indent=2) if isinstance(data, dict) else data

def delete_conversation() -> str:
    """가독성 좋은 별칭: reset=true"""
    return send_reset_only("true")


def fetch_history_only() -> str:
    # ✅ fetch_history만 단독 전송 (이때 세션/이름도 같이)
    payload = {"fetch_history": "true", "session_id": SESSION_ID, "name": USER_NAME}
    data = post_raw(payload)
    # 서버가 {"history":[...]} 형태라면 보기 좋게
    if isinstance(data, dict) and "history" in data:
        return json.dumps(data["history"], ensure_ascii=False, indent=2)
    return json.dumps(data, ensure_ascii=False, indent=2)

def ask_server(q: str) -> str:
    payload = dict(BASE_PAYLOAD)
    payload["question"] = q
    try:
        r = requests.post(ENDPOINT, json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()
        return data.get("answer") or json.dumps(data, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"[요청 실패] {e}"


        
def main():
    print("🗣  사주/점괘 테스트 CLI (종료: Ctrl+C)\n") 
     # 시작 시 최근 히스토리 표시
    print("📥 서버에서 이전 대화 불러오는 중...")
    try:
        hist = fetch_history_only()
        print(hist)        
    except Exception as e:
        print(f"[히스토리 요청 실패] {e}")
        
    while True:
        try:
            q = input("질문> ").strip()
            if not q:
                continue
            
            # 슬래시 명령(옵션): /reset 입력 시 즉시 삭제
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
