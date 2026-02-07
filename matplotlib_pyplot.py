# Импортируем нужные библиотеки
import matplotlib.pyplot as plt

# Данные для графика
месяцы = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн']
продажи = [150, 200, 180, 300, 250, 400]
расходы = [100, 120, 150, 200, 180, 220]

# Создаем график
plt.figure(figsize=(10, 6))  # Размер графика

# Два графика на одном рисунке
plt.plot(месяцы, продажи, label='Продажи', 
         marker='o', linewidth=2, color='green')
plt.plot(месяцы, расходы, label='Расходы', 
         marker='s', linewidth=2, color='red')

# Настройки графика
plt.title('Продажи и расходы по месяцам', fontsize=16)
plt.xlabel('Месяцы', fontsize=12)
plt.ylabel('Тысячи рублей', fontsize=12)
plt.grid(True, alpha=0.3)  # Сетка с прозрачностью
plt.legend()  # Показываем легенду

# Сохраняем график
plt.savefig('matplotlib_pyplot.png', dpi=300)

# Показываем график
plt.show()

print("matplotlib_pyplot.png'")