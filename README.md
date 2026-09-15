# LifeFlow — 이트너스 개인 맞춤형 Shared Service 플랫폼

작업지시서 기준 **Phase 1~4**(프로토타입 분석, Backend 기반, 개인화 Rule Engine, 서비스 신청 플로우)까지 구현되어 있습니다. 관리자 서비스/사용자/Rule 관리 CRUD, 통계 Dashboard, Audit Log, Docker 배포는 Phase 5~6에서 이어서 진행합니다.

## 실행 방법

```bash
pip install -r requirements.txt
python seed.py        # 샘플 데이터 적재 (SQLite, lifeflow.db 생성)
python run.py          # http://127.0.0.1:5000
```

### 데모 계정
| 사번 | 비밀번호 | 특징 |
| --- | --- | --- |
| 11111 | 0000 | 홍길동, 근속 7년+ (장기근속 포상 대상) |
| 22222 | 0000 | 김신입, 입사 1년 미만 (신입사원 지원 대상) |
| 33333 | 0000 | 이단단, 팀장 (리더십 교육 대상) |
| 44444 | 0000 | 박지원, 자녀 등록 (자녀 교육지원 대상) |
| 55555 | 0000 | 관리자 (`/admin/applications`에서 신청 승인/반려) |

## 구조
- `app/models` — companies/departments/users/employee_family/service_categories/services/service_rules/service_applications/notifications + attachments/status_history/inquiries (작업지시서 22번 섹션 + 확장)
- `app/services/personalization.py` — 사용자 인사정보 → 개인화 context 변환, 카테고리 다양화 추천
- `app/services/service_rule_engine.py` — `service_rules` 평가 및 7단계 상태(AVAILABLE/APPLY_AVAILABLE/APPLIED/IN_PROGRESS/NOT_AVAILABLE/COMPLETED/EXPIRED) 산출
- `app/services/application_service.py` — 신청 생성(단일/배치)/상태 변경/취소/문의응답 + 알림 발송 + 이력 기록
- `app/services/application_filters.py` — 나의 신청내역·관리자 화면 공용 필터(기간/서비스/상태/신청자) + 상태별 건수 집계
- `app/services/file_storage.py` — 신청 첨부파일 저장(`uploads/<application_id>/`)
- `app/routes/api.py` — 작업지시서 25~26번 섹션 REST 계약(`/api/me`, `/api/services`, `/api/services/<id>/apply`, `/api/me/personalized-services` 등)
- `app/templates` — 프로토타입(`C:\workspace\esrm-lifeflow`)의 색상 토큰/카드형 UI/헤더 레이아웃을 계승한 서버 렌더링 화면

## 추가 기능 (신청 플로우 고도화)
- 서비스 목록에서 체크박스로 다중 선택 → `/services/review-apply`에서 서비스별 서류 첨부/긴급 신청(연·월·일 분리 입력 + 달력 선택, 유효성 검증)을 받아 일괄 신청
- 서비스별 `required_documents`에 따라 필요 서류 첨부 입력란 자동 생성 (`sample_documents/` 폴더에 업로드 테스트용 더미 파일 제공)
- 신청 상태별 색상 배지, 상단 상태별 건수 버튼(클릭 시 필터링), 기간/서비스/상태(관리자는 신청자 검색까지) 필터
- 나의 신청내역/관리자 화면에서 각 신청을 펼쳐 처리 이력·첨부파일·문의 및 답변을 확인
- 신청 취소 시 사유 입력 필수, 레코드는 삭제하지 않고 `CANCELLED` 상태로 보존
- 알림은 벨 아이콘을 눌러 여닫는 드롭다운 팝업으로 확인(전체 보기는 `/notifications`)
- 관리자 화면에서 긴급 신청 건은 ❗로 강조 표시, 상태 변경 select는 한글 라벨 사용
- 직급(사원/대리 전용, 차장/부장 전용 등) 조건에 따라 이용 불가 서비스는 목록/대시보드 어디서도 노출되지 않음

## 테스트

```bash
pytest tests/
```

Rule Engine(근속/자녀/직책 조건), 신청→승인 플로우(알림 생성 포함), 다중 선택 배치 신청/첨부파일/긴급신청, 취소 사유 보존, 문의·답변, 필터를 검증합니다(총 24건).

## 운영 전환 시
`DATABASE_URL` 환경변수에 PostgreSQL 연결 문자열을 지정하면 SQLAlchemy가 자동으로 사용합니다(예: `postgresql://user:pw@host:5432/lifeflow`). `SECRET_KEY` 환경변수도 운영 환경에서는 반드시 별도 값으로 설정하세요.
