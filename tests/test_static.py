from datetime import date,time
from app.config import normalize_database_url
from app.services.importer import as_date,as_time

def test_url():assert normalize_database_url('postgresql://u:p@h/d')=='postgresql+psycopg://u:p@h/d'
def test_excel_date():assert as_date(46038)==date(2026,1,16)
def test_excel_time():assert as_time(0.6041666666666666)==time(14,30)
