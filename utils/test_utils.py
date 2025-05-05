from database.sqlite import Database
from services.web_handler import WebHandler

async def start_testing_process(user_id: int, db: Database, bot=None, test_url: str = None) -> dict:
    web = None
    try:
        credentials = db.get_user_credentials(user_id)
        if not credentials:
            return {"error": "Не найдены данные для входа"}
        
        login, password = credentials
        web = WebHandler(bot_instance=bot, user_id=user_id)
        
        page = await web.login(login, password)
        result = await web.process_test(page, test_url)
        
        # Сохраняем результат в БД
        db.save_test_result(
            user_id=user_id,
            score=result['percentage'],
            correct=result['correct'],
            total=result['total']
        )
        
        return result
    except Exception as e:
        if "Executable doesn't exist" in str(e):
            return {"error": "Необходимо установить браузеры. Пожалуйста, обратитесь к администратору."}
        return {"error": f"Ошибка при прохождении теста: {str(e)}"}
    finally:
        if web:
            await web.close()
