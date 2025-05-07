import asyncio
import re
import os
import logging
import subprocess

from urllib import parse

from fuzzywuzzy import process

from aiogram.types import FSInputFile

from playwright.async_api import async_playwright, TimeoutError, Page, Browser, Locator


logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class WebHandler:
    def __init__(self, bot_instance=None, user_id=None):
        self.base_url = "http://selftest-mpe.mededtech.ru"
        self.bot = bot_instance
        self.user_id = user_id
        self.browser: Browser = None
        self.context = None
        self.answers_url = "https://www.tests-exam.ru/vopros.html?id_test=719&id_vopros=25565"
        self.answer_page: Page = None
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

    async def _init_browser(self):
        if not self.browser:
            logger.info("🔄 Запуск браузера...")
            p = await async_playwright().start()
            self.browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            logger.info("✅ Браузер запущен успешно")

    async def close(self):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()

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
        
        try:
            await self._init_browser()
            page = await self.context.new_page()
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
                
                await page.fill('input[name="j_username"]', login)
                await page.fill('input[name="j_password"]', password)
                
                await page.screenshot(path="before_login.png")
                await self._send_info_screenshot(
                    "before_login.png",
                    "Форма авторизации заполнена, выполняем вход..."
                )
                
                await page.click('input.login-button[type="submit"]')
                await page.wait_for_load_state("networkidle")
                
                await page.screenshot(path="after_login.png")
                await self._send_info_screenshot(
                    "after_login.png",
                    "✅ Авторизация выполнена"
                )
                
                return page

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
            await self.close()
            raise

    async def start_test(self, page):
        try:
            logger.info("🔄 Начинаем создание теста...")
            await page.wait_for_load_state("networkidle")
            
            # Шаг 1: Нажатие кнопки "Пройти тестирование"
            logger.info("🔄 Ищем кнопку 'Пройти тестирование'...")
            await page.wait_for_timeout(2000)  # Даем странице полностью загрузиться
            await page.screenshot(path="before_start_button.png")
            await self._send_info_screenshot(
                "before_start_button.png",
                "Ищем кнопку 'Пройти тестирование'"
            )
            
            await page.click('#dijit_form_Button_0_label')
            await page.wait_for_load_state("networkidle")
            logger.info("✅ Кнопка 'Пройти тестирование' нажата")
            
            # Шаг 2: Выбор специальности
            logger.info("🔄 Выбираем специальность...")
            await page.wait_for_timeout(2000)
            await page.screenshot(path="specialty_selection.png")
            await self._send_info_screenshot(
                "specialty_selection.png",
                "Выбираем 'Фармация, 2025'"
            )
            
            await page.click('span.extraSpace:has-text("Фармация, 2025")')
            await page.wait_for_load_state("networkidle")
            logger.info("✅ Специальность выбрана")
            
            # Шаг 3: Переход к первому вопросу
            logger.info("🔄 Переходим к первому вопросу...")
            await page.wait_for_timeout(2000)
            await page.screenshot(path="before_first_question.png")
            await self._send_info_screenshot(
                "before_first_question.png",
                "Переходим к тестированию"
            )
            
            await page.click('#xsltforms-subform-0-label-2_2_6_4_2_')
            await page.wait_for_load_state("networkidle")
            logger.info("✅ Тест начат")
            
            return page
            
        except Exception as e:
            error_path = "error_start_test.png"
            await page.screenshot(path=error_path)
            await self._send_error_screenshot(
                error_path,
                f"❌ Ошибка при подготовке теста: {str(e)}"
            )
            raise
    
    async def parse_answer(self, question_text: str):
        if not self.answer_page:
            self.answer_page = await self.browser.new_page()
        
        url = (
                "https://www.tests-exam.ru/search.html?kat=428&sea="
                + parse.quote(
                    (' '.join(re.sub(r'[^\w\s]', '', question_text, flags=re.UNICODE).split()[:-2])).encode('cp1251')
                )
            )
        print(url)
        await self.answer_page.goto(url)
        # переход на страницу с ответом
        await self.answer_page.click('//div[@class="b"]/a[@href]')
        
        return (await self.answer_page.locator('//*[@id="prav_id"]').text_content()).strip()
    
    async def get_answer(self, page: Page, question_text: str) -> int | None:
        try:
            logger.info("🔄 Получаем варианты ответов...")
            
            # Находим все варианты ответов и их порядковые номера
            options = {}
            rows = await page.locator("table.question_options > tbody > tr").all()
            
            for i, row in enumerate(rows, 1):
                try:
                    option_text = await row.locator("td:nth-child(3)").inner_text()
                    if option_text:
                        clean_text = option_text.split("Обоснование")[0].strip()
                        options[clean_text] = i  # Сохраняем порядковый номер варианта
                except Exception as e:
                    logger.error(f"Ошибка при получении варианта {i}: {e}")
                    continue

            # Получаем правильный ответ
            correct_answer = await self.parse_answer(question_text)
            if correct_answer:
                clean_correct = correct_answer.split("Обоснование")[0].strip()
                closest_match = process.extractOne(clean_correct, options.keys())
                
                if closest_match and closest_match[1] >= 85:
                    answer_index = options[closest_match[0]]
                    await self.bot.send_message(
                        self.user_id,
                        f"Правильный ответ:\n{closest_match[0]}"
                    )
                    return answer_index
            
            return None

        except Exception as e:
            logger.error(f"❌ Ошибка при поиске ответа: {e}")
            return None

    async def process_test(self, page, test_url: str):
        try:
            logger.info("🔄 Переходим по ссылке на тест...")
            await page.goto(test_url)
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(2000)  # Даем странице полностью загрузиться
            
            await page.screenshot(path="before_list.png")
            await self._send_info_screenshot(
                "before_list.png",
                "Переходим к списку вопросов..."
            )
            
            # Нажимаем кнопку "К списку вопросов" с новым селектором
            try:
                list_button = await page.wait_for_selector(
                    'button span#xsltforms-subform-0-label-2_2_2_6_2_10_4_2_',
                    timeout=10000
                )
                if list_button:
                    await list_button.click()
                else:
                    logger.error("❌ Кнопка 'К списку вопросов' не найдена")
                    raise Exception("Кнопка списка вопросов не найдена")
                
            except Exception as e:
                logger.error(f"❌ Ошибка при поиске кнопки списка: {e}")
                # Пробуем альтернативный способ
                try:
                    await page.evaluate('''() => {
                        const buttons = Array.from(document.querySelectorAll('button'));
                        const listButton = buttons.find(b => b.textContent.includes('К списку вопросов'));
                        if (listButton) listButton.click();
                    }''')
                except Exception as e2:
                    logger.error(f"❌ Альтернативный метод также не сработал: {e2}")
                    raise
            
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(2000)
            
            await page.screenshot(path="questions_list.png")
            await self._send_info_screenshot(
                "questions_list.png",
                "Список вопросов открыт"
            )
            
            # Остальная логика обработки теста
            correct_answers = 0
            current_question = 80

            while current_question > 0:
                logger.info(f"🔄 Обработка вопроса {current_question}")
                
                try:
                    # Ждем загрузки вопроса
                    await page.wait_for_load_state("networkidle")
                    await page.wait_for_timeout(2000)
                    
                    question_element = await page.wait_for_selector('//*[@id="xsltforms-subform-0-output-14_4_2_"]/span/span/p')
                    question_text = await question_element.inner_text()
                    
                    # Получаем индекс правильного ответа
                    answer_index = await self.get_answer(page, question_text)
                    
                    if answer_index:
                        try:
                            # Находим и кликаем по нужному радиобоксу
                            selector = f"table.question_options > tbody > tr:nth-child({answer_index}) td:first-child input[type='radio']"
                            await page.wait_for_selector(selector)
                            await page.click(selector)
                            correct_answers += 1
                            logger.info(f"✅ Выбран ответ {answer_index}")
                            
                            # Ждем применения ответа
                            await page.wait_for_timeout(1000)
                            
                            # Проверяем, есть ли кнопка "Далее"
                            next_button = await page.query_selector("button:has-text('Далее')")
                            if next_button:
                                await next_button.click()
                            else:
                                # Если нет кнопки "Далее", значит мы дошли до конца или до решенного вопроса
                                break
                                
                        except Exception as click_error:
                            logger.error(f"Ошибка при выборе ответа: {click_error}")
                            break
                    
                    current_question -= 1
                    
                except Exception as e:
                    logger.error(f"Ошибка при обработке вопроса {current_question}: {e}")
                    break

            return {
                "correct": correct_answers,
                "total": 80 - current_question,
                "percentage": round((correct_answers / (80 - current_question)) * 100, 2)
            }

        except Exception as e:
            error_path = "error_processing_test.png"
            await page.screenshot(path=error_path)
            await self._send_error_screenshot(
                error_path,
                f"❌ Ошибка при выполнении теста: {str(e)}"
            )
            raise
