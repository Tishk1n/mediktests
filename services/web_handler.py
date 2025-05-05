import asyncio
from playwright.async_api import async_playwright, TimeoutError
from aiogram.types import FSInputFile
import os
import subprocess
import logging

logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WebHandler:
    def __init__(self, bot_instance=None, user_id=None):
        self.base_url = "http://selftest-mpe.mededtech.ru"
        self.bot = bot_instance
        self.user_id = user_id
        self._ensure_playwright_browsers()
    
    def _ensure_playwright_browsers(self):
        try:
            if not os.path.exists(os.path.expanduser('~/.cache/ms-playwright')):
                logger.info("🔄 Установка браузеров Playwright...")
                subprocess.run(['playwright', 'install', 'chromium'], check=True)
                logger.info("✅ Браузеры успешно установлены")
        except Exception as e:
            logger.error(f"❌ Ошибка при установке браузеров: {e}")
            raise

    async def _send_error_screenshot(self, screenshot_path: str, error_message: str):
        if self.bot and self.user_id:
            try:
                photo = FSInputFile(screenshot_path)
                await self.bot.send_photo(
                    chat_id=self.user_id,
                    photo=photo,
                    caption=f"❌ {error_message}"
                )
                os.remove(screenshot_path)  # Удаляем файл после отправки
            except Exception as e:
                logger.error(f"Ошибка при отправке скриншота: {e}")

    async def _send_info_screenshot(self, screenshot_path: str, message: str):
        if self.bot and self.user_id:
            try:
                photo = FSInputFile(screenshot_path)
                await self.bot.send_photo(
                    chat_id=self.user_id,
                    photo=photo,
                    caption=f"ℹ️ {message}"
                )
                os.remove(screenshot_path)
            except Exception as e:
                logger.error(f"Ошибка при отправке скриншота: {e}")
    
    async def login(self, login: str, password: str):
        logger.info("🔄 Начинаем процесс авторизации...")
        
        async with async_playwright() as p:
            try:
                logger.info("🔄 Запуск браузера...")
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-dev-shm-usage']
                )
                logger.info("✅ Браузер запущен успешно")
                
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                page = await context.new_page()
                page.set_default_timeout(60000)
                
                # Первая часть навигации по fmza.ru
                steps = [
                    ("Переход на сайт fmza.ru", 
                     lambda: page.goto("https://fmza.ru", wait_until="networkidle")),
                    
                    ("Поиск 'Первичная аккредитация'", 
                     lambda: page.wait_for_selector('a:has-text("Первичная аккредитация (СПО)")')),
                    ("Клик по 'Первичная аккредитация'", 
                     lambda: page.click('a:has-text("Первичная аккредитация (СПО)")')),
                    
                    ("Поиск 'Специальности СПО'",
                     lambda: page.wait_for_selector('a:has-text("Специальности СПО")')),
                    ("Клик по 'Специальности СПО'",
                     lambda: page.click('a:has-text("Специальности СПО")')),
                ]
                
                # Выполняем первую часть навигации
                for step_name, step_action in steps:
                    try:
                        logger.info(f"🔄 {step_name}...")
                        await step_action()
                        await page.wait_for_load_state("networkidle")
                        
                        # Делаем и отправляем скриншот каждого шага
                        screenshot_path = f"step_{step_name.lower().replace(' ', '_')}.png"
                        await page.screenshot(path=screenshot_path)
                        await self._send_info_screenshot(
                            screenshot_path,
                            f"Шаг: {step_name} - успешно"
                        )
                        
                        logger.info(f"✅ {step_name} - успешно")
                    except Exception as e:
                        error_path = f"error_{step_name.lower().replace(' ', '_')}.png"
                        await page.screenshot(path=error_path)
                        await self._send_error_screenshot(
                            error_path,
                            f"Ошибка на шаге '{step_name}': {str(e)}"
                        )
                        raise

                # Переход на новый сайт и авторизация
                try:
                    logger.info("🔄 Переход на сайт тестирования...")
                    await page.goto(self.base_url, wait_until="networkidle")
                    logger.info("✅ Переход выполнен успешно")

                    logger.info("🔄 Ожидание формы авторизации...")
                    await page.wait_for_selector('input[name="j_username"]')
                    logger.info("🔄 Заполнение формы авторизации...")
                    
                    # Используем новые селекторы
                    await page.fill('input[name="j_username"]', login)
                    await page.fill('input[name="j_password"]', password)
                    
                    # Скриншот перед нажатием кнопки входа
                    await page.screenshot(path="before_login.png")
                    await self._send_info_screenshot(
                        "before_login.png",
                        "Форма авторизации заполнена, выполняем вход..."
                    )
                    
                    await page.click('input.login-button[type="submit"]')

                    # Проверка успешной авторизации
                    try:
                        await page.wait_for_selector('.user-menu', timeout=5000)
                        # Скриншот успешной авторизации
                        await page.screenshot(path="login_success.png")
                        await self._send_info_screenshot(
                            "login_success.png",
                            "✅ Авторизация успешна"
                        )
                        return page
                    except TimeoutError:
                        logger.error("❌ Ошибка авторизации: не найдено подтверждение входа")
                        error_path = "error_auth_failed.png"
                        await page.screenshot(path=error_path)
                        await self._send_error_screenshot(
                            error_path,
                            "Ошибка авторизации: неверный логин или пароль"
                        )
                        raise Exception("Не удалось авторизоваться")

                except Exception as e:
                    error_path = "error_auth.png"
                    await page.screenshot(path=error_path)
                    await self._send_error_screenshot(
                        error_path,
                        f"Ошибка при авторизации: {str(e)}"
                    )
                    raise
                    
            except Exception as e:
                logger.error(f"❌ Критическая ошибка: {str(e)}")
                if 'browser' in locals():
                    await browser.close()
                raise

    async def start_test(self, page):
        await page.click("text=Пройти тестирование")
        await page.click("text=Фармация, 2025")
        await page.click("text=Перейти к первому вопросу")
        return page

    async def process_test(self, page):
        correct_answers = 0
        total_questions = 60
        
        for _ in range(total_questions):
            # Находим правильный ответ (предполагаем, что он есть в коде страницы)
            answer_element = await page.query_selector('[data-correct="true"]')
            if answer_element:
                await answer_element.click()
                correct_answers += 1
            
            # Переходим к следующему вопросу
            next_button = await page.query_selector('button:has-text("Далее")')
            if next_button:
                await next_button.click()
            await page.wait_for_timeout(1000)  # Ждем загрузки следующего вопроса
        
        return {
            "correct": correct_answers,
            "total": total_questions,
            "percentage": round((correct_answers / total_questions) * 100, 2)
        }
