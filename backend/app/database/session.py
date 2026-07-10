from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# إعداد المحرك مع تحسينات الأداء (صفحة 208 في التوثيق)
engine = create_engine(
    DATABASE_URL,
    # زيادة عدد الاتصالات المفتوحة للتعامل مع ضغط الـ AI
    pool_size=20, 
    # السماح بزيادة مؤقتة في الاتصالات عند حدوث "انفجار" في التنبيهات
    max_overflow=10,
    # التأكد من أن الاتصال لا يزال حياً قبل استخدامه (يمنع أخطاء الفصل المفاجئ)
    pool_pre_ping=True,
    # إعادة تدوير الاتصالات كل ساعة لمنع الاتصالات "الميتة"
    pool_recycle=3600 
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

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