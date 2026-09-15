"""샘플 데이터 적재 스크립트 (로컬 개발용).

사용법: python seed.py
기존 테이블을 모두 지우고 다시 생성한 뒤 데모 데이터를 넣는다.
운영(Vercel+Supabase) 환경은 app/__init__.py의 자동 시딩(비어있을 때만 채움)을 사용한다.
"""

from app import create_app
from app.extensions import db
from app.seed_data import populate


def run():
    app = create_app()
    with app.app_context():
        db.drop_all()
        db.create_all()
        populate()
        db.session.commit()
        print("샘플 데이터 적재 완료")
        print("데모 계정:")
        print("  홍길동(5년+ 근속) 11111 / 0000")
        print("  김신입(신입) 22222 / 0000")
        print("  이단단(팀장) 33333 / 0000")
        print("  박지원(자녀등록) 44444 / 0000")
        print("  관리자 55555 / 0000")


if __name__ == "__main__":
    run()
