import logging,re
from telegram import Update
from telegram.error import Conflict,NetworkError,TimedOut
from telegram.ext import Application,CommandHandler,MessageHandler,CallbackQueryHandler,ConversationHandler,filters
from app.config import load_settings
from app.database import db
from app.database.models import Staff
from app.services.importer import import_all,ensure_bootstrap
from app.services.reminders import run as reminder_run
from app.handlers import core
logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(name)s: %(message)s');log=logging.getLogger('training_bot')
async def error_handler(update,context):
    if isinstance(context.error,Conflict):log.error('Polling conflict: another instance uses this BOT_TOKEN');return
    if isinstance(context.error,(NetworkError,TimedOut)):log.warning('Temporary network error: %s',context.error);return
    log.exception('Unhandled update error',exc_info=context.error)
async def health(update,context):await update.effective_message.reply_text('✅ Training bot is online.')
async def reminder_job(context):await reminder_run(context,context.application.bot_data['cfg'].timezone)
def exact(x):return filters.TEXT&filters.Regex('^'+re.escape(x)+'$')
def main():
    cfg=load_settings();db.configure(cfg.database_url);s=db.SessionLocal();empty=s.query(Staff).count()==0;s.close()
    if empty:log.info('Initial import: %s',import_all(cfg.data_dir))
    ensure_bootstrap(cfg.bootstrap_admin_staff_id,cfg.bootstrap_admin_name)
    app=Application.builder().token(cfg.bot_token).build();app.bot_data['cfg']=cfg
    link=ConversationHandler(entry_points=[CommandHandler('start',core.start)],states={core.LINK:[MessageHandler(filters.TEXT&~filters.COMMAND,core.link)]},fallbacks=[CommandHandler('cancel',core.cancel)])
    score=ConversationHandler(entry_points=[MessageHandler(exact('📝 Score Update'),core.score_start)],states={core.S_CAT:[MessageHandler(filters.TEXT&~filters.COMMAND,core.score_category)],core.S_LESSON:[MessageHandler(filters.TEXT&~filters.COMMAND,core.score_lesson)],core.S_FILE:[MessageHandler(filters.Document.FileExtension('xlsx'),core.score_file)]},fallbacks=[CommandHandler('cancel',core.cancel)])
    plan=ConversationHandler(entry_points=[MessageHandler(exact('📋 Generate Training Plan'),core.plan_start)],states={core.P_CAT:[MessageHandler(filters.TEXT&~filters.COMMAND,core.plan_category)],core.P_DEPT:[MessageHandler(filters.TEXT&~filters.COMMAND,core.plan_department)],core.P_SEC:[MessageHandler(filters.TEXT&~filters.COMMAND,core.plan_section)]},fallbacks=[CommandHandler('cancel',core.cancel)])
    schedule=ConversationHandler(entry_points=[MessageHandler(exact('📅 Create Schedule'),core.schedule_start)],states={core.SC_LESSON:[MessageHandler(filters.TEXT&~filters.COMMAND,core.schedule_lesson)],core.SC_COUNT:[MessageHandler(filters.TEXT&~filters.COMMAND,core.schedule_count)],core.SC_ROW:[MessageHandler(filters.TEXT&~filters.COMMAND,core.schedule_row)]},fallbacks=[CommandHandler('cancel',core.cancel)])
    edit=ConversationHandler(entry_points=[MessageHandler(exact('✏️ Edit Schedule'),core.edit_start)],states={core.E_CAT:[MessageHandler(filters.TEXT&~filters.COMMAND,core.edit_category)],core.E_SELECT:[MessageHandler(filters.TEXT&~filters.COMMAND,core.edit_select)],core.E_ACTION:[MessageHandler(filters.TEXT&~filters.COMMAND,core.edit_action)],core.E_DATE:[MessageHandler(filters.TEXT&~filters.COMMAND,core.edit_date)]},fallbacks=[CommandHandler('cancel',core.cancel)])
    reports=ConversationHandler(entry_points=[MessageHandler(exact('📈 Reports'),core.reports)],states={core.R_CAT:[MessageHandler(filters.TEXT&~filters.COMMAND,core.reports_category)]},fallbacks=[CommandHandler('cancel',core.cancel)])
    telegram_link=ConversationHandler(entry_points=[MessageHandler(exact('🔗 Telegram Linking'),core.telegram_linking)],states={core.LINK_CLEAR:[MessageHandler(filters.TEXT&~filters.COMMAND,core.clear_link)]},fallbacks=[CommandHandler('cancel',core.cancel)])
    attendance=ConversationHandler(entry_points=[MessageHandler(exact('✅ Attendance'),core.attendance_start)],states={core.A_LESSON:[MessageHandler(filters.TEXT&~filters.COMMAND,core.attendance_lesson)],core.A_DATE:[MessageHandler(filters.TEXT&~filters.COMMAND,core.attendance_date)],core.A_FILE:[MessageHandler(filters.Document.FileExtension('xlsx'),core.attendance_file)]},fallbacks=[CommandHandler('cancel',core.cancel)])
    follow=ConversationHandler(entry_points=[MessageHandler(exact('👥 Follow-up Training'),core.follow_start)],states={core.F_DEPT:[MessageHandler(filters.TEXT&~filters.COMMAND,core.follow_department)]},fallbacks=[CommandHandler('cancel',core.cancel)])
    remind=ConversationHandler(entry_points=[MessageHandler(exact('🔔 Send Reminders'),core.send_reminders_start)],states={core.R_LESSON:[MessageHandler(filters.TEXT&~filters.COMMAND,core.send_reminders_lesson)],core.R_SESSION:[MessageHandler(filters.TEXT&~filters.COMMAND,core.send_reminders_session)]},fallbacks=[CommandHandler('cancel',core.cancel)])
    manage=ConversationHandler(entry_points=[MessageHandler(exact('👤 Staff Management'),core.staff_management),MessageHandler(exact('📘 Lesson Management'),core.lesson_management)],states={core.M_FILE:[MessageHandler(filters.Document.FileExtension('xlsx'),core.master_file)]},fallbacks=[CommandHandler('cancel',core.cancel)])
    for h in [link,score,plan,schedule,edit,reports,telegram_link,attendance,follow,remind,manage]:app.add_handler(h)
    app.add_handler(CommandHandler('menu',core.start));app.add_handler(CommandHandler('health',health));app.add_handler(CallbackQueryHandler(core.dashboard_category,pattern='^dc:'));app.add_handler(CallbackQueryHandler(core.dashboard_period,pattern='^dp:'))
    buttons={'📊 Training Dashboard':core.admin_dashboard,'🔔 Send Reminders':core.send_reminders_start,'🙋 My Staff View':core.staff_view,'📊 My Dashboard':core.my_dashboard,'📋 My Plan':core.my_plan,'🗓 My Training Sessions':core.my_sessions,'📚 My Training History':core.history,'🔔 Notifications':core.notifications,'👤 My Profile':core.profile,'📊 My Team Dashboard':core.team_dashboard,'📋 My Team Plan':core.team_plan,'🗓 All Training Sessions':core.all_sessions,'👥 Supervisor View':core.supervisor_view,'🛠 Admin View':core.admin_view}
    for text,fn in buttons.items():app.add_handler(MessageHandler(exact(text),fn),group=10)
    app.add_handler(MessageHandler(filters.TEXT&~filters.COMMAND,core.unknown),group=100);app.add_error_handler(error_handler);app.job_queue.run_repeating(reminder_job,900,first=30);log.info('Bot polling started');app.run_polling(drop_pending_updates=True,allowed_updates=Update.ALL_TYPES)
if __name__=='__main__':main()
