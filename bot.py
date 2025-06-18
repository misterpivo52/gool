import json
import os
import logging
import re
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = "7455767385:AAGHA5dnUIP3frcLmbNcp77gCljI75R5mBY"
ADMIN_CHAT_ID = "1201289440"
USERS_FILE = "data/users.json"

def is_valid_email(email):
    return '@' in email and len(email.split('@')) == 2 and '.' in email.split('@')[1]

def is_valid_password(password):
    return len(password) >= 6

PAYMENT_DETAILS = """
💳 Реквізити для поповнення:
Картка: 1234 5678 9012 3456
Власник: ІВАН ІВАНОВИЧ І.
Банк: ПриватБанк

📱 Monobank: 5375 4141 1234 5678
Власник: ІВАН ІВАНОВИЧ І.

Будь ласка, вкажіть в коментарі до переказу ваш email!
"""

USER_STATES = {}

def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
    return {}

def save_users(users_data):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users_data, f, ensure_ascii=False, indent=2)

def get_main_keyboard():
    keyboard = [
        ['🚪 Вхід', '📝 Реєстрація'],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_user_keyboard():
    keyboard = [
        ['💰 Поповнити баланс', '👤 Мій профіль'],
        ['🚪 Вийти']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_admin_keyboard():
    keyboard = [
        ['👥 Користувачі', '💰 Керування балансом'],
        ['📊 Статистика', '⚙️ Налаштування']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_users_list_keyboard(users_data, page=0, per_page=5):
    users_list = list(users_data.items())
    total_pages = (len(users_list) + per_page - 1) // per_page

    keyboard = []
    start_idx = page * per_page
    end_idx = min(start_idx + per_page, len(users_list))

    for i in range(start_idx, end_idx):
        email, user_data = users_list[i]
        keyboard.append([InlineKeyboardButton(
            f"👤 {user_data['name']} ({user_data['balance']} грн)",
            callback_data=f"admin_user_{email}"
        )])

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ Назад", callback_data=f"admin_users_page_{page - 1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("Вперед ▶️", callback_data=f"admin_users_page_{page + 1}"))

    if nav_buttons:
        keyboard.append(nav_buttons)

    return InlineKeyboardMarkup(keyboard)

def get_user_management_keyboard(email):
    keyboard = [
        [InlineKeyboardButton("💰 Змінити баланс", callback_data=f"admin_change_balance_{email}")],
        [InlineKeyboardButton("📊 Детальна інформація", callback_data=f"admin_user_info_{email}")],
        [InlineKeyboardButton("🔙 Назад до списку", callback_data="admin_users_page_0")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_balance_keyboard():
    keyboard = [
        [InlineKeyboardButton("100 грн", callback_data="topup_100")],
        [InlineKeyboardButton("250 грн", callback_data="topup_250")],
        [InlineKeyboardButton("500 грн", callback_data="topup_500")],
        [InlineKeyboardButton("1000 грн", callback_data="topup_1000")],
        [InlineKeyboardButton("💸 Інша сума", callback_data="topup_custom")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if str(chat_id) == ADMIN_CHAT_ID:
        await update.message.reply_text(
            "🔧 **Панель адміністратора**\n\nОберіть дію:",
            reply_markup=get_admin_keyboard(),
            parse_mode='Markdown'
        )
        return

    USER_STATES[chat_id] = {'state': 'main', 'logged_in': False}

    await update.message.reply_text(
        "🎮 Вітаю в боті магазину ігор!\n\nОберіть дію:",
        reply_markup=get_main_keyboard()
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text

    if str(chat_id) == ADMIN_CHAT_ID:
        await handle_admin_message(update, context)
        return

    if chat_id not in USER_STATES:
        USER_STATES[chat_id] = {'state': 'main', 'logged_in': False}

    user_state = USER_STATES[chat_id]

    if text == "🚪 Вхід":
        USER_STATES[chat_id]['state'] = 'login_email'
        await update.message.reply_text("📧 Введіть ваш email:")

    elif text == "📝 Реєстрація":
        USER_STATES[chat_id]['state'] = 'register_email'
        await update.message.reply_text("📧 Введіть ваш email для реєстрації:")

    elif text == "💰 Поповнити баланс" and user_state.get('logged_in'):
        await update.message.reply_text(
            "💳 Оберіть суму для поповнення:",
            reply_markup=get_balance_keyboard()
        )

    elif text == "👤 Мій профіль" and user_state.get('logged_in'):
        users = load_users()
        user_email = user_state.get('email')
        if user_email and user_email in users:
            user_data = users[user_email]
            profile_text = f"""
👤 **Мій профіль**
📧 Email: {user_data['email']}
👤 Ім'я: {user_data['name']}
💰 Баланс: {user_data['balance']} грн
💸 Всього витрачено: {user_data['totalSpent']} грн
📅 Дата реєстрації: {user_data['registrationDate'][:10]}
🎮 Куплено ігор: {len(user_data['purchasedGames'])}
"""
            await update.message.reply_text(profile_text, parse_mode='Markdown')

    elif text == "🚪 Вийти":
        USER_STATES[chat_id] = {'state': 'main', 'logged_in': False}
        await update.message.reply_text(
            "👋 До побачення! Ви вийшли з системи.",
            reply_markup=get_main_keyboard()
        )

    elif user_state['state'] == 'login_email':
        await handle_login_email(update, context)

    elif user_state['state'] == 'login_password':
        await handle_login_password(update, context)

    elif user_state['state'] == 'register_email':
        await handle_register_email(update, context)

    elif user_state['state'] == 'register_password':
        await handle_register_password(update, context)

    elif user_state['state'] == 'register_name':
        await handle_register_name(update, context)

    elif user_state['state'] == 'custom_amount':
        await handle_custom_amount(update, context)

    elif text == "✅ Я поповнив" and user_state.get('pending_payment'):
        await handle_payment_confirmation(update, context)

async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    chat_id = update.effective_chat.id

    if chat_id not in USER_STATES:
        USER_STATES[chat_id] = {'state': 'admin_main'}

    admin_state = USER_STATES[chat_id]

    if text == "👥 Користувачі":
        users = load_users()
        if not users:
            await update.message.reply_text("👥 Користувачів поки немає.")
        else:
            await update.message.reply_text(
                f"👥 **Список користувачів** ({len(users)} осіб):",
                reply_markup=get_users_list_keyboard(users),
                parse_mode='Markdown'
            )

    elif text == "💰 Керування балансом":
        users = load_users()
        if not users:
            await update.message.reply_text("👥 Користувачів поки немає.")
        else:
            await update.message.reply_text(
                "💰 **Керування балансом користувачів**\n\nОберіть користувача:",
                reply_markup=get_users_list_keyboard(users),
                parse_mode='Markdown'
            )

    elif text == "📊 Статистика":
        users = load_users()
        total_users = len(users)
        total_balance = sum(user['balance'] for user in users.values())
        total_spent = sum(user['totalSpent'] for user in users.values())

        stats_text = f"""
📊 **Статистика системи**

👥 Всього користувачів: {total_users}
💰 Загальний баланс: {total_balance} грн
💸 Всього витрачено: {total_spent} грн
📅 Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}
"""
        await update.message.reply_text(stats_text, parse_mode='Markdown')

    elif admin_state.get('state') == 'change_balance_amount':
        await handle_admin_balance_change(update, context)

async def handle_login_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    email = update.message.text.strip()

    users = load_users()
    if email in users:
        USER_STATES[chat_id]['email'] = email
        USER_STATES[chat_id]['state'] = 'login_password'
        await update.message.reply_text("🔐 Введіть ваш пароль:")
    else:
        await update.message.reply_text("❌ Користувач з таким email не знайдений. Спробуйте ще раз або зареєструйтесь.")

async def handle_login_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    password = update.message.text.strip()

    users = load_users()
    email = USER_STATES[chat_id]['email']

    if users[email]['password'] == password:
        USER_STATES[chat_id]['logged_in'] = True
        USER_STATES[chat_id]['state'] = 'logged_in'

        user_data = users[email]
        await update.message.reply_text(
            f"✅ Вітаю, {user_data['name']}!\n💰 Ваш поточний баланс: {user_data['balance']} грн",
            reply_markup=get_user_keyboard()
        )
    else:
        await update.message.reply_text("❌ Невірний пароль. Спробуйте ще раз:")

async def handle_register_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    email = update.message.text.strip()

    if not is_valid_email(email):
        await update.message.reply_text("❌ Невірний формат email! Email повинен містити '@' та домен. Спробуйте ще раз:")
        return

    users = load_users()
    if email in users:
        await update.message.reply_text("❌ Користувач з таким email вже існує! Спробуйте інший email або увійдіть в систему.")
        USER_STATES[chat_id]['state'] = 'main'
    else:
        USER_STATES[chat_id]['email'] = email
        USER_STATES[chat_id]['state'] = 'register_password'
        await update.message.reply_text("🔐 Введіть пароль для нового акаунту (мінімум 6 символів):")

async def handle_register_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    password = update.message.text.strip()

    if not is_valid_password(password):
        await update.message.reply_text("❌ Пароль повинен містити мінімум 6 символів! Спробуйте ще раз:")
        return

    USER_STATES[chat_id]['password'] = password
    USER_STATES[chat_id]['state'] = 'register_name'
    await update.message.reply_text("👤 Введіть ваше ім'я:")

async def handle_register_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    name = update.message.text.strip()

    users = load_users()
    email = USER_STATES[chat_id]['email']
    password = USER_STATES[chat_id]['password']

    users[email] = {
        "email": email,
        "password": password,
        "name": name,
        "balance": 0,
        "registrationDate": datetime.now().isoformat(),
        "purchasedGames": [],
        "totalSpent": 0
    }

    save_users(users)

    USER_STATES[chat_id]['logged_in'] = True
    USER_STATES[chat_id]['state'] = 'logged_in'

    await update.message.reply_text(
        f"🎉 Реєстрація успішна! Вітаю, {name}!\n💰 Ваш поточний баланс: 0 грн\n\nТепер ви можете поповнити баланс та почати купувати ігри!",
        reply_markup=get_user_keyboard()
    )

async def handle_admin_callback_query(query, context):
    data = query.data
    if data.startswith("admin_confirm_") or data.startswith("admin_reject_"):
        parts = data.split("_")
        action = parts[1]
        user_chat_id = int(parts[2])
        amount = int(parts[3])

        users = load_users()

        if user_chat_id not in USER_STATES:
            await query.message.edit_text("❌ Користувач не знайдений.")
            return

        user_email = USER_STATES[user_chat_id]['email']

        if action == "confirm":
            if user_email in users:
                users[user_email]['balance'] += amount
                save_users(users)
                try:
                    await context.bot.send_message(
                        chat_id=user_chat_id,
                        text=f"✅ Ваш баланс поповнено на {amount} грн!\n💰 Поточний баланс: {users[user_email]['balance']} грн"
                    )
                except Exception as e:
                    logger.error(f"Помилка відправки повідомлення користувачу {user_chat_id}: {e}")
                await query.message.edit_text(f"✅ Поповнення підтверджено для {user_email} на суму {amount} грн")

        elif action == "reject":
            try:
                await context.bot.send_message(
                    chat_id=user_chat_id,
                    text=f"❌ Ваш запит на поповнення балансу на суму {amount} грн було відхилено.\nЗверніться до підтримки для уточнення деталей."
                )
            except Exception as e:
                logger.error(f"Помилка відправки повідомлення користувачу {user_chat_id}: {e}")
            await query.message.edit_text(f"❌ Поповнення відхилено для {user_email} на суму {amount} грн")

        if user_chat_id in USER_STATES and 'pending_payment' in USER_STATES[user_chat_id]:
            del USER_STATES[user_chat_id]['pending_payment']
        return

    if data.startswith("admin_users_page_"):
        page = int(data.split("_")[-1])
        users = load_users()
        await query.message.edit_text(
            f"👥 **Список користувачів** ({len(users)} осіб):",
            reply_markup=get_users_list_keyboard(users, page),
            parse_mode='Markdown'
        )

    elif data.startswith("admin_user_"):
        email = data.replace("admin_user_", "")
        users = load_users()
        if email in users:
            user_data = users[email]
            user_info = f"""
👤 **{user_data['name']}**
📧 Email: {email}
💰 Баланс: {user_data['balance']} грн
💸 Витрачено: {user_data['totalSpent']} грн
📅 Реєстрація: {user_data['registrationDate'][:10]}
🎮 Ігор куплено: {len(user_data['purchasedGames'])}
"""
            await query.message.edit_text(
                user_info,
                reply_markup=get_user_management_keyboard(email),
                parse_mode='Markdown'
            )

    elif data.startswith("admin_change_balance_"):
        email = data.replace("admin_change_balance_", "")
        USER_STATES[query.message.chat_id] = {
            'state': 'change_balance_amount',
            'target_email': email
        }
        await query.message.reply_text(
            f"💰 **Зміна балансу користувача**\n\nПоточний баланс: {load_users()[email]['balance']} грн\n\nВведіть нову суму балансу (або +100/-50 для зміни):",
            parse_mode='Markdown'
        )

    elif data.startswith("admin_user_info_"):
        email = data.replace("admin_user_info_", "")
        users = load_users()
        if email in users:
            user_data = users[email]
            detailed_info = f"""
👤 **Детальна інформація**

📧 Email: {email}
👤 Ім'я: {user_data['name']}
💰 Поточний баланс: {user_data['balance']} грн
💸 Всього витрачено: {user_data['totalSpent']} грн
📅 Дата реєстрації: {user_data['registrationDate']}

🎮 **Куплені ігри:** {len(user_data['purchasedGames'])}
"""
            for game in user_data['purchasedGames']:
                detailed_info += f"\n• {game['gameTitle']} - {game['price']} грн"

            back_keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=f"admin_user_{email}")]]
            await query.message.edit_text(
                detailed_info,
                reply_markup=InlineKeyboardMarkup(back_keyboard),
                parse_mode='Markdown'
            )

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    data = query.data

    if str(chat_id) == ADMIN_CHAT_ID:
        await handle_admin_callback_query(query, context)
        return

    if data.startswith("topup_"):
        if data == "topup_custom":
            USER_STATES[chat_id]['state'] = 'custom_amount'
            await query.message.reply_text("💰 Введіть суму для поповнення (в грн):")
        else:
            amount = int(data.split("_")[1])
            await initiate_payment(query, chat_id, amount)

async def handle_admin_balance_change(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text.strip()

    admin_state = USER_STATES[chat_id]
    target_email = admin_state['target_email']

    users = load_users()
    if target_email not in users:
        await update.message.reply_text("❌ Користувач не знайдений.")
        return

    try:
        current_balance = users[target_email]['balance']

        if text.startswith('+') or text.startswith('-'):
            change = int(text)
            new_balance = current_balance + change
        else:
            new_balance = int(text)

        if new_balance < 0:
            await update.message.reply_text("❌ Баланс не може бути від'ємним!")
            return

        old_balance = users[target_email]['balance']
        users[target_email]['balance'] = new_balance
        save_users(users)

        await update.message.reply_text(
            f"✅ **Баланс оновлено!**\n\n👤 Користувач: {users[target_email]['name']}\n📧 Email: {target_email}\n💰 Старий баланс: {old_balance} грн\n💰 Новий баланс: {new_balance} грн\n📊 Зміна: {new_balance - old_balance:+d} грн",
            reply_markup=get_admin_keyboard(),
            parse_mode='Markdown'
        )

        USER_STATES[chat_id]['state'] = 'admin_main'

    except ValueError:
        await update.message.reply_text("❌ Невірний формат! Введіть число або +/-число\nПриклади: 1000, +500, -200")

async def handle_custom_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    try:
        amount = int(update.message.text.strip())
        if amount <= 0:
            await update.message.reply_text("❌ Сума повинна бути більше 0. Введіть коректну суму:")
            return
        await initiate_payment(update, chat_id, amount)
    except ValueError:
        await update.message.reply_text("❌ Введіть коректну суму (тільки цифри):")

async def initiate_payment(update_or_query, chat_id, amount):
    USER_STATES[chat_id]['pending_payment'] = {
        'amount': amount,
        'timestamp': datetime.now().isoformat()
    }

    keyboard = [['✅ Я поповнив', '❌ Скасувати']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    message_text = f"💳 Поповнення на суму: {amount} грн\n\n{PAYMENT_DETAILS}"

    if hasattr(update_or_query, 'message'):
        await update_or_query.message.reply_text(message_text, reply_markup=reply_markup)
    else:
        await update_or_query.message.reply_text(message_text, reply_markup=reply_markup)

async def handle_payment_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_state = USER_STATES[chat_id]

    if not user_state.get('pending_payment'):
        await update.message.reply_text("❌ Немає активних запитів на поповнення.")
        return

    amount = user_state['pending_payment']['amount']
    email = user_state['email']

    admin_keyboard = [
        [InlineKeyboardButton("✅ Підтвердити", callback_data=f"admin_confirm_{chat_id}_{amount}")],
        [InlineKeyboardButton("❌ Відхилити", callback_data=f"admin_reject_{chat_id}_{amount}")]
    ]
    admin_markup = InlineKeyboardMarkup(admin_keyboard)

    admin_message = f"""
🔔 **Новий запит на поповнення**

👤 Користувач: {user_state['email']}
👤 Ім'я: {load_users()[user_state['email']]['name']}
💰 Сума: {amount} грн
📅 Час запиту: {user_state['pending_payment']['timestamp'][:19]}
💬 Chat ID: {chat_id}

⚡ Перевірте надходження коштів та підтвердіть або відхиліть операцію.
"""

    try:
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=admin_message,
            reply_markup=admin_markup,
            parse_mode='Markdown'
        )

        await update.message.reply_text(
            "✅ Ваш запит на поповнення відправлено на перевірку!\nОчікуйте підтвердження від адміністратора.",
            reply_markup=get_user_keyboard()
        )

        USER_STATES[chat_id]['state'] = 'logged_in'

    except Exception as e:
        logger.error(f"Помилка відправки повідомлення адміну: {e}")
        await update.message.reply_text(
            "❌ Виникла помилка при відправці запиту. Спробуйте пізніше.",
            reply_markup=get_user_keyboard()
        )

async def handle_admin_callback(query, context):
    data = query.data
    parts = data.split("_")

    if len(parts) < 4 or parts[0] != "admin":
        return

    action = parts[1]
    user_chat_id = int(parts[2])
    amount = int(parts[3])

    users = load_users()

    if user_chat_id not in USER_STATES:
        await query.message.edit_text("❌ Користувач не знайдений.")
        return

    user_email = USER_STATES[user_chat_id]['email']

    if action == "confirm":
        if user_email in users:
            users[user_email]['balance'] += amount
            save_users(users)
            try:
                await context.bot.send_message(
                    chat_id=user_chat_id,
                    text=f"✅ Ваш баланс поповнено на {amount} грн!\n💰 Поточний баланс: {users[user_email]['balance']} грн"
                )
            except Exception as e:
                logger.error(f"Помилка відправки повідомлення користувачу {user_chat_id}: {e}")
            await query.message.edit_text(f"✅ Поповнення підтверджено для {user_email} на суму {amount} грн")

    elif action == "reject":
        try:
            await context.bot.send_message(
                chat_id=user_chat_id,
                text=f"❌ Ваш запит на поповнення балансу на суму {amount} грн було відхилено.\nЗверніться до підтримки для уточнення деталей."
            )
        except Exception as e:
            logger.error(f"Помилка відправки повідомлення користувачу {user_chat_id}: {e}")
        await query.message.edit_text(f"❌ Поповнення відхилено для {user_email} на суму {amount} грн")

    if user_chat_id in USER_STATES and 'pending_payment' in USER_STATES[user_chat_id]:
        del USER_STATES[user_chat_id]['pending_payment']

def main():
    os.makedirs(os.path.dirname(USERS_FILE) if os.path.dirname(USERS_FILE) else '.', exist_ok=True)
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(handle_callback_query))

    print("🤖 Бот запущений!")
    application.run_polling()

if __name__ == '__main__':
    main()