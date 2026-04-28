# budget_dashboard.py
# Запуск: python budget_dashboard.py

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from sqlalchemy import create_engine, text

# ─────────────────────────────────────────
#  Подключение к БД
# ─────────────────────────────────────────
engine = create_engine(
    'mysql+mysqlconnector://user:123@localhost:6033/order_desk'
)

# ─────────────────────────────────────────
#  1. Загрузка данных
# ─────────────────────────────────────────
def load_data():
    with engine.connect() as conn:

        # Суммарный бюджет по категориям (для пончика)
        df_pie = pd.read_sql(text("""
            SELECT
                bc.name     AS Категория,
                bc.color    AS color,
                SUM(be.amount) AS Бюджет
            FROM budget_entries be
            JOIN budget_categories bc ON bc.id = be.category_id
            GROUP BY bc.id, bc.name, bc.color
            ORDER BY Бюджет DESC
        """), conn)

        # Бюджет по месяцам и категориям (для линий)
        df_trend = pd.read_sql(text("""
            SELECT
                DATE_FORMAT(be.period, '%Y-%m') AS месяц,
                bc.name                          AS категория,
                SUM(be.amount)                   AS сумма
            FROM budget_entries be
            JOIN budget_categories bc ON bc.id = be.category_id
            GROUP BY be.period, bc.name
            ORDER BY be.period
        """), conn)

        # Итоговые расходы по месяцам (для bar)
        df_monthly = pd.read_sql(text("""
            SELECT
                DATE_FORMAT(period, '%Y-%m') AS месяц,
                SUM(amount)                  AS итого
            FROM budget_entries
            GROUP BY period
            ORDER BY period
        """), conn)

    return df_pie, df_trend, df_monthly


# ─────────────────────────────────────────
#  2. Вспомогательная функция тёмной темы
# ─────────────────────────────────────────
def dark_layout(title: str) -> dict:
    return dict(
        title_font_size=18,
        paper_bgcolor='#141d2b',
        plot_bgcolor='#1e2a3a',
        font=dict(color='#a8b2d8', family='Arial'),
        legend=dict(
            bgcolor='#1a2535',
            bordercolor='#2d3748',
            borderwidth=1,
        ),
        xaxis=dict(gridcolor='#2d3748', linecolor='#2d3748'),
        yaxis=dict(gridcolor='#2d3748', linecolor='#2d3748'),
        hoverlabel=dict(bgcolor='#1e2a3a', font_color='white'),
        margin=dict(t=60, b=40, l=60, r=40),
    )


# ─────────────────────────────────────────
#  3. Подготовка данных
# ─────────────────────────────────────────
df_pie, df_trend, df_monthly = load_data()

# Цвета из БД — передаём в том же порядке что и категории
pie_colors = list(df_pie['color'])

# Процент от общего для подписи KPI
total_budget = df_pie['Бюджет'].sum()

# ─────────────────────────────────────────
#  3. Построение графиков
# ─────────────────────────────────────────

# ── Фигура 1: Пончик (как в оригинале, но данные из БД) ─────
fig_pie = px.pie(
    df_pie,
    values='Бюджет',
    names='Категория',
    title='🍩 Распределение бюджета (все месяцы)',
    hole=0.4,
    color='Категория',
    color_discrete_sequence=pie_colors,
)
fig_pie.update_traces(
    textposition='inside',
    textinfo='percent+label',
    hovertemplate="<b>%{label}</b><br>Сумма: %{value:,.0f} ₽<br>Доля: %{percent}<extra></extra>",
)
fig_pie.update_layout(**dark_layout("Распределение бюджета"))
#fig_pie.show()


# ── Фигура 2: Тренды по категориям (линии) ──────────────────
fig_trend = px.line(
    df_trend,
    x='месяц',
    y='сумма',
    color='категория',
    markers=True,
    title='📈 Динамика расходов по категориям',
    labels={'сумма': 'Сумма (₽)', 'месяц': 'Месяц'},
    color_discrete_sequence=pie_colors,
)
fig_trend.update_traces(line_width=2.5, marker_size=7)
fig_trend.update_layout(**dark_layout("Динамика расходов"))
#fig_trend.show()


# ── Фигура 3: Stacked bar — структура по месяцам ────────────
fig_bar = px.bar(
    df_trend,
    x='месяц',
    y='сумма',
    color='категория',
    title='📊 Структура расходов по месяцам',
    labels={'сумма': 'Сумма (₽)', 'месяц': 'Месяц'},
    color_discrete_sequence=pie_colors,
    barmode='stack',
)
fig_bar.update_layout(**dark_layout("Структура расходов"))
#fig_bar.show()


# ── Фигура 4: Комбо — бар + линия итого ─────────────────────
fig_combo = make_subplots(specs=[[{"secondary_y": True}]])

# Stacked bars
categories = df_trend['категория'].unique()
for i, cat in enumerate(categories):
    df_cat = df_trend[df_trend['категория'] == cat]
    fig_combo.add_trace(
        go.Bar(
            x=df_cat['месяц'],
            y=df_cat['сумма'],
            name=cat,
            marker_color=pie_colors[i % len(pie_colors)],
            hovertemplate=f"<b>{cat}</b><br>%{{x}}<br>%{{y:,.0f}} ₽<extra></extra>",
        ),
        secondary_y=False,
    )

# Линия итого
fig_combo.add_trace(
    go.Scatter(
        x=df_monthly['месяц'],
        y=df_monthly['итого'],
        name='Итого',
        mode='lines+markers',
        line=dict(color='white', width=2.5, dash='dot'),
        marker=dict(size=8, color='white'),
        hovertemplate="<b>Итого</b><br>%{x}<br>%{y:,.0f} ₽<extra></extra>",
    ),
    secondary_y=False,
)

fig_combo.update_layout(
    barmode='stack',
    title='📦 Полная картина: структура + итог',
    **dark_layout("Полная картина"),
)
fig_combo.show()