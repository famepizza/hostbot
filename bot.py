import os
import random
import string
import asyncio
import logging
import json
from datetime import datetime
from typing import Dict, Optional
from dataclasses import dataclass, field

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from telegram.constants import ParseMode
from fake_useragent import UserAgent
import requests
import cloudscraper

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Константы для состояний
USERNAME, REASON, TARGET_ID, REPEATS, CUSTOM_MESSAGE = range(5)

# 👑 ВЛАДЕЛЕЦ
OWNER_ID = 940338901

# ========== РУССКИЕ ТЕКСТЫ ==========
TEXTS_RU = {
    # Главное меню
    'send_complaint': 'СНЕСТИ АККАУНТ',
    'stats': 'СТАТИСТИКА',
    'targets': 'ЦЕЛИ',
    'settings': 'НАСТРОЙКИ',
    'help': 'ПОМОЩЬ',
    'admin': 'АДМИН-ПАНЕЛЬ',
    'back': 'НАЗАД В МЕНЮ',
    'clear': 'ОЧИСТИТЬ ЦЕЛИ',
    'add': 'ДОБАВИТЬ',
    'remove': 'УДАЛИТЬ',
    
    # Настройки
    'language': 'ЯЗЫК',
    'method': 'МЕТОД ОТПРАВКИ',
    'delay': 'ЗАДЕРЖКА',
    'current_settings': 'ТЕКУЩИЕ НАСТРОЙКИ',
    'russian': 'РУССКИЙ',
    'english': 'АНГЛИЙСКИЙ',
    'fast': 'БЫСТРЫЙ',
    'normal': 'ОБЫЧНЫЙ',
    'slow': 'МЕДЛЕННЫЙ',
    'auto': 'АВТО',
    'cloudscraper': 'CLOUDSCRAPER',
    'advanced': 'ПРОДВИНУТЫЙ',
    'session': 'СЕССИЯ',
    'direct': 'ПРЯМОЙ',
    
    # Причины жалоб
    'reason_1': 'Докс / Слив данных',
    'reason_2': 'Спам',
    'reason_3': 'Мати / Оскорбления',
    'reason_4': 'Виртуальный номер',
    'reason_5': 'Премиум для спама',
    'reason_6': 'Взлом аккаунта',
    'reason_7': 'Мошенничество',
    'reason_8': 'Детская порнография',
    'reason_9': 'Свой текст',
    
    # Тексты жалоб
    'complaint_1': 'Здраствуйте. Аккаунт {username}, id {telegram_id}. Очень много и часто нарушает политику сервиса Телеграмм. А именно, оскорбляет, сливает личные данные юзеров. Продает различные услуги. Прозьба разобраться и наказать данный аккаунт.',
    'complaint_2': 'Здраствуйте, сидя на просторах сети телеграмм, я заметил пользователя который совершает спам-рассылки, мне и другим пользователям это очень не нравится. Его аккаунт: {username}, ID {telegram_id}. Огромная прозьба разобраться с этим и заблокировать данного пользователя. Заранее спасибо.',
    'complaint_3': 'Здраствуйте. Аккаунт {username}, id {telegram_id} оскорбляет меня и мою маму. Мне это очень не приятно, поэтому и пишу вам. Огромная прозьба разобраться и заблокировать данного пользователя т.к это нарушает политику сервиса. Блгаодарю',
    'complaint_4': 'Добрый день поддержка Telegram! Аккаунт {username}, {telegram_id} использует виртуальный номер купленный на сайте по активации номеров. Отношения к номеру он не имеет, номер никак к нему не относиться. Прошу разберитесь с этим. Заранее спасибо!',
    'complaint_5': 'Аккаунт {username}, {telegram_id} приобрёл премиум в вашем сервисе чтобы обходить наказания за спам и совершает спам-рассылки в личные сообщения пользователям и в чаты. Прошу проверить информацию!',
    'complaint_6': 'Здравствуйте, я утерял свой телеграм-аккаунт путем взлома. Я попался на фишинговую ссылку, и теперь на моем аккаунте сидит какой-то человек. Он установил облачный пароль, так что я не могу зайти в свой аккаунт и прошу о помощи. Мой юзернейм — {username}, а мой айди, если злоумышленник поменял юзернейм — {telegram_id}. Пожалуйста, перезагрузите сессии или удалите этот аккаунт, так как у меня там очень много важных данных.',
    'complaint_7': 'Здравствуйте! Пользователь {username}, ID {telegram_id} занимается мошенничеством. Обманывает людей, просит деньги под ложными предлогами. Прошу заблокировать данного пользователя.',
    'complaint_8': 'Срочное сообщение! Пользователь {username}, ID {telegram_id} распространяет запрещенный контент с несовершеннолетними. Прошу немедленно заблокировать!',
    
    # Разные тексты
    'welcome': 'ДОБРО ПОЖАЛОВАТЬ',
    'your_stats': 'Твоя статистика',
    'times_used': 'раз',
    'complaints_sent': 'Отправлено жалоб',
    'successful': 'Успешно',
    'failed': 'Ошибок',
    'success_rate': 'Успешность',
    'last_targets': 'Последние цели',
    'no_targets': 'Пока нет целей',
    'enter_username': 'Введите username цели (например: @durov)',
    'enter_id': 'Введите ID цели (число)',
    'enter_count': 'Сколько жалоб? (1-100)',
    'enter_custom': 'Введите свой текст жалобы',
    'starting': 'НАЧИНАЮ ОТПРАВКУ',
    'sending': 'ОТПРАВКА',
    'completed': 'ОТПРАВКА ЗАВЕРШЕНА',
    'success': 'УСПЕШНО',
    'failed_status': 'НЕУДАЧНО',
    'target': 'Цель',
    'id': 'ID',
    'method_used': 'Метод',
    'delay_mode': 'Задержка',
    'time_passed': 'Прошло',
    'time_left': 'Осталось',
    'again': 'ЕЩЁ РАЗ',
    'protected': 'Этот пользователь защищен от сноса!',
    'error_number': 'Введите число от 1 до 100!',
    'error_id': 'ID должен быть числом!',
    'blocked': 'Вы заблокированы в боте!',
    'no_rights': 'У вас нет прав!',
    'admin_added': 'Админ добавлен!',
    'admin_removed': 'Админ удален!',
    'targets_cleared': 'Список целей очищен!',
    'language_changed': 'Язык изменён!',
    'method_changed': 'Метод отправки изменён!',
    'delay_changed': 'Режим задержки изменён!',
}

# ========== АНГЛИЙСКИЕ ТЕКСТЫ ==========
TEXTS_EN = {
    # Main menu
    'send_complaint': 'SEND COMPLAINT',
    'stats': 'STATISTICS',
    'targets': 'TARGETS',
    'settings': 'SETTINGS',
    'help': 'HELP',
    'admin': 'ADMIN PANEL',
    'back': 'BACK TO MENU',
    'clear': 'CLEAR TARGETS',
    'add': 'ADD',
    'remove': 'REMOVE',
    
    # Settings
    'language': 'LANGUAGE',
    'method': 'SEND METHOD',
    'delay': 'DELAY',
    'current_settings': 'CURRENT SETTINGS',
    'russian': 'RUSSIAN',
    'english': 'ENGLISH',
    'fast': 'FAST',
    'normal': 'NORMAL',
    'slow': 'SLOW',
    'auto': 'AUTO',
    'cloudscraper': 'CLOUDSCRAPER',
    'advanced': 'ADVANCED',
    'session': 'SESSION',
    'direct': 'DIRECT',
    
    # Complaint reasons
    'reason_1': 'Dox / Data leak',
    'reason_2': 'Spam',
    'reason_3': 'Insults / Offensive',
    'reason_4': 'Virtual number',
    'reason_5': 'Premium for spam',
    'reason_6': 'Account hack',
    'reason_7': 'Fraud',
    'reason_8': 'Child pornography',
    'reason_9': 'Custom text',
    
    # Complaint texts
    'complaint_1': 'Hello. Account {username}, id {telegram_id} frequently violates Telegram policy. He insults, leaks personal data. Sells various services. Please investigate and punish this account.',
    'complaint_2': 'Hello, I noticed a user who sends spam messages to me and other users. His account: {username}, ID {telegram_id}. Please investigate and block this user. Thank you.',
    'complaint_3': 'Hello. Account {username}, id {telegram_id} insults me and my family. This is very unpleasant. Please investigate and block this user as it violates service policy.',
    'complaint_4': 'Good day Telegram support! Account {username}, {telegram_id} uses a virtual number purchased on activation sites. He has no relation to this number. Please investigate. Thank you!',
    'complaint_5': 'Account {username}, {telegram_id} bought premium to bypass spam restrictions and sends spam messages to users and chats. Please check this information!',
    'complaint_6': 'Hello, I lost my Telegram account due to hacking. I clicked on a phishing link, and now someone else is using my account. He set a cloud password, so I cannot access my account. My username is {username}, ID {telegram_id}. Please help me recover it.',
    'complaint_7': 'Hello! User {username}, ID {telegram_id} is engaged in fraud. He deceives people, asks for money under false pretenses. Please block this user.',
    'complaint_8': 'Urgent message! User {username}, ID {telegram_id} distributes prohibited content with minors. Please block immediately!',
    
    # Various texts
    'welcome': 'WELCOME',
    'your_stats': 'Your statistics',
    'times_used': 'times',
    'complaints_sent': 'Complaints sent',
    'successful': 'Successful',
    'failed': 'Failed',
    'success_rate': 'Success rate',
    'last_targets': 'Last targets',
    'no_targets': 'No targets yet',
    'enter_username': 'Enter target username (example: @durov)',
    'enter_id': 'Enter target ID (number)',
    'enter_count': 'How many complaints? (1-100)',
    'enter_custom': 'Enter your complaint text',
    'starting': 'STARTING',
    'sending': 'SENDING',
    'completed': 'SENDING COMPLETED',
    'success': 'SUCCESS',
    'failed_status': 'FAILED',
    'target': 'Target',
    'id': 'ID',
    'method_used': 'Method',
    'delay_mode': 'Delay',
    'time_passed': 'Passed',
    'time_left': 'Left',
    'again': 'AGAIN',
    'protected': 'This user is protected!',
    'error_number': 'Enter number from 1 to 100!',
    'error_id': 'ID must be a number!',
    'blocked': 'You are blocked!',
    'no_rights': 'Access denied!',
    'admin_added': 'Admin added!',
    'admin_removed': 'Admin removed!',
    'targets_cleared': 'Targets cleared!',
    'language_changed': 'Language changed!',
    'method_changed': 'Send method changed!',
    'delay_changed': 'Delay mode changed!',
}

# Эмодзи
EMOJI = {
    'success': '✅', 'fail': '❌', 'wait': '⏳', 'rocket': '🚀',
    'fire': '🔥', 'target': '🎯', 'stats': '📊', 'settings': '⚙️',
    'help': 'ℹ️', 'warning': '⚠️', 'crown': '👑', 'admin': '👮',
    'web': '🌐', 'add': '➕', 'remove': '➖', 'list': '📋', 
    'back': '◀️', 'lock': '🔒', 'unlock': '🔓', 'chart': '📈',
    'star': '⭐', 'language': '🔤', 'speed': '⚡', 'method': '🔄',
    'diamond': '💎', 'shield': '🛡', 'skull': '💀', 'money': '💰',
    'gift': '🎁', 'rainbow': '🌈', 'lightning': '⚡'
}

# Защищенные пользователи
PROTECTED_USERS = ["@turrondev", "turrondev", "telegram"]


@dataclass
class ComplaintData:
    username: str = ""
    reason_code: str = ""
    target_id: str = ""
    repeats: int = 1
    custom_message: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    complaints_sent: int = 0
    failed_attempts: int = 0
    total_time: float = 0.0


class Database:
    def __init__(self, filename='bot_data.json'):
        self.filename = filename
        self.data = self.load()
        self._ensure_structure()
    
    def _ensure_structure(self):
        if 'users' not in self.data:
            self.data['users'] = {}
        if 'admins' not in self.data:
            self.data['admins'] = [OWNER_ID]
        if 'blacklist' not in self.data:
            self.data['blacklist'] = []
        if 'settings' not in self.data:
            self.data['settings'] = {}
        self.save()
    
    def load(self):
        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {'users': {}, 'admins': [OWNER_ID], 'blacklist': [], 'settings': {}}
    
    def save(self):
        with open(self.filename, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False, default=str)
    
    def is_owner(self, user_id: int) -> bool:
        return user_id == OWNER_ID
    
    def is_admin(self, user_id: int) -> bool:
        return user_id == OWNER_ID or user_id in self.data.get('admins', [])
    
    def get_admins(self) -> list:
        return self.data.get('admins', [])
    
    def add_admin(self, user_id: int) -> bool:
        if user_id == OWNER_ID:
            return False
        if user_id not in self.data['admins']:
            self.data['admins'].append(user_id)
            self.save()
            return True
        return False
    
    def remove_admin(self, user_id: int) -> bool:
        if user_id in self.data['admins'] and user_id != OWNER_ID:
            self.data['admins'].remove(user_id)
            self.save()
            return True
        return False
    
    def get_user(self, user_id: int) -> dict:
        user_id = str(user_id)
        if user_id not in self.data['users']:
            self.data['users'][user_id] = {
                'total_uses': 0,
                'total_complaints': 0,
                'successful': 0,
                'failed': 0,
                'joined': str(datetime.now()),
                'last_seen': str(datetime.now()),
                'targets': []
            }
            self.save()
        return self.data['users'][user_id]
    
    def get_user_settings(self, user_id: int) -> dict:
        user_id = str(user_id)
        if user_id not in self.data['settings']:
            self.data['settings'][user_id] = {
                'language': 'ru',
                'method': 'auto',
                'delay': 'normal'
            }
            self.save()
        return self.data['settings'][user_id]
    
    def update_user_settings(self, user_id: int, **kwargs):
        user_id = str(user_id)
        if user_id not in self.data['settings']:
            self.data['settings'][user_id] = {}
        self.data['settings'][user_id].update(kwargs)
        self.save()
    
    def update_user(self, user_id: int, **kwargs):
        user_id = str(user_id)
        user = self.get_user(user_id)
        user.update(kwargs)
        user['last_seen'] = str(datetime.now())
        self.save()
    
    def is_blacklisted(self, user_id: int) -> bool:
        return str(user_id) in self.data.get('blacklist', [])
    
    def increment_complaints(self, user_id: int, success: bool = True):
        user = self.get_user(user_id)
        user['total_complaints'] += 1
        if success:
            user['successful'] += 1
        else:
            user['failed'] += 1
        self.save()
    
    def add_target(self, user_id: int, target: str):
        user = self.get_user(user_id)
        if 'targets' not in user:
            user['targets'] = []
        user['targets'].append(target)
        if len(user['targets']) > 50:
            user['targets'] = user['targets'][-50:]
        self.save()


class ComplaintSender:
    def __init__(self):
        self.scraper = cloudscraper.create_scraper()
        self.session = requests.Session()
    
    def send_complaint(self, username: str, target_id: str, message_text: str, method: str = "auto") -> bool:
        data = self._generate_fake_data()
        
        if method == "auto":
            methods = [self._send_cloudscraper, self._send_advanced, self._send_session, self._send_direct]
            for m in methods:
                try:
                    if m(username, target_id, message_text, data):
                        return True
                except:
                    continue
            return False
        elif method == "cloudscraper":
            return self._send_cloudscraper(username, target_id, message_text, data)
        elif method == "advanced":
            return self._send_advanced(username, target_id, message_text, data)
        elif method == "session":
            return self._send_session(username, target_id, message_text, data)
        elif method == "direct":
            return self._send_direct(username, target_id, message_text, data)
        return False
    
    def _generate_fake_data(self) -> dict:
        username = ''.join(random.choices(string.ascii_lowercase, k=8))
        phone = f"+7{''.join(random.choices('0123456789', k=10))}"
        email = f"{username}@gmail.com"
        return {'phone': phone, 'email': email}
    
    def _get_headers(self) -> dict:
        return {'User-Agent': UserAgent().random}
    
    def _send_cloudscraper(self, username, target_id, message_text, data):
        payload = {'text': message_text, 'number': data['phone'], 'email': data['email']}
        response = self.scraper.post('https://telegram.org/support', headers=self._get_headers(), data=payload, timeout=10)
        return response.status_code == 200
    
    def _send_advanced(self, username, target_id, message_text, data):
        session = requests.Session()
        session.get('https://telegram.org', timeout=5)
        payload = {'text': message_text, 'number': data['phone'], 'email': data['email']}
        response = session.post('https://telegram.org/support', headers=self._get_headers(), data=payload, timeout=10)
        return response.status_code == 200
    
    def _send_session(self, username, target_id, message_text, data):
        payload = {'text': message_text, 'number': data['phone'], 'email': data['email']}
        response = self.session.post('https://telegram.org/support', headers=self._get_headers(), data=payload, timeout=10)
        return response.status_code == 200
    
    def _send_direct(self, username, target_id, message_text, data):
        headers = {'User-Agent': UserAgent().random, 'Content-Type': 'application/x-www-form-urlencoded'}
        payload = {'text': message_text, 'number': data['phone'], 'email': data['email']}
        response = requests.post('https://telegram.org/support', headers=headers, data=payload, timeout=10)
        return response.status_code == 200


class ComplaintBot:
    def __init__(self, token: str):
        self.token = token
        self.sender = ComplaintSender()
        self.db = Database()
        self.user_complaints: Dict[int, ComplaintData] = {}
        self.start_time = datetime.now()
    
    def get_texts(self, user_id: int) -> dict:
        """Возвращает тексты на нужном языке"""
        settings = self.db.get_user_settings(user_id)
        return TEXTS_EN if settings.get('language') == 'en' else TEXTS_RU
    
    def get_complaint_text(self, user_id: int, reason_code: str, username: str, target_id: str, custom: str = "") -> str:
        """Возвращает текст жалобы на нужном языке"""
        texts = self.get_texts(user_id)
        
        if reason_code == "9" and custom:
            return custom
        
        complaint_key = f'complaint_{reason_code}'
        if complaint_key in texts:
            return texts[complaint_key].format(username=username, telegram_id=target_id)
        return "Complaint text"
    
    def get_reason_name(self, user_id: int, reason_code: str) -> str:
        """Возвращает название причины на нужном языке"""
        texts = self.get_texts(user_id)
        reason_key = f'reason_{reason_code}'
        return texts.get(reason_key, f"Reason {reason_code}")
    
    def get_delay(self, user_id: int) -> float:
        """Возвращает задержку в зависимости от настройки"""
        settings = self.db.get_user_settings(user_id)
        mode = settings.get('delay', 'normal')
        if mode == 'fast':
            return random.uniform(1, 2)
        elif mode == 'slow':
            return random.uniform(4, 6)
        else:
            return random.uniform(2, 4)
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_id = user.id
        
        # Обновляем статистику
        user_data = self.db.get_user(user_id)
        user_data['total_uses'] += 1
        self.db.save()
        
        texts = self.get_texts(user_id)
        
        # Ссылка на мини-апп
        mini_app_url = "https://vodanieejaroslav-cell.github.io/truepizza-app/"
        
        # Создаем клавиатуру
        keyboard = [
            [InlineKeyboardButton(f"{EMOJI['fire']} {texts['send_complaint']}", callback_data="new_complaint")],
            [
                InlineKeyboardButton(f"{EMOJI['stats']} {texts['stats']}", callback_data="stats"),
                InlineKeyboardButton(f"{EMOJI['target']} {texts['targets']}", callback_data="targets")
            ],
            [
                InlineKeyboardButton(f"{EMOJI['web']} МИНИ-ПРИЛОЖЕНИЕ", web_app=WebAppInfo(url=mini_app_url)),
                InlineKeyboardButton(f"{EMOJI['settings']} {texts['settings']}", callback_data="settings")
            ],
            [InlineKeyboardButton(f"{EMOJI['help']} {texts['help']}", callback_data="help")]
        ]
        
        # Админ-панель для админов
        if self.db.is_admin(user_id):
            keyboard.append([InlineKeyboardButton(f"{EMOJI['admin']} {texts['admin']}", callback_data="admin_panel")])
        
        # Текст приветствия
        welcome_text = (
            f"{EMOJI['fire']}{EMOJI['fire']}{EMOJI['fire']} **TRUE PIZZA BOT** {EMOJI['fire']}{EMOJI['fire']}{EMOJI['fire']}\n\n"
            f"👋 Привет, **{user.first_name}**!\n\n"
            f"📊 **{texts['your_stats']}:**\n"
            f"├ {texts['times_used']}: {user_data['total_uses']}\n"
            f"├ {texts['complaints_sent']}: {user_data['total_complaints']}\n"
            f"├ {EMOJI['success']} {texts['successful']}: {user_data['successful']}\n"
            f"├ {EMOJI['fail']} {texts['failed']}: {user_data['failed']}\n"
            f"└ {EMOJI['chart']} {texts['success_rate']}: {self._get_success_rate(user_id)}%\n\n"
            f"{EMOJI['rocket']} **{texts['welcome']}**"
        )
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def button_click(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = update.effective_user.id
        texts = self.get_texts(user_id)
        
        # Проверка на черный список
        if self.db.is_blacklisted(user_id) and not self.db.is_admin(user_id):
            await query.message.reply_text(f"{EMOJI['warning']} {texts['blocked']}")
            return
        
        # Обработка callback_data
        if query.data == "new_complaint":
            context.user_data['state'] = USERNAME
            await query.message.reply_text(f"{EMOJI['target']} {texts['enter_username']}")
        
        elif query.data == "stats":
            await self._show_stats(query, context, user_id)
        
        elif query.data == "targets":
            await self._show_targets(query, context, user_id)
        
        elif query.data == "settings":
            await self._show_settings(query, context, user_id)
        
        elif query.data == "help":
            await self._show_help(query, context, user_id)
        
        elif query.data == "admin_panel":
            await self._show_admin_panel(query, context, user_id)
        
        elif query.data == "admin_list":
            await self._show_admin_list(query, context, user_id)
        
        elif query.data == "admin_add":
            context.user_data['admin_action'] = 'add'
            context.user_data['state'] = 'admin_input'
            await query.message.reply_text(f"{EMOJI['add']} {texts['add']} ID:")
        
        elif query.data == "admin_remove":
            context.user_data['admin_action'] = 'remove'
            context.user_data['state'] = 'admin_input'
            await query.message.reply_text(f"{EMOJI['remove']} {texts['remove']} ID:")
        
        elif query.data == "clear_targets":
            self.db.get_user(user_id)['targets'] = []
            self.db.save()
            await query.message.reply_text(f"{EMOJI['success']} {texts['targets_cleared']}")
            await self._show_targets(query, context, user_id)
        
        elif query.data == "settings_language":
            await self._show_language_settings(query, context, user_id)
        
        elif query.data == "settings_method":
            await self._show_method_settings(query, context, user_id)
        
        elif query.data == "settings_delay":
            await self._show_delay_settings(query, context, user_id)
        
        elif query.data.startswith("lang_"):
            lang = query.data.replace("lang_", "")
            self.db.update_user_settings(user_id, language=lang)
            new_texts = self.get_texts(user_id)
            await query.message.reply_text(f"{EMOJI['success']} {new_texts['language_changed']}")
            await self._show_settings(query, context, user_id)
        
        elif query.data.startswith("method_"):
            method = query.data.replace("method_", "")
            self.db.update_user_settings(user_id, method=method)
            new_texts = self.get_texts(user_id)
            await query.message.reply_text(f"{EMOJI['success']} {new_texts['method_changed']}")
            await self._show_settings(query, context, user_id)
        
        elif query.data.startswith("delay_"):
            delay = query.data.replace("delay_", "")
            self.db.update_user_settings(user_id, delay=delay)
            new_texts = self.get_texts(user_id)
            await query.message.reply_text(f"{EMOJI['success']} {new_texts['delay_changed']}")
            await self._show_settings(query, context, user_id)
        
        elif query.data == "back_to_main":
            # Возвращаемся в главное меню
            await self.start(query.message, context)
        
        elif query.data.startswith("reason_"):
            reason_code = query.data.replace("reason_", "")
            context.user_data['reason'] = reason_code
            if reason_code == "9":
                context.user_data['state'] = CUSTOM_MESSAGE
                await query.message.reply_text(f"{EMOJI['gift']} {texts['enter_custom']}:")
            else:
                context.user_data['state'] = TARGET_ID
                await query.message.reply_text(f"{EMOJI['target']} {texts['enter_id']}")
    
    async def _show_stats(self, query, context, user_id):
        texts = self.get_texts(user_id)
        user_data = self.db.get_user(user_id)
        joined = datetime.fromisoformat(user_data['joined'])
        days = (datetime.now() - joined).days
        
        text = (
            f"{EMOJI['stats']} **{texts['stats']}**\n\n"
            f"👤 {query.from_user.first_name}\n"
            f"🆔 `{user_id}`\n"
            f"📅 {days} days\n\n"
            f"📊 **{texts['your_stats']}:**\n"
            f"├ {texts['times_used']}: {user_data['total_uses']}\n"
            f"├ {texts['complaints_sent']}: {user_data['total_complaints']}\n"
            f"├ {EMOJI['success']} {texts['successful']}: {user_data['successful']}\n"
            f"├ {EMOJI['fail']} {texts['failed']}: {user_data['failed']}\n"
            f"└ {EMOJI['chart']} {texts['success_rate']}: {self._get_success_rate(user_id)}%\n\n"
            f"🎯 **{texts['last_targets']}:**\n"
        )
        
        targets = user_data.get('targets', [])[-5:]
        text += "\n".join([f"└ {t}" for t in targets]) if targets else f"└ {texts['no_targets']}"
        
        keyboard = [[InlineKeyboardButton(f"{EMOJI['back']} {texts['back']}", callback_data="back_to_main")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
    
    async def _show_targets(self, query, context, user_id):
        texts = self.get_texts(user_id)
        targets = self.db.get_user(user_id).get('targets', [])
        
        if not targets:
            text = f"{EMOJI['warning']} {texts['no_targets']}"
        else:
            target_stats = {}
            for t in targets:
                target_stats[t] = target_stats.get(t, 0) + 1
            sorted_targets = sorted(target_stats.items(), key=lambda x: x[1], reverse=True)
            
            text = f"{EMOJI['target']} **{texts['targets']}**\n\n"
            for i, (target, count) in enumerate(sorted_targets[:10], 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "└"
                text += f"{medal} {target}: {count}\n"
        
        keyboard = [
            [InlineKeyboardButton(f"{EMOJI['fail']} {texts['clear']}", callback_data="clear_targets")],
            [InlineKeyboardButton(f"{EMOJI['back']} {texts['back']}", callback_data="back_to_main")]
        ]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
    
    async def _show_settings(self, query, context, user_id):
        texts = self.get_texts(user_id)
        settings = self.db.get_user_settings(user_id)
        
        lang = f"{'🇷🇺' if settings.get('language') == 'ru' else '🇬🇧'} {texts['russian'] if settings.get('language') == 'ru' else texts['english']}"
        method_map = {'auto': texts['auto'], 'cloudscraper': texts['cloudscraper'], 
                     'advanced': texts['advanced'], 'session': texts['session'], 'direct': texts['direct']}
        delay_map = {'fast': texts['fast'], 'normal': texts['normal'], 'slow': texts['slow']}
        
        text = (
            f"{EMOJI['settings']} **{texts['settings']}**\n\n"
            f"**{texts['current_settings']}:**\n"
            f"{EMOJI['language']} {texts['language']}: {lang}\n"
            f"{EMOJI['method']} {texts['method']}: {method_map.get(settings.get('method'), texts['auto'])}\n"
            f"{EMOJI['speed']} {texts['delay']}: {delay_map.get(settings.get('delay'), texts['normal'])}\n\n"
            f"{EMOJI['rocket']} **{texts['welcome']}:**"
        )
        
        keyboard = [
            [InlineKeyboardButton(f"{EMOJI['language']} {texts['language']}", callback_data="settings_language")],
            [InlineKeyboardButton(f"{EMOJI['method']} {texts['method']}", callback_data="settings_method")],
            [InlineKeyboardButton(f"{EMOJI['speed']} {texts['delay']}", callback_data="settings_delay")],
            [InlineKeyboardButton(f"{EMOJI['back']} {texts['back']}", callback_data="back_to_main")]
        ]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
    
    async def _show_language_settings(self, query, context, user_id):
        texts = self.get_texts(user_id)
        keyboard = [
            [InlineKeyboardButton(f"🇷🇺 {texts['russian']}", callback_data="lang_ru")],
            [InlineKeyboardButton(f"🇬🇧 {texts['english']}", callback_data="lang_en")],
            [InlineKeyboardButton(f"{EMOJI['back']} {texts['back']}", callback_data="settings")]
        ]
        await query.message.edit_text(f"{EMOJI['language']} **{texts['language']}**", reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def _show_method_settings(self, query, context, user_id):
        texts = self.get_texts(user_id)
        keyboard = [
            [InlineKeyboardButton(f"🤖 {texts['auto']}", callback_data="method_auto")],
            [InlineKeyboardButton(f"🛡 {texts['cloudscraper']}", callback_data="method_cloudscraper")],
            [InlineKeyboardButton(f"⚙️ {texts['advanced']}", callback_data="method_advanced")],
            [InlineKeyboardButton(f"🔄 {texts['session']}", callback_data="method_session")],
            [InlineKeyboardButton(f"📨 {texts['direct']}", callback_data="method_direct")],
            [InlineKeyboardButton(f"{EMOJI['back']} {texts['back']}", callback_data="settings")]
        ]
        await query.message.edit_text(f"{EMOJI['method']} **{texts['method']}**", reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def _show_delay_settings(self, query, context, user_id):
        texts = self.get_texts(user_id)
        keyboard = [
            [InlineKeyboardButton(f"⚡ {texts['fast']}", callback_data="delay_fast")],
            [InlineKeyboardButton(f"⏱ {texts['normal']}", callback_data="delay_normal")],
            [InlineKeyboardButton(f"🐢 {texts['slow']}", callback_data="delay_slow")],
            [InlineKeyboardButton(f"{EMOJI['back']} {texts['back']}", callback_data="settings")]
        ]
        await query.message.edit_text(f"{EMOJI['speed']} **{texts['delay']}**", reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def _show_help(self, query, context, user_id):
        texts = self.get_texts(user_id)
        text = (
            f"{EMOJI['help']} **{texts['help']}**\n\n"
            f"1️⃣ {texts['send_complaint']}\n"
            f"2️⃣ {texts['enter_username']}\n"
            f"3️⃣ {texts['reason_1']}...\n"
            f"4️⃣ {texts['enter_id']}\n"
            f"5️⃣ {texts['enter_count']}\n\n"
            f"⚙️ **{texts['settings']}:**\n"
            f"├ {EMOJI['language']} {texts['language']}\n"
            f"├ {EMOJI['method']} {texts['method']}\n"
            f"└ {EMOJI['speed']} {texts['delay']}"
        )
        keyboard = [[InlineKeyboardButton(f"{EMOJI['back']} {texts['back']}", callback_data="back_to_main")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
    
    async def _show_admin_panel(self, query, context, user_id):
        texts = self.get_texts(user_id)
        if not self.db.is_admin(user_id):
            await query.message.reply_text(f"{EMOJI['warning']} {texts['no_rights']}")
            return
        
        admins = self.db.get_admins()
        uptime = datetime.now() - self.start_time
        hours = uptime.seconds // 3600
        minutes = (uptime.seconds % 3600) // 60
        
        text = (
            f"{EMOJI['admin']} **{texts['admin']}**\n\n"
            f"👥 Users: {len(self.db.data['users'])}\n"
            f"👮 Admins: {len(admins)}\n"
            f"⏱ Uptime: {hours}h {minutes}m\n\n"
            f"{EMOJI['rocket']} **{texts['welcome']}:**"
        )
        
        keyboard = [
            [InlineKeyboardButton(f"{EMOJI['list']} {texts['admin']}", callback_data="admin_list")],
            [InlineKeyboardButton(f"{EMOJI['add']} {texts['add']}", callback_data="admin_add")],
            [InlineKeyboardButton(f"{EMOJI['remove']} {texts['remove']}", callback_data="admin_remove")],
            [InlineKeyboardButton(f"{EMOJI['back']} {texts['back']}", callback_data="back_to_main")]
        ]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
    
    async def _show_admin_list(self, query, context, user_id):
        texts = self.get_texts(user_id)
        if not self.db.is_admin(user_id):
            return
        
        admins = self.db.get_admins()
        text = f"{EMOJI['list']} **{texts['admin']}**\n\n"
        for i, admin_id in enumerate(admins, 1):
            prefix = "👑" if admin_id == OWNER_ID else "👮"
            text += f"{prefix} {admin_id}\n"
        
        keyboard = [[InlineKeyboardButton(f"{EMOJI['back']} {texts['back']}", callback_data="admin_panel")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        text = update.message.text.strip()
        state = context.user_data.get('state')
        texts = self.get_texts(user_id)
        
        # Проверка на черный список
        if self.db.is_blacklisted(user_id) and not self.db.is_admin(user_id):
            await update.message.reply_text(f"{EMOJI['warning']} {texts['blocked']}")
            return
        
        # Обработка админского ввода
        if state == 'admin_input' and 'admin_action' in context.user_data:
            if not text.isdigit():
                await update.message.reply_text(f"{EMOJI['fail']} {texts['error_id']}")
                return
            
            target_id = int(text)
            action = context.user_data['admin_action']
            
            if action == 'add':
                if self.db.add_admin(target_id):
                    await update.message.reply_text(f"{EMOJI['success']} {texts['admin_added']}")
                else:
                    await update.message.reply_text(f"{EMOJI['fail']} {texts['no_rights']}")
            elif action == 'remove':
                if self.db.remove_admin(target_id):
                    await update.message.reply_text(f"{EMOJI['success']} {texts['admin_removed']}")
                else:
                    await update.message.reply_text(f"{EMOJI['fail']} {texts['no_rights']}")
            
            del context.user_data['admin_action']
            context.user_data['state'] = None
            return
        
        # Обработка обычных состояний
        if state == USERNAME:
            if text in PROTECTED_USERS:
                await update.message.reply_text(f"{EMOJI['warning']} {texts['protected']}")
                context.user_data['state'] = None
                return
            
            context.user_data['username'] = text
            await self._show_reasons(update, context)
        
        elif state == TARGET_ID:
            if not text.isdigit():
                await update.message.reply_text(f"{EMOJI['fail']} {texts['error_id']}")
                return
            context.user_data['target_id'] = text
            context.user_data['state'] = REPEATS
            await update.message.reply_text(f"{EMOJI['rocket']} {texts['enter_count']}")
        
        elif state == REPEATS:
            if not text.isdigit() or int(text) < 1 or int(text) > 100:
                await update.message.reply_text(f"{EMOJI['fail']} {texts['error_number']}")
                return
            
            repeats = int(text)
            await self._process_complaint(update, context, repeats)
            context.user_data['state'] = None
        
        elif state == CUSTOM_MESSAGE:
            context.user_data['custom_message'] = text
            context.user_data['state'] = TARGET_ID
            await update.message.reply_text(f"{EMOJI['target']} {texts['enter_id']}")
        
        else:
            await update.message.reply_text(f"{EMOJI['help']} /start")
    
    async def _show_reasons(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        texts = self.get_texts(user_id)
        
        keyboard = []
        row = []
        for i in range(1, 10):
            reason_text = texts.get(f'reason_{i}', f'Reason {i}')
            callback = f"reason_{i}"
            row.append(InlineKeyboardButton(f"{i}", callback_data=callback))
            if len(row) == 3:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        
        reason_list = "\n".join([f"{i}. {texts.get(f'reason_{i}', '')}" for i in range(1, 10)])
        
        await update.message.reply_text(
            f"{EMOJI['fire']} **{texts['send_complaint']}**\n\n{reason_list}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def _process_complaint(self, update: Update, context: ContextTypes.DEFAULT_TYPE, repeats: int):
        user_id = update.effective_user.id
        texts = self.get_texts(user_id)
        settings = self.db.get_user_settings(user_id)
        
        username = context.user_data.get('username', '')
        reason_code = context.user_data.get('reason', '1')
        target_id = context.user_data.get('target_id', '')
        custom = context.user_data.get('custom_message', '')
        
        reason_name = self.get_reason_name(user_id, reason_code)
        message_text = self.get_complaint_text(user_id, reason_code, username, target_id, custom)
        
        # Сообщение о начале
        await update.message.reply_text(
            f"{EMOJI['rocket']} **{texts['starting']} {repeats} {texts['complaints_sent']}**\n\n"
            f"🎯 {texts['target']}: {username}\n"
            f"🆔 {texts['id']}: {target_id}\n"
            f"📋 {texts['reason_1'][:20]}: {reason_name[:20]}...\n"
            f"⚙️ {texts['method_used']}: {settings.get('method', 'auto')}\n"
            f"⚡ {texts['delay_mode']}: {settings.get('delay', 'normal')}"
        )
        
        # Прогресс
        progress_msg = await update.message.reply_text(f"{EMOJI['wait']} {texts['starting']}...")
        
        start_time = datetime.now()
        success = 0
        failed = 0
        
        for i in range(repeats):
            try:
                if self.sender.send_complaint(username, target_id, message_text, settings.get('method', 'auto')):
                    success += 1
                    self.db.increment_complaints(user_id, success=True)
                else:
                    failed += 1
                    self.db.increment_complaints(user_id, success=False)
                
                self.db.add_target(user_id, username)
                
                # Прогресс
                elapsed = (datetime.now() - start_time).seconds
                remaining = int((repeats - i - 1) * self.get_delay(user_id))
                percent = int((i + 1) / repeats * 100)
                bar = "█" * (percent // 5) + "░" * (20 - percent // 5)
                
                await progress_msg.edit_text(
                    f"{EMOJI['rocket']} **{texts['sending']}...**\n\n"
                    f"`[{bar}]` {percent}%\n"
                    f"{EMOJI['success']} {success} | {EMOJI['fail']} {failed} | {i+1}/{repeats}\n"
                    f"⏱ {texts['time_passed']}: {elapsed}s | ⏳ {texts['time_left']}: ~{remaining}s"
                )
                
                await asyncio.sleep(self.get_delay(user_id))
                
            except Exception as e:
                failed += 1
                self.db.increment_complaints(user_id, success=False)
                logger.error(f"Error: {e}")
        
        # Финальное сообщение
        elapsed = (datetime.now() - start_time).seconds
        success_rate = int(success / repeats * 100) if repeats > 0 else 0
        
        final_text = (
            f"{'🎉' if success > 0 else '💔'} **{texts['completed']}**\n\n"
            f"{EMOJI['success']} {texts['successful']}: {success}\n"
            f"{EMOJI['fail']} {texts['failed']}: {failed}\n"
            f"🎯 {texts['target']}: {username}\n"
            f"⏱ {texts['time_passed']}: {elapsed}s\n"
            f"📈 {texts['success_rate']}: {success_rate}%"
        )
        
        keyboard = [
            [InlineKeyboardButton(f"{EMOJI['rocket']} {texts['again']}", callback_data="new_complaint")],
            [InlineKeyboardButton(f"{EMOJI['back']} {texts['back']}", callback_data="back_to_main")]
        ]
        
        await update.message.reply_text(
            final_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    def _get_success_rate(self, user_id: int) -> int:
        user = self.db.get_user(user_id)
        total = user.get('successful', 0) + user.get('failed', 0)
        return int(user.get('successful', 0) / total * 100) if total > 0 else 0


def main():
    # Берём токен из переменной окружения (на Render её нужно добавить)
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise ValueError("No BOT_TOKEN found in environment variables")
    
    bot = ComplaintBot(token)
    
    # Создаём приложение
    application = Application.builder().token(token).build()
    
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CallbackQueryHandler(bot.button_click))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))
    
    # Для Render используем вебхуки, если задан URL (RENDER_EXTERNAL_URL)
    render_url = os.environ.get("RENDER_EXTERNAL_URL")
    if render_url:
        # Запускаем вебхук
        print(f"Starting webhook on {render_url}")
        application.run_webhook(
            listen="0.0.0.0",
            port=int(os.environ.get("PORT", 10000)),
            url_path=token,
            webhook_url=f"{render_url}/{token}"
        )
    else:
        # Локально или на других платформах можно использовать polling
        print("🔥 TruePizza Bot 7.0 FINAL")
        print(f"👑 Owner: {OWNER_ID}")
        print("✅ Bot started in polling mode!")
        print("⏳ Waiting for commands...\n")
        application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
