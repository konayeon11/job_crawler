import sqlite3
import json
import os

DB_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'nutritionist.db')

class DatabaseManager:
    def __init__(self, db_file=DB_FILE):
        """
        데이터베이스 관리자 초기화
        :param db_file: SQLite 데이터베이스 파일 경로
        """
        self.conn = sqlite3.connect(db_file)
        self.create_tables()

    def create_tables(self):
        """
        필요한 모든 테이블을 생성합니다.
        """
        with self.conn:
            # user_preferences 테이블
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id TEXT PRIMARY KEY,
                    allergies TEXT,
                    preferences TEXT,
                    dietary_goals TEXT
                )
            """)

            # inventory 테이블
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS inventory (
                    item_name TEXT PRIMARY KEY,
                    quantity TEXT,
                    added_date TEXT,
                    expiry_date TEXT
                )
            """)

            # meal_history 테이블
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS meal_history (
                    meal_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    meal_date TEXT,
                    recipe_id TEXT,
                    recipe_title TEXT,
                    ingredients TEXT
                )
            """)

    def get_inventory(self) -> dict:
        """
        데이터베이스에서 현재 모든 재고를 조회하여 반환합니다.
        """
        with self.conn:
            cursor = self.conn.execute("SELECT item_name, quantity, added_date, expiry_date FROM inventory")
            inventory = {}
            for row in cursor.fetchall():
                item_name, quantity, added_date, expiry_date = row
                inventory[item_name] = {
                    "quantity": quantity,
                    "added_date": added_date,
                    "expiry_date": expiry_date
                }
            return inventory

    def upsert_inventory_item(self, item_name: str, quantity: str, added_date: str, expiry_date: str):
        """
        재고 아이템을 추가하거나 이미 존재하면 업데이트합니다. (Upsert)
        """
        with self.conn:
            self.conn.execute("""
                INSERT INTO inventory (item_name, quantity, added_date, expiry_date)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(item_name) DO UPDATE SET
                    quantity = excluded.quantity,
                    added_date = excluded.added_date,
                    expiry_date = excluded.expiry_date
            """, (item_name, quantity, added_date, expiry_date))

    def get_user_preferences(self, user_id: str = "default_user") -> dict:
        """
        특정 사용자의 환경설정을 조회합니다.
        """
        with self.conn:
            cursor = self.conn.execute(
                "SELECT allergies, preferences, dietary_goals FROM user_preferences WHERE user_id = ?",
                (user_id,)
            )
            row = cursor.fetchone()
            if row:
                allergies, preferences, dietary_goals = row
                return {
                    "user_id": user_id,
                    "allergies": json.loads(allergies) if allergies else [],
                    "preferences": json.loads(preferences) if preferences else {},
                    "dietary_goals": dietary_goals
                }
            return {}

    def update_user_preferences(self, user_id: str = "default_user", allergies: list = None, preferences: dict = None, dietary_goals: str = None):
        """
        사용자 환경설정을 업데이트하거나 추가합니다.
        """
        with self.conn:
            # JSON 직렬화
            allergies_json = json.dumps(allergies) if allergies is not None else None
            preferences_json = json.dumps(preferences) if preferences is not None else None

            self.conn.execute("""
                INSERT INTO user_preferences (user_id, allergies, preferences, dietary_goals)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    allergies = COALESCE(excluded.allergies, allergies),
                    preferences = COALESCE(excluded.preferences, preferences),
                    dietary_goals = COALESCE(excluded.dietary_goals, dietary_goals)
            """, (user_id, allergies_json, preferences_json, dietary_goals))

    def add_meal_to_history(self, meal_date: str, recipe_id: str, recipe_title: str, ingredients: list):
        """
        식사 기록을 추가합니다.
        """
        with self.conn:
            # 동일한 날짜와 recipe_id를 가진 기록이 이미 있는지 확인
            cursor = self.conn.execute(
                "SELECT COUNT(*) FROM meal_history WHERE meal_date = ? AND recipe_id = ?",
                (meal_date, recipe_id)
            )
            if cursor.fetchone()[0] > 0:
                print(f"경고: {meal_date}에 이미 레시피 '{recipe_title}' ({recipe_id}) 기록이 존재합니다. 중복 기록을 건너뜁니다.")
                return

            self.conn.execute("""
                INSERT INTO meal_history (meal_date, recipe_id, recipe_title, ingredients)
                VALUES (?, ?, ?, ?)
            """, (meal_date, recipe_id, recipe_title, json.dumps(ingredients, ensure_ascii=False)))

    def close(self):
        """
        데이터베이스 연결을 닫습니다.
        """
        self.conn.close()

if __name__ == '__main__':
    # 데이터베이스 및 테이블 생성 확인
    db_manager = DatabaseManager()
    print("Database and tables created successfully.")

    # --- 기본 사용자 설정 추가 ---
    print("\nInserting/updating default user preferences...")
    db_manager.update_user_preferences(
        user_id="default_user",
        allergies=["새우"],
        preferences={"dislikes": ["오이"]},
        dietary_goals="저탄수화물"
    )
    print("Default user preferences updated.")

    # --- 설정 조회 및 확인 ---
    prefs = db_manager.get_user_preferences("default_user")
    print("\nRetrieved preferences:")
    import pprint
    pprint.pprint(prefs)
    
    db_manager.close()
