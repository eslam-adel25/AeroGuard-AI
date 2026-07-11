import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
engine = create_engine(os.getenv('DATABASE_URL'))
with engine.connect() as conn:
    for table in ['users','roles','email_verifications','refresh_tokens']:
        exists = conn.execute(text("select to_regclass(:table)"), {'table': f'public.{table}'}).scalar()
        print(table, exists)
    print('users count', conn.execute(text('select count(*) from users')).scalar())
    print('roles count', conn.execute(text('select count(*) from roles')).scalar())
    rows = conn.execute(text('select username, email, is_verified, status from users limit 10')).fetchall()
    print(rows)
engine.dispose()
