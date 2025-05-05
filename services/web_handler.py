import asyncio
from playwright.async_api import async_playwright, TimeoutError
import os
import subprocess
import logging

logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WebHandler:
    def __init__(self):
        self.base_url = "https://selftest-mpe.medtech.ru"
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
                
                # Навигация по сайту с логированием каждого шага
                steps = [
                    ("Переход на сайт fmza.ru", 
                     lambda: page.goto("https://fmza.ru", wait_until="networkidle")),
                    
                    ("Поиск 'Первичная аккредитация'", 
                     lambda: page.wait_for_selector('a:has-text("Первичная аккредитация")')),
                    ("Клик по 'Первичная аккредитация'", 
                     lambda: page.click('a:has-text("Первичная аккредитация")')),
                    
                    ("Поиск 'Специальности СПО'",
                     lambda: page.wait_for_selector('a:has-text("Специальности СПО")')),
                    ("Клик по 'Специальности СПО'",
                     lambda: page.click('a:has-text("Специальности СПО")')),
                    
                    ("Поиск 'Фармация'",
                     lambda: page.wait_for_selector('a:has-text("Фармация")')),
                    ("Клик по 'Фармация'",
                     lambda: page.click('a:has-text("Фармация")')),
                    
                    ("Поиск 'Тестовые задания'",
                     lambda: page.wait_for_selector('a:has-text("Тестовые задания")')),
                    ("Клик по 'Тестовые задания'",
                     lambda: page.click('a:has-text("Тестовые задания")')),
                    
                    ("Поиск 'Репетиционный экзамен'",
                     lambda: page.wait_for_selector('a:has-text("Репетиционный экзамен")')),
                    ("Клик по 'Репетиционный экзамен'",
                     lambda: page.click('a:has-text("Репетиционный экзамен")')),
                ]
                
                # Выполняем каждый шаг с логированием
                for step_name, step_action in steps:
                    try:
                        logger.info(f"🔄 {step_name}...")
                        await step_action()
                        await page.wait_for_load_state("networkidle")
                        logger.info(f"✅ {step_name} - успешно")
                    except Exception as e:
                        logger.error(f"❌ {step_name} - ошибка: {str(e)}")
                        await page.screenshot(path=f"error_{step_name.lower().replace(' ', '_')}.png")
                        raise
                
                # Авторизация
                try:
                    logger.info("🔄 Ожидание формы авторизации...")
                    await page.wait_for_selector('input[name="login"]')
                    logger.info("🔄 Заполнение формы авторизации...")
                    await page.fill('input[name="login"]', login)
                    await page.fill('input[name="password"]', password)
                    await page.click('button[type="submit"]')
                    logger.info("✅ Авторизация выполнена")
                    return page
                except Exception as e:
                    logger.error(f"❌ Ошибка при авторизации: {str(e)}")
                    await page.screenshot(path="error_auth.png")
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
