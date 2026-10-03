from datetime import date
from calendar import monthrange
from sqlalchemy import select
from app.database.models import Lesson,Requirement,Score,Schedule,Attendance
def add_months(d,n):
    y=d.year+(d.month-1+n)//12;m=(d.month-1+n)%12+1;return date(y,m,min(d.day,monthrange(y,m)[1]))
def applies(r,st):return r.active and r.required and r.department in ("All",st.department) and r.section in ("All",st.section) and r.position in ("All",st.position)
def current_plan(s,st,category="All"):
    lessons={x.code:x for x in s.scalars(select(Lesson).where(Lesson.active==True))};required={r.lesson_code for r in s.scalars(select(Requirement).where(Requirement.active==True)) if applies(r,st)};result=[]
    for code in sorted(required):
        lesson=lessons.get(code)
        if not lesson or (category!="All" and lesson.category!=category):continue
        score=s.scalar(select(Score).where(Score.staff_id==st.staff_id,Score.lesson_code==code).order_by(Score.assessment_date.desc(),Score.id.desc()))
        attendance=s.scalar(select(Attendance).where(Attendance.staff_id==st.staff_id,Attendance.lesson_code==code,Attendance.attendance=="Present").order_by(Attendance.session_date.desc(),Attendance.id.desc()))
        valid=bool(score and score.score>=lesson.pass_score and (lesson.validity_months==0 or add_months(score.assessment_date,lesson.validity_months)>=date.today()))
        status="Passed" if valid else ("Retraining Required" if score and score.score<lesson.pass_score else ("Expired" if score else ("Waiting for Score" if attendance else "Training Required")))
        sessions=list(s.scalars(select(Schedule).where(Schedule.lesson_code==code,Schedule.status=="Active",Schedule.session_date>=date.today()).order_by(Schedule.session_date,Schedule.start_time)))
        result.append((lesson,score,status,sessions,attendance))
    return result
def period_bounds(year,period):
    if period=="Yearly":return date(year,1,1),date(year,12,31)
    q=int(period[1]);m=(q-1)*3+1;return date(year,m,1),date(year,m+2,monthrange(year,m+2)[1])
