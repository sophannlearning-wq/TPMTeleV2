from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from sqlalchemy import select
from app.database import db
from app.database.models import Schedule,Staff,Lesson,Notification
from app.services.training import current_plan
async def send_schedule(context,s,sch,label):
    lesson=s.scalar(select(Lesson).where(Lesson.code==sch.lesson_code));count=0
    for st in s.scalars(select(Staff).where(Staff.active==True,Staff.telegram_chat_id.is_not(None))):
        if any(x[0].code==sch.lesson_code and x[2]!="Passed" for x in current_plan(s,st)):
            msg=f"🔔 TRAINING REMINDER\n\nTraining {label}\nLesson: {lesson.name if lesson else sch.lesson_code}\nDate: {sch.session_date:%d-%b-%Y}\nTime: {sch.start_time:%H:%M}-{sch.end_time:%H:%M}\nLocation: {sch.location}"
            try:await context.bot.send_message(st.telegram_chat_id,msg);sent=True;count+=1
            except Exception:sent=False
            s.add(Notification(staff_id=st.staff_id,kind="Reminder",message=msg,sent=sent))
    return count
async def run(context,timezone):
    s=db.SessionLocal();now=datetime.now(ZoneInfo(timezone))
    try:
        for sch in s.scalars(select(Schedule).where(Schedule.status=="Active")):
            scheduled_dt=datetime.combine(sch.session_date,sch.start_time,tzinfo=ZoneInfo(timezone))
            if scheduled_dt <= now:continue
            delta=scheduled_dt-now;field=label=None
            tomorrow_date=(now.date()+timedelta(days=1))
            if sch.session_date==tomorrow_date and now.time()>=datetime.strptime('14:30','%H:%M').time() and now.time()<datetime.strptime('15:00','%H:%M').time() and not sch.day_sent:
                field,label='day_sent','tomorrow at 2:30PM'
            elif timedelta(hours=1,minutes=45)<=delta<=timedelta(hours=2,minutes=15) and not sch.hour_sent:
                field,label='hour_sent','2 hours before start'
            if field:
                await send_schedule(context,s,sch,label)
                setattr(sch,field,True)
                s.commit()
    finally:s.close()
