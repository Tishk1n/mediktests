from database.sqlite import Database
from services.web_handler import WebHandler

async def start_testing_process(user_id: int, db: Database) -> dict:
    try:
        credentials = db.get_user_credentials(user_id)
        if not credentials:
            return {"error": "Не найдены данные для входа"}
        
        login, password = credentials
        web = WebHandler()
        
        try:
            page = await web.login(login, password)
            test_page = await web.start_test(page)
            result = await web.process_test(test_page)
            
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
        # Закрываем браузер в любом случае
        if 'page' in locals():
            await page.context.close()
