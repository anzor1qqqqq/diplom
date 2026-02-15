import plotly.express as px
import numpy as np
import pandas as pd

# Данные по продажам по кварталам

# Данные о распределении бюджета
df_budget = pd.DataFrame({
    'Категория': ['Зарплата', 'Аренда', 'Маркетинг', 'Разработка', 'Прочее'],
    'Бюджет': [50000, 20000, 15000, 25000, 10000]
})

# Создаем круговую диаграмму
fig = px.pie(df_budget, 
             values='Бюджет', 
             names='Категория',
             title='Распределение бюджета',
             hole=0.3)  # делает "пончик" вместо круга

fig.update_traces(textposition='inside', textinfo='percent+label')
fig.show()