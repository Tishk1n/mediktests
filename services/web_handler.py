import asyncio
from playwright.async_api import async_playwright, TimeoutError
from aiogram.types import FSInputFile
import os
import subprocess
import logging
import re
import aiohttp

logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WebHandler:
    def __init__(self, bot_instance=None, user_id=None):
        self.base_url = "http://selftest-mpe.mededtech.ru"
        self.bot = bot_instance
        self.user_id = user_id
        self.browser = None
        self.context = None
        self.answers_url = "https://www.tests-exam.ru/vopros.html?id_test=719&id_vopros=25565"
        self.chatgpt_api_url = "https://free.churchless.tech/v1/chat/completions"
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
    
    async def _ask_chatgpt(self, question: str, answers: list) -> str:
        try:
            prompt = f"Вопрос - {question}\nВарианты ответа - {', '.join(answers)}\nПришли только правильный вариант ответа."
            
            headers = {
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7
            }
            
            logger.info(f"🔄 Отправляем запрос в ChatGPT:\n{prompt}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.chatgpt_api_url, json=data, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        answer = result['choices'][0]['message']['content'].strip()
                        logger.info(f"✅ Получен ответ от ChatGPT: {answer}")
                        return answer
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Ошибка API ChatGPT: {error_text}")
                        return None
                        
        except Exception as e:
            logger.error(f"❌ Ошибка при запросе к ChatGPT: {e}")
            return None

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

    async def get_answer(self, page, question_text: str) -> str:
        try:
            logger.info("🔄 Получаем варианты ответов...")
            
            # Получаем все варианты ответов с улучшенной очисткой текста
            answers = await page.evaluate('''() => {
                const options = Array.from(document.querySelectorAll('.testRadioButton')).map(el => {
                    // Получаем текст ответа
                    let text = el.closest('tr').textContent.trim();
                    
                    // Удаляем все звездочки и пробелы
                    text = text.replace(/\*/g, '').trim();
                    
                    // Удаляем буквенные обозначения (А, Б, В, Г) в начале и пробел после них
                    text = text.replace(/^[АБВГ]\s*/, '');
                    
                    // Удаляем слово "Обоснование" и всё после него
                    text = text.split('Обоснование')[0].trim();
                    
                    // Удаляем все лишние пробелы между буквами
                    text = text.replace(/\s+/g, '');
                    
                    // Добавляем пробелы между словами по правилам русского языка
                    text = text.replace(/([а-яё])([А-ЯЁ])/g, '$1 $2').toLowerCase();
                    
                    return text.trim();
                });
                return options;
            }''')
            
            if not answers:
                logger.error("❌ Не найдены варианты ответов")
                return None
                
            # Удаляем дубликаты ответов
            answers = list(dict.fromkeys(answers))
                
            await page.screenshot(path="question_options.png")
            await self._send_info_screenshot(
                "question_options.png",
                f"Вопрос: {question_text}\n\nВарианты ответов:\n" + "\n".join(answers)
            )
            
            # Получаем ответ от ChatGPT
            correct_answer = await self._ask_chatgpt(question_text, answers)
            
            if correct_answer:
                await self.bot.send_message(
                    self.user_id,
                    f"🤖 ChatGPT предполагает, что правильный ответ:\n{correct_answer}"
                )
                return correct_answer
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Ошибка при поиске ответа: {e}")
            await page.screenshot(path="error_get_answer.png")
            await self._send_error_screenshot(
                "error_get_answer.png",
                f"Ошибка при поиске ответа: {str(e)}"
            )
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
                
                # Получаем текст вопроса с новым XPath селектором
                try:
                    question_element = await page.wait_for_selector('//*[@id="xsltforms-subform-0-output-14_4_2_"]/span/span/p')
                    question_text = await question_element.inner_text()
                    if not question_text:
                        logger.error("❌ Текст вопроса пуст")
                        raise Exception("Не удалось получить текст вопроса")
                    
                    logger.info(f"✅ Получен текст вопроса: {question_text[:100]}...")
                except Exception as e:
                    logger.error(f"❌ Ошибка при получении текста вопроса: {e}")
                    # Делаем скриншот для отладки
                    await page.screenshot(path=f"error_question_{current_question}.png")
                    await self._send_error_screenshot(
                        f"error_question_{current_question}.png",
                        f"Ошибка при получении текста вопроса {current_question}"
                    )
                    raise

                await page.screenshot(path=f"question_{current_question}.png")
                await self._send_info_screenshot(
                    f"question_{current_question}.png",
                    f"Вопрос {current_question}:\n{question_text[:100]}..."
                )

                # Получаем правильный ответ
                correct_answer = await self.get_answer(page, question_text)
                
                if correct_answer:
                    # Возвращаемся на страницу теста
                    await page.goto(test_url)
                    await page.wait_for_load_state("networkidle")
                    
                    # Ищем и выбираем правильный вариант ответа
                    answers = await page.query_selector_all('.testRadioButton')
                    for answer in answers:
                        answer_text = await answer.evaluate('el => el.closest("tr").textContent')
                        if correct_answer in answer_text:
                            await answer.click()
                            correct_answers += 1
                            break
                
                # Возвращаемся к предыдущему вопросу
                await page.click('#xsltforms-subform-4-label-2_2_2_2_2_10_4_2_')
                current_question -= 1
                await page.wait_for_load_state("networkidle")
                
                # Проверяем, решен ли предыдущий вопрос
                is_answered = await page.evaluate('''() => {
                    return document.querySelector('.fa-check-circle') !== null;
                }''')
                
                if is_answered:
                    logger.info("✅ Достигнут уже решенный вопрос")
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
