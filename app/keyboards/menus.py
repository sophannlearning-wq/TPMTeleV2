from telegram import ReplyKeyboardMarkup,InlineKeyboardButton,InlineKeyboardMarkup
def admin_menu():return ReplyKeyboardMarkup([['📊 Training Dashboard','📝 Score Update'],['📋 Generate Training Plan','📅 Create Schedule'],['✏️ Edit Schedule','🔔 Send Reminders'],['✅ Attendance','👥 Follow-up Training'],['📈 Reports','👤 Staff Management'],['📘 Lesson Management','🔗 Telegram Linking'],['🙋 My Staff View']],resize_keyboard=True)
def supervisor_menu():return ReplyKeyboardMarkup([['📊 My Team Dashboard','📋 My Team Plan'],['🗓 All Training Sessions','🔔 Notifications'],['🙋 My Staff View']],resize_keyboard=True)
def staff_menu(supervisor=False,admin=False):
    rows=[['📊 My Dashboard','📋 My Plan'],['🗓 My Training Sessions','📚 My Training History'],['🔔 Notifications','👤 My Profile']]
    if supervisor:rows.append(['👥 Supervisor View'])
    if admin:rows.append(['🛠 Admin View'])
    return ReplyKeyboardMarkup(rows,resize_keyboard=True)
def inline(items,cols=2):return InlineKeyboardMarkup([[InlineKeyboardButton(t,callback_data=v) for t,v in items[i:i+cols]] for i in range(0,len(items),cols)])
