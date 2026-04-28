import matplotlib.pyplot as plt
import pandas as pd
from sqlalchemy import create_engine

plt.rcParams['font.family'] = 'DejaVu Sans'  # поддержка кириллицы

def get_data_from_mysql():
    """Достаем данные из вашей таблицы finance"""
    try:
        engine = create_engine(
            'mysql+mysqlconnector://user:123@localhost:6033/order_desk'
        )
        
        query = """
        SELECT
            month_name,
            month_num,
            sales,
            expenses
        FROM finance
        WHERE year = 2024
        ORDER BY month_num
        """
        
        df = pd.read_sql_query(query, engine)
        print("Успешное подключение к базе данных")
        return df
            
    except Exception as e:
        print(f"Ошибка подключения к MySQL: {e}")
        return None

# Вызов функции
df = get_data_from_mysql()

if df is not None:
    print(df.head())
    
    plt.figure(figsize=(10, 6))
    plt.plot(df['month_num'], df['sales'], marker='o', label='Продажи')
    plt.plot(df['month_num'], df['expenses'], marker='s', label='Расходы')
    plt.xlabel('Месяц')
    plt.ylabel('Сумма')
    plt.title('Продажи и расходы за 2024 год')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.xticks(df['month_num'], df['month_name'], rotation=45)
    plt.tight_layout()
    plt.show()
else:
    print("Не удалось получить данные из базы данных.")