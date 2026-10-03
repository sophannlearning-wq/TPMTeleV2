from datetime import date,datetime
from io import BytesIO
from openpyxl import load_workbook
from telegram.ext import ConversationHandler,MessageHandler,filters
from sqlalchemy import select
from app.database import db
from app.database.models import Staff,Admin,Lesson,Score,Schedule,Attendance,Notification,AuditLog
from app.services.training import current_plan
from app.services.reports import training_plan_workbook
from app.services.reminders import send_schedule
from app.keyboards.menus import admin_menu,supervisor_menu,staff_menu,inline
LINK,S_CAT,S_LESSON,S_FILE,P_CAT,P_DEPT,P_SEC,SC_LESSON,SC_COUNT,SC_ROW,E_CAT,E_SELECT,E_ACTION,E_DATE,A_LESSON,A_DATE,A_FILE,F_DEPT,M_FILE,LINK_CLEAR,R_CAT,R_LESSON,R_SESSION=range(23)
def identity(chat):
    s=db.SessionLocal();st=s.scalar(select(Staff).where(Staff.telegram_chat_id==chat,Staff.active==True));ad=s.scalar(select(Admin).where(Admin.staff_id==st.staff_id,Admin.active==True)) if st else None;return s,st,ad
def log(s,st,action,target='',detail='',success=True):s.add(AuditLog(actor_staff_id=st.staff_id if st else None,action=action,target=target,detail=detail,success=success))
async def start(update,context):
    s,st,ad=identity(update.effective_chat.id)
    try:
        if not st:await update.effective_message.reply_text("👋 WELCOME TO THE TRAINING SYSTEM\n\nPlease enter your Staff ID.\nExample: 90024252");return LINK
        if ad:await update.effective_message.reply_text(f"🏠 TRAINING MANAGEMENT SYSTEM\n\nWelcome, {st.name}\nRole: {ad.role}",reply_markup=admin_menu())
        elif st.is_supervisor:await update.effective_message.reply_text(f"👥 SUPERVISOR TRAINING MENU\n\nWelcome, {st.name}",reply_markup=supervisor_menu())
        else:await update.effective_message.reply_text(f"👤 MY TRAINING\n\nWelcome, {st.name}",reply_markup=staff_menu())
    finally:s.close()
    return ConversationHandler.END
async def link(update,context):
    s=db.SessionLocal();sid=update.message.text.strip()
    try:
        st=s.scalar(select(Staff).where(Staff.staff_id==sid,Staff.active==True))
        if not st:await update.message.reply_text("❌ Staff ID not found or inactive.");return LINK
        if st.telegram_chat_id and st.telegram_chat_id!=update.effective_chat.id:await update.message.reply_text("⚠️ Staff ID already linked. Contact Admin.");return ConversationHandler.END
        if s.scalar(select(Staff).where(Staff.telegram_chat_id==update.effective_chat.id,Staff.staff_id!=sid)):await update.message.reply_text("⚠️ Telegram account already linked.");return ConversationHandler.END
        st.telegram_chat_id=update.effective_chat.id;ad=s.scalar(select(Admin).where(Admin.staff_id==sid));
        if ad:ad.telegram_chat_id=update.effective_chat.id
        log(s,st,"ACCOUNT_LINK",sid,str(update.effective_chat.id));s.commit();await update.message.reply_text(f"✅ ACCOUNT LINKED\n\n{st.staff_id} — {st.name}")
    finally:s.close()
    await start(update,context);return ConversationHandler.END
async def cancel(update,context):await update.effective_message.reply_text("Cancelled.");return ConversationHandler.END
async def staff_view(update,context):
    s,st,ad=identity(update.effective_chat.id)
    try:await update.message.reply_text("👤 MY TRAINING",reply_markup=staff_menu(st.is_supervisor,bool(ad)))
    finally:s.close()
async def supervisor_view(update,context):await update.message.reply_text("👥 SUPERVISOR VIEW",reply_markup=supervisor_menu())
async def admin_view(update,context):await update.message.reply_text("🛠 ADMIN VIEW",reply_markup=admin_menu())
async def my_dashboard(update,context):
    s,st,ad=identity(update.effective_chat.id)
    try:
        p=current_plan(s,st);passed=sum(x[2]=="Passed" for x in p);await update.message.reply_text(f"📊 MY TRAINING DASHBOARD\n\nRequired: {len(p)}\n✅ Passed: {passed}\nGaps: {len(p)-passed}\n📈 Completion: {(passed/len(p)*100 if p else 0):.1f}%")
    finally:s.close()
async def my_plan(update,context):
    s,st,ad=identity(update.effective_chat.id)
    try:
        lines=[f"📋 MY TRAINING PLAN\n\n{st.name} | {st.staff_id}"]
        for l,sc,status,sessions,att in current_plan(s,st):
            if status=="Passed":continue
            lines.append(f"\n• {l.code} — {l.name}\nStatus: {status} | Score: {sc.score if sc else 'No score'}")
            for x in sessions[:5]:lines.append(f"{x.session_date:%d-%b-%Y} | {x.start_time:%H:%M}-{x.end_time:%H:%M} | {x.location}")
        await update.message.reply_text("\n".join(lines)[:4000])
    finally:s.close()
async def my_sessions(update,context):
    s,st,ad=identity(update.effective_chat.id)
    try:
        lines=["🗓 MY TRAINING SESSIONS"]
        for l,sc,status,sessions,att in current_plan(s,st):
            if status!="Passed":
                for x in sessions:lines.append(f"\n{l.name} | S{x.session_no}\n{x.session_date:%d-%b-%Y} {x.start_time:%H:%M}-{x.end_time:%H:%M}\n{x.location}")
        await update.message.reply_text(("\n".join(lines) if len(lines)>1 else "No relevant active sessions.")[:4000])
    finally:s.close()
async def history(update,context):
    s,st,ad=identity(update.effective_chat.id)
    try:
        xs=list(s.scalars(select(Score).where(Score.staff_id==st.staff_id).order_by(Score.assessment_date.desc()).limit(50)));await update.message.reply_text(("📚 MY TRAINING HISTORY"+"".join(f"\n\n{x.lesson_code} | {x.score:g} | {x.assessment_date:%d-%b-%Y}" for x in xs))[:4000])
    finally:s.close()
async def notifications(update,context):
    s,st,ad=identity(update.effective_chat.id)
    try:
        xs=list(s.scalars(select(Notification).where(Notification.staff_id==st.staff_id).order_by(Notification.created_at.desc()).limit(20)));await update.message.reply_text(("🔔 NOTIFICATIONS"+"".join(f"\n\n{x.created_at:%d-%b %H:%M} | {x.message}" for x in xs) if xs else "🔔 No notifications.")[:4000]);[setattr(x,"read",True) for x in xs];s.commit()
    finally:s.close()
async def profile(update,context):
    s,st,ad=identity(update.effective_chat.id)
    try:await update.message.reply_text(f"👤 MY PROFILE\n\nID: {st.staff_id}\nName: {st.name}\nDepartment: {st.department}\nSection: {st.section}\nPosition: {st.position}\nSupervisor: {st.supervisor_name or '-'}")
    finally:s.close()
async def team_dashboard(update,context):
    s,st,ad=identity(update.effective_chat.id)
    try:
        team=list(s.scalars(select(Staff).where(Staff.supervisor_id==st.staff_id,Staff.active==True)));total=passed=0
        for m in team:p=current_plan(s,m);total+=len(p);passed+=sum(x[2]=="Passed" for x in p)
        await update.message.reply_text(f"📊 MY TEAM DASHBOARD\n\nTeam: {len(team)}\nRequired: {total}\nPassed: {passed}\nGaps: {total-passed}\nCompletion: {(passed/total*100 if total else 0):.1f}%")
    finally:s.close()
async def team_plan(update,context):
    s,st,ad=identity(update.effective_chat.id)
    try:team=list(s.scalars(select(Staff).where(Staff.supervisor_id==st.staff_id,Staff.active==True)));await update.message.reply_document(training_plan_workbook(s,team,f"{st.name} Team Plan"),filename=f"{st.staff_id}_Team_Plan.xlsx")
    finally:s.close()
async def all_sessions(update,context):
    s,st,ad=identity(update.effective_chat.id)
    try:
        xs=list(s.scalars(select(Schedule).where(Schedule.status=="Active",Schedule.session_date>=date.today()).order_by(Schedule.session_date)));await update.message.reply_text(("🗓 ALL TRAINING SESSIONS"+"".join(f"\n\nID {x.id} | {x.lesson_code} S{x.session_no}\n{x.session_date:%d-%b-%Y} {x.start_time:%H:%M}-{x.end_time:%H:%M} | {x.location}" for x in xs))[:4000])
    finally:s.close()
async def admin_dashboard(update,context):await update.message.reply_text("📊 TRAINING DASHBOARD\nChoose category:",reply_markup=inline([("All","dc:All"),("TPM","dc:TPM"),("Safety","dc:Safety"),("ISO","dc:ISO")]))
async def dashboard_category(update,context):q=update.callback_query;await q.answer();context.user_data["category"]=q.data[3:];await q.edit_message_text("Choose period:",reply_markup=inline([(x,"dp:"+x) for x in ["Q1","Q2","Q3","Q4","Yearly"]]))
async def dashboard_period(update,context):
    q=update.callback_query;await q.answer();category=context.user_data.get("category","All");period=q.data[3:];s=db.SessionLocal()
    try:
        people=list(s.scalars(select(Staff).where(Staff.active==True)))
        total_staff=len(people)
        lesson_stats={}
        for st in people:
            for lesson,score,status,sessions,attendance in current_plan(s,st,category):
                stat=lesson_stats.setdefault(lesson.code,{"lesson":lesson,"rows":[]})
                stat["rows"].append((st,score,status))
        lines=[f"📊 TRAINING DASHBOARD\n\nCategory: {category} | Period: {period}\nStaff: {total_staff}"]
        if lesson_stats:
            lines.append("\nLessons:")
            lesson_lines=[]
            for code,data in sorted(lesson_stats.items()):
                trained=sum(1 for _,score,status in data["rows"] if score is not None)
                passed=sum(1 for _,score,status in data["rows"] if status=="Passed")
                lesson=data["lesson"]
                lesson_lines.append(f"{lesson.name} : trained {trained} of {total_staff} and pass {passed}/{trained} = {(passed/trained*100 if trained else 0):.1f}%")
            if len(lesson_lines) > 24:
                lesson_lines = lesson_lines[:24] + [f"...and {len(lesson_lines)-24} more lessons"]
            lines.extend(lesson_lines)
        await q.edit_message_text("\n".join(lines)[:4000])
    finally:s.close()
async def score_start(update,context):await update.message.reply_text("Enter category: TPM, Safety, ISO");return S_CAT
async def score_category(update,context):context.user_data["score_category"]=update.message.text.strip();s=db.SessionLocal();ls=list(s.scalars(select(Lesson).where(Lesson.category==context.user_data["score_category"],Lesson.active==True)));s.close();await update.message.reply_text("Enter Lesson Code:\n"+"\n".join(f"{x.code} — {x.name}" for x in ls));return S_LESSON
async def score_lesson(update,context):context.user_data["score_lesson"]=update.message.text.strip();await update.message.reply_text("Upload .xlsx with columns ID | Score");return S_FILE
async def score_file(update,context):
    f=await update.message.document.get_file();b=BytesIO();await f.download_to_memory(b);b.seek(0);ws=load_workbook(b,data_only=True).active;heads=[str(c.value).strip() if c.value else "" for c in ws[1]]
    if heads[:2] != ["ID","Score"]:await update.message.reply_text("❌ Headers must be ID | Score");return S_FILE
    s,actor,ad=identity(update.effective_chat.id);ok=bad=0;ref=datetime.now().strftime("SCORE-%Y%m%d-%H%M%S")
    try:
        lesson=s.scalar(select(Lesson).where(Lesson.code==context.user_data["score_lesson"],Lesson.category==context.user_data["score_category"]))
        for r in ws.iter_rows(min_row=2,values_only=True):
            if not r[0]:continue
            st=s.scalar(select(Staff).where(Staff.staff_id==str(r[0]).strip(),Staff.active==True));v=r[1]
            if not st or not isinstance(v,(int,float)) or not 0<=v<=100:bad+=1;continue
            s.add(Score(staff_id=st.staff_id,category=lesson.category,lesson_code=lesson.code,score=float(v),assessment_date=date.today(),training_date=date.today(),upload_ref=ref,remark="Telegram upload"));ok+=1
        log(s,actor,"SCORE_UPLOAD",lesson.code,f"ok={ok},bad={bad}");s.commit();await update.message.reply_text(f"✅ Completed\nReference: {ref}\nValid: {ok}\nInvalid: {bad}")
    finally:s.close()
    return ConversationHandler.END

async def plan_start(update,context):
    await update.message.reply_text('📋 Generate Training Plan\nChoose category: TPM, Safety, ISO')
    return P_CAT
async def plan_category(update,context):
    context.user_data['plan_category']=update.message.text.strip()
    s=db.SessionLocal()
    try:
        depts=['All']+[x for x in s.scalars(select(Staff.department).where(Staff.active==True).distinct().order_by(Staff.department)) if x]
        await update.message.reply_text('Choose Department:\n'+'\n'.join(depts))
    finally:s.close()
    return P_DEPT
async def plan_department(update,context):
    context.user_data['plan_department']=update.message.text.strip();s=db.SessionLocal()
    try:
        secs=['All'] if context.user_data['plan_department']=='All' else ['All']+[x for x in s.scalars(select(Staff.section).where(Staff.department==context.user_data['plan_department']).distinct().order_by(Staff.section)) if x]
        await update.message.reply_text('Choose Section:\n'+'\n'.join(secs))
    finally:s.close()
    return P_SEC
async def plan_section(update,context):
    s,actor,ad=identity(update.effective_chat.id)
    try:
        q=select(Staff).where(Staff.active==True)
        dept=context.user_data['plan_department'];sec=update.message.text.strip();
        if dept!='All':q=q.where(Staff.department==dept)
        if sec!='All':q=q.where(Staff.section==sec)
        people=list(s.scalars(q.order_by(Staff.name)))
        category=context.user_data.get('plan_category','All')
        log(s,actor,'GENERATE_PLAN',f'{category}:{dept}',f'{sec}; staff={len(people)}')
        await update.message.reply_document(training_plan_workbook(s,people,f'{category} / {dept} / {sec} Training Plan',category=category),filename=f'{category}_{dept}_{sec}_Training_Plan.xlsx')
    finally:s.close()
    return ConversationHandler.END
async def schedule_start(update,context):await update.message.reply_text('Enter Lesson Code');return SC_LESSON
async def schedule_lesson(update,context):context.user_data['lesson']=update.message.text.strip();await update.message.reply_text('Number of sessions, 1-10');return SC_COUNT
async def schedule_count(update,context):
    try:n=int(update.message.text)
    except ValueError:await update.message.reply_text('Enter 1-10');return SC_COUNT
    if n<1 or n>10:await update.message.reply_text('Enter 1-10');return SC_COUNT
    context.user_data['count']=n;context.user_data['rows']=[];await update.message.reply_text('Session 1: DD-MMM-YYYY | HH:MM | HH:MM | Location');return SC_ROW
async def schedule_row(update,context):
    try:
        a=[x.strip() for x in update.message.text.split('|')];row=(datetime.strptime(a[0],'%d-%b-%Y').date(),datetime.strptime(a[1],'%H:%M').time(),datetime.strptime(a[2],'%H:%M').time(),a[3])
    except Exception:await update.message.reply_text('Use DD-MMM-YYYY | HH:MM | HH:MM | Location');return SC_ROW
    context.user_data['rows'].append(row)
    if len(context.user_data['rows'])<context.user_data['count']:
        await update.message.reply_text(f"Session {len(context.user_data['rows'])+1}: same format");return SC_ROW
    s,actor,ad=identity(update.effective_chat.id)
    try:
        lesson=s.scalar(select(Lesson).where(Lesson.code==context.user_data['lesson']))
        if not lesson:await update.message.reply_text('Lesson not found');return ConversationHandler.END
        for i,r in enumerate(context.user_data['rows'],1):s.add(Schedule(category=lesson.category,lesson_code=lesson.code,session_no=i,session_date=r[0],start_time=r[1],end_time=r[2],location=r[3],status='Active'))
        log(s,actor,'CREATE_SCHEDULE',lesson.code,str(len(context.user_data['rows'])));s.commit();await update.message.reply_text('✅ Schedule created and reminders enabled.')
    finally:s.close()
    return ConversationHandler.END
async def edit_start(update,context):
    await update.message.reply_text('📅 Edit Schedule\nChoose category: TPM, Safety, ISO')
    return E_CAT
async def edit_category(update,context):
    category=update.message.text.strip();context.user_data['edit_category']=category
    s=db.SessionLocal()
    try:
        rows=list(s.scalars(select(Schedule).where(Schedule.category==category,Schedule.status=='Active').order_by(Schedule.session_date,Schedule.start_time)))
        if not rows:
            await update.message.reply_text('No active schedules found for that category.');return ConversationHandler.END
        text='Select Schedule ID to edit/delete:'
        for x in rows[:20]:text+=f'\n\nID {x.id} | {x.lesson_code} | {x.session_date:%d-%b-%Y} {x.start_time:%H:%M}-{x.end_time:%H:%M} | {x.location}'
        await update.message.reply_text(text[:4000]);
    finally:s.close()
    return E_SELECT
async def edit_select(update,context):
    context.user_data['schedule_id']=update.message.text.strip();
    await update.message.reply_text('Type edit or delete')
    return E_ACTION
async def edit_action(update,context):
    action=update.message.text.strip().lower()
    if action=='delete':
        s,actor,ad=identity(update.effective_chat.id)
        try:
            x=s.get(Schedule,int(context.user_data['schedule_id']))
            x.status='Cancelled';x.remark='Deleted by admin';log(s,actor,'DELETE_SCHEDULE',str(x.id));s.commit();await update.message.reply_text('✅ Schedule deleted.')
        except Exception:await update.message.reply_text('❌ Invalid schedule ID.');
        finally:s.close()
        return ConversationHandler.END
    if action!='edit':
        await update.message.reply_text('Please type edit or delete.');return E_ACTION
    await update.message.reply_text('Enter new schedule data: DD-MMM-YYYY | HH:MM | HH:MM | Location')
    return E_DATE
async def edit_date(update,context):
    s,actor,ad=identity(update.effective_chat.id)
    try:
        x=s.get(Schedule,int(context.user_data['schedule_id']));a=[v.strip() for v in update.message.text.split('|')]
        x.session_date=datetime.strptime(a[0],'%d-%b-%Y').date();x.start_time=datetime.strptime(a[1],'%H:%M').time();x.end_time=datetime.strptime(a[2],'%H:%M').time();x.location=a[3];x.week_sent=x.day_sent=x.hour_sent=False;log(s,actor,'EDIT_SCHEDULE',str(x.id));s.commit();await update.message.reply_text('✅ Schedule updated.')
    except Exception:await update.message.reply_text('❌ Invalid input or schedule ID.')
    finally:s.close()
    return ConversationHandler.END
async def attendance_start(update,context):await update.message.reply_text('Enter Lesson Code');return A_LESSON
async def attendance_lesson(update,context):context.user_data['lesson']=update.message.text.strip();await update.message.reply_text('Session date DD-MMM-YYYY');return A_DATE
async def attendance_date(update,context):
    try:context.user_data['date']=datetime.strptime(update.message.text.strip(),'%d-%b-%Y').date()
    except ValueError:await update.message.reply_text('Use DD-MMM-YYYY');return A_DATE
    await update.message.reply_text('Upload .xlsx: ID | Attendance | Remark');return A_FILE
async def attendance_file(update,context):
    f=await update.message.document.get_file();b=BytesIO();await f.download_to_memory(b);b.seek(0);ws=load_workbook(b,data_only=True).active;s,actor,ad=identity(update.effective_chat.id);ok=bad=0
    try:
        lesson=s.scalar(select(Lesson).where(Lesson.code==context.user_data['lesson']))
        for r in ws.iter_rows(min_row=2,values_only=True):
            if not r[0]:continue
            member=s.scalar(select(Staff).where(Staff.staff_id==str(r[0]).strip()));v=str(r[1] or '').title()
            if not member or v not in ('Present','Absent','Excused','Late'):bad+=1;continue
            s.add(Attendance(staff_id=member.staff_id,category=lesson.category,lesson_code=lesson.code,session_date=context.user_data['date'],attendance=v,remark=r[2]));ok+=1
        log(s,actor,'ATTENDANCE_UPLOAD',lesson.code,f'ok={ok},bad={bad}');s.commit();await update.message.reply_text(f'✅ Attendance saved. Valid {ok}; invalid {bad}.')
    finally:s.close()
    return ConversationHandler.END
async def send_reminders_start(update,context):
    await update.message.reply_text('Enter Lesson Code')
    return R_LESSON
async def send_reminders_lesson(update,context):
    lesson_code=update.message.text.strip();context.user_data['reminder_lesson']=lesson_code
    s=db.SessionLocal()
    try:
        lesson=s.scalar(select(Lesson).where(Lesson.code==lesson_code,Lesson.active==True))
        if not lesson:
            await update.message.reply_text('❌ Lesson not found. Enter Lesson Code')
            return R_LESSON
        rows=list(s.scalars(select(Schedule).where(Schedule.lesson_code==lesson_code,Schedule.status=='Active',Schedule.session_date>=date.today()).order_by(Schedule.session_date,Schedule.start_time)))
        if not rows:
            await update.message.reply_text('❌ No upcoming active sessions found for that lesson.')
            return ConversationHandler.END
        lines=['Select session ID to send reminder:']
        for x in rows:lines.append(f'ID {x.id}: S{x.session_no} | {x.session_date:%d-%b-%Y} {x.start_time:%H:%M}-{x.end_time:%H:%M} | {x.location}')
        await update.message.reply_text('\n'.join(lines))
        return R_SESSION
    finally:
        s.close()
async def send_reminders_session(update,context):
    session_text=update.message.text.strip()
    if not session_text.isdigit():
        await update.message.reply_text('❌ Enter a valid session ID.')
        return R_SESSION
    schedule_id=int(session_text)
    s,actor,ad=identity(update.effective_chat.id)
    try:
        sch=s.scalar(select(Schedule).where(Schedule.id==schedule_id,Schedule.status=='Active',Schedule.session_date>=date.today()))
        if not sch:
            await update.message.reply_text('❌ Session not found. Enter a valid session ID.')
            return R_SESSION
        count=await send_schedule(context,s,sch,f'for session {sch.session_no}')
        log(s,actor,'MANUAL_REMINDERS',sch.lesson_code,f'session_id={schedule_id},count={count}')
        s.commit();await update.message.reply_text(f'✅ Reminder sent for {sch.lesson_code} session {sch.session_no}. Messages: {count}')
    finally:
        s.close()
    return ConversationHandler.END
async def follow_start(update,context):await update.message.reply_text('Enter Department or All');return F_DEPT
async def follow_department(update,context):
    s,actor,ad=identity(update.effective_chat.id);dept=update.message.text.strip()
    try:
        q=select(Staff).where(Staff.active==True)
        if dept!='All':q=q.where(Staff.department==dept)
        people=list(s.scalars(q));groups={}
        for m in people:
            if any(x[2]!='Passed' for x in current_plan(s,m)):groups.setdefault(m.supervisor_id,[]).append(m)
        sent=failed=0
        for sid,members in groups.items():
            sup=s.scalar(select(Staff).where(Staff.staff_id==sid))
            if not sup or not sup.telegram_chat_id:failed+=1;continue
            try:await context.bot.send_document(sup.telegram_chat_id,training_plan_workbook(s,members,f'{sup.name} Follow-up'),filename=f'{sid}_Follow_Up.xlsx');sent+=1
            except Exception:failed+=1
        log(s,actor,'FOLLOW_UP',dept,f'sent={sent},failed={failed}');s.commit();await update.message.reply_text(f'✅ Follow-up sent {sent}; failed {failed}.')
    finally:s.close()
    return ConversationHandler.END
async def reports(update,context):
    await update.message.reply_text('📈 REPORTS\nChoose category for summary results: TPM, Safety, ISO')
    return R_CAT
async def reports_category(update,context):
    category=context.user_data['report_category']=update.message.text.strip();
    s,st,ad=identity(update.effective_chat.id)
    try:
        people=list(s.scalars(select(Staff).where(Staff.active==True)))
        total=len(people);passed=0;dept_stats={};
        for person in people:
            p=current_plan(s,person,category)
            ps=sum(x[2]=='Passed' for x in p);passed+=ps
            dept=person.department or 'Unknown';stats=dept_stats.setdefault(dept,[0,0]);stats[0]+=len(p);stats[1]+=ps
        overall = passed/total*100 if total else 0
        lines=[f'📈 REPORTS\nCategory: {category}\nTotal staff: {total}\nTotal required items: {sum(v[0] for v in dept_stats.values())}\nPassed count: {passed}\nPass %: {overall:.1f}%\n']
        lines.append('By Department:')
        for dept,(req,ps) in sorted(dept_stats.items()):
            pct = ps/req*100 if req else 0
            lines.append(f'{dept}: {ps}/{req} passed ({pct:.1f}%)')
        await update.message.reply_text('\n'.join(lines)[:4000])
    finally:s.close()
    return ConversationHandler.END
async def telegram_linking(update,context):
    s,st,ad=identity(update.effective_chat.id)
    if not ad and not (st and st.is_supervisor):
        await update.message.reply_text('⚠️ Only admin or supervisor can clear links.');
        return ConversationHandler.END
    await update.message.reply_text('🔗 TELEGRAM LINKING\nEnter Staff ID to clear the linked Telegram account.')
    return LINK_CLEAR
async def clear_link(update,context):
    staff_id=update.message.text.strip();s,st,ad=identity(update.effective_chat.id)
    try:
        target=s.scalar(select(Staff).where(Staff.staff_id==staff_id,Staff.active==True))
        if not target:
            await update.message.reply_text('❌ Staff ID not found.');return ConversationHandler.END
        if not target.telegram_chat_id:
            await update.message.reply_text('ℹ️ This staff is not linked.');return ConversationHandler.END
        target.telegram_chat_id=None
        admin_record=s.scalar(select(Admin).where(Admin.staff_id==staff_id))
        if admin_record:admin_record.telegram_chat_id=None
        log(s,st,'CLEAR_LINK',staff_id,'Telegram link cleared');s.commit();await update.message.reply_text(f'✅ Link cleared for {staff_id} — {target.name}')
    finally:s.close()
    return ConversationHandler.END
async def staff_management(update,context):
    context.user_data['master']='staff';
    await update.message.reply_text('Upload updated Staff Master .xlsx with the same columns as 01_Staff_Master.xlsx');
    return M_FILE
async def lesson_management(update,context):
    context.user_data['master']='lesson';
    await update.message.reply_text('Upload updated Lesson Master .xlsx');
    return M_FILE
async def master_file(update,context):
    f=await update.message.document.get_file();b=BytesIO();await f.download_to_memory(b);b.seek(0);wb=load_workbook(b,data_only=True)
    ws=wb.active;headers=[str(c.value).strip() if c.value else '' for c in ws[1]]
    required=['Staff ID','Staff Name']
    if not all(col in headers for col in required):
        await update.message.reply_text('❌ Required columns missing: Staff ID, Staff Name');return ConversationHandler.END
    idx={h:i for i,h in enumerate(headers)}
    s,actor,ad=identity(update.effective_chat.id);added=0;updated=0;bad=0
    try:
        for row in ws.iter_rows(min_row=2,values_only=True):
            if not row or not row[idx['Staff ID']]:continue
            staff_id=str(row[idx['Staff ID']]).strip();name=str(row[idx['Staff Name']]).strip()
            st=s.scalar(select(Staff).where(Staff.staff_id==staff_id))
            if st:
                st.name=name;updated+=1
            else:
                st=Staff(staff_id=staff_id,name=name,active=True);s.add(st);added+=1
            st.department=str(row[idx['Department']]).strip() if 'Department' in idx and row[idx['Department']] else st.department
            st.section=str(row[idx['Section']]).strip() if 'Section' in idx and row[idx['Section']] else st.section
            st.position=str(row[idx['Position']]).strip() if 'Position' in idx and row[idx['Position']] else st.position
            st.supervisor_id=str(row[idx['Supervisor ID']]).strip() if 'Supervisor ID' in idx and row[idx['Supervisor ID']] else st.supervisor_id
            st.supervisor_name=str(row[idx['Supervisor Name']]).strip() if 'Supervisor Name' in idx and row[idx['Supervisor Name']] else st.supervisor_name
            if 'Is Supervisor' in idx and row[idx['Is Supervisor']] is not None:st.is_supervisor=str(row[idx['Is Supervisor']]).strip().lower() in {'yes','y','true','1'}
            if 'Active' in idx and row[idx['Active']] is not None:st.active=str(row[idx['Active']]).strip().lower() in {'yes','y','true','1'}
            if 'Shift' in idx and row[idx['Shift']]:st.shift=str(row[idx['Shift']]).strip()
            if 'Telegram Chat ID' in idx and row[idx['Telegram Chat ID']]:
                try:st.telegram_chat_id=int(row[idx['Telegram Chat ID']])
                except Exception:pass
            if 'Join Date' in idx and row[idx['Join Date']]:
                try:st.join_date=datetime.strptime(str(row[idx['Join Date']]).strip(),'%d-%b-%Y').date()
                except Exception:pass
            if 'Location' in idx and row[idx['Location']]:st.location=str(row[idx['Location']]).strip()
        s.commit();await update.message.reply_text(f'✅ Staff Master imported. Added: {added}; Updated: {updated}')
    finally:s.close()
    return ConversationHandler.END
async def unknown(update,context):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    return
async def cancel(update,context):await update.effective_message.reply_text('Cancelled.');return ConversationHandler.END
