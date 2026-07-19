from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

dotenv_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path)

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL is None:
    raise RuntimeError("DATABASE_URL is not set")

# إعداد المحرك مع تحسينات الأداء (صفحة 208 في التوثيق)
if DATABASE_URL.lower().startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_engine(
        DATABASE_URL,
        # زيادة عدد الاتصالات المفتوحة للتعامل مع ضغط الـ AI
        pool_size=20,
        # السماح بزيادة مؤقتة في الاتصالات عند حدوث "انفجار" في التنبيهات
        max_overflow=10,
        # التأكد من أن الاتصال لا يزال حياً قبل استخدامه (يمنع أخطاء الفصل المفاجئ)
        pool_pre_ping=True,
        # إعادة تدوير الاتصالات كل ساعة لمنع الاتصالات "الميتة"
        pool_recycle=3600,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def _ensure_schema_compatibility() -> None:
    """Add missing columns expected by the API when the database schema is older."""
    try:
        with engine.begin() as conn:
            for table in Base.metadata.sorted_tables:
                table_exists = conn.execute(
                    text(f"SELECT to_regclass('public.{table.name}')")
                ).scalar()
                if not table_exists:
                    continue

                existing_columns = {
                    row[0]
                    for row in conn.execute(
                        text("SELECT column_name FROM information_schema.columns WHERE table_name=:table_name"),
                        {"table_name": table.name},
                    ).fetchall()
                }

                for column in table.columns:
                    if column.name in existing_columns:
                        continue

                    column_type = column.type.compile(dialect=postgresql.dialect())
                    conn.execute(
                        text(
                            f"ALTER TABLE {table.name} ADD COLUMN IF NOT EXISTS {column.name} {column_type}"
                        )
                    )
    except Exception as exc:
        print(f"⚠️ Schema compatibility check skipped: {exc}")


# دالة الحصول على الجلسة (Dependency Injection)
def get_db():
    """
    توفير جلسة قاعدة بيانات لكل طلب API وإغلاقها فور الانتهاء 
    لضمان عدم استهلاك الذاكرة (صفحة 137).
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()