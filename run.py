from app import create_app

app = create_app()

# 콜드 스타트 시 테이블이 없으면 생성하고, 데이터가 비어있으면 데모 데이터를 채운다.
# (Vercel 서버리스는 별도 마이그레이션 단계가 없으므로 매 콜드 스타트마다 안전하게 확인한다.
#  이미 데이터가 있으면 아무 것도 하지 않는다 — 운영 중 쌓인 신청/변경 내역을 보존.)
with app.app_context():
    from app.extensions import db
    from app.models import Company
    from app.seed_data import populate

    db.create_all()
    if Company.query.first() is None:
        populate()
        db.session.commit()

if __name__ == "__main__":
    app.run(debug=True)
