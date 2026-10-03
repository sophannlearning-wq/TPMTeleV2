from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Font,PatternFill
from app.services.training import current_plan
NAVY="17365D"
def style_header(row):
    for c in row:c.font=Font(bold=True,color="FFFFFF");c.fill=PatternFill("solid",fgColor=NAVY)
def normalize_sheet_name(name):
    invalid='[]:*?/\\'
    clean=''.join(c for c in name if c not in invalid)
    return clean[:31] or 'Sheet1'
def training_plan_workbook(s,people,title="Training Plan",category=None):
    wb=Workbook();summary=wb.active;summary.title="Summary";summary.append([title]);summary.merge_cells("A1:H1");summary["A1"].font=Font(size=16,bold=True,color="FFFFFF");summary["A1"].fill=PatternFill("solid",fgColor=NAVY)
    summary.append(["Lesson Code","Lesson Name","Category","Total Required","Trained","Trained %","Passed","Pass Ratio","Training Required","Training Required %"]);style_header(summary[2])
    lesson_groups={}
    for st in people:
        p=current_plan(s,st,category) if category else current_plan(s,st)
        for lesson,score,status,sessions,attendance in p:
            group=lesson_groups.setdefault(lesson.code,{"lesson":lesson,"rows":[]})
            group["rows"].append({"staff":st,"score":score,"status":status,"sessions":sessions,"attendance":attendance})
    for code,data in sorted(lesson_groups.items()):
        lesson=data["lesson"]
        rows=data["rows"]
        total=len(rows)
        trained=total
        passed=sum(1 for row in rows if row["status"]=="Passed")
        train_required=sum(1 for row in rows if row["status"]!="Passed")
        summary.append([lesson.code,lesson.name,lesson.category,total,trained,(trained/total if total else 0),passed,f"{passed}/{trained}" if trained else "0/0",train_required,(train_required/total if total else 0)])
        summary.cell(summary.max_row,6).number_format="0.0%"
        summary.cell(summary.max_row,10).number_format="0.0%"
        ws=wb.create_sheet(normalize_sheet_name(f"{lesson.code} {lesson.name}"))
        ws.append(["Staff ID","Name","Department","Section","Position","Supervisor","Score","Status","Sessions","Attendance"]);style_header(ws[1])
        for row in rows:
            st=row["staff"]
            score=row["score"]
            attendance=row["attendance"]
            sessions=row["sessions"]
            session_text="; ".join(f"S{x.session_no} {x.session_date:%d-%b-%Y} {x.start_time:%H:%M}-{x.end_time:%H:%M} @ {x.location}" for x in sessions) if sessions else ""
            ws.append([st.staff_id,st.name,st.department,st.section,st.position,st.supervisor_name,score.score if score else None,row["status"],session_text,attendance.attendance if attendance else None])
    for ws in wb.worksheets:ws.freeze_panes="A2";ws.auto_filter.ref=ws.dimensions
    b=BytesIO();wb.save(b);b.seek(0);return b
