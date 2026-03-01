# viz_example1.py
from bokeh.plotting import figure
from bokeh.server.server import Server
from bokeh.application import Application
from bokeh.application.handlers.function import FunctionHandler
from bokeh.layouts import row, column
from bokeh.models import ColumnDataSource, HoverTool
import numpy as np

def create_dashboard(doc):
    # Генерируем данные
    np.random.seed(42)
    x = np.linspace(0, 10, 50)
    y1 = np.sin(x)
    y2 = np.cos(x)
    y3 = np.random.normal(0, 1, 50)
    
    # Создаем источник данных
    source = ColumnDataSource(data=dict(
        x=x, y1=y1, y2=y2, y3=y3
    ))
    
    # График 1: Синус (линия + точки)
    p1 = figure(title="Синус", width=400, height=300,
                tools="pan,wheel_zoom,box_zoom,reset,hover")
    p1.line('x', 'y1', source=source, line_width=2, color="blue", legend_label="sin(x)")
    p1.circle('x', 'y1', source=source, size=5, color="blue", alpha=0.5)
    p1.xaxis.axis_label = "X"
    p1.yaxis.axis_label = "Y"
    
    # График 2: Косинус (линия + точки)
    p2 = figure(title="Косинус", width=400, height=300,
                tools="pan,wheel_zoom,box_zoom,reset,hover")
    p2.line('x', 'y2', source=source, line_width=2, color="green", legend_label="cos(x)")
    p2.triangle('x', 'y2', source=source, size=6, color="green", alpha=0.5)
    p2.xaxis.axis_label = "X"
    p2.yaxis.axis_label = "Y"
    
    # График 3: Случайные точки
    p3 = figure(title="Случайные точки", width=400, height=300,
                tools="pan,wheel_zoom,box_zoom,reset,hover")
    p3.circle('x', 'y3', source=source, size=10, color="red", alpha=0.6)
    p3.xaxis.axis_label = "X"
    p3.yaxis.axis_label = "Y"
    
    # График 4: Синус vs Косинус
    p4 = figure(title="Синус vs Косинус", width=400, height=300,
                tools="pan,wheel_zoom,box_zoom,reset,hover")
    p4.circle('y1', 'y2', source=source, size=8, color="purple", alpha=0.6)
    p4.xaxis.axis_label = "sin(x)"
    p4.yaxis.axis_label = "cos(x)"
    
    # Добавляем подсказки для всех графиков
    for p in [p1, p2, p3, p4]:
        hover = p.select_one(HoverTool)
        hover.tooltips = [
            ("X", "@x{0.00}"),
            ("Y1", "@y1{0.00}"),
            ("Y2", "@y2{0.00}"),
        ]
    
    # Располагаем графики сеткой 2x2
    layout = column(
        row(p1, p2),
        row(p3, p4)
    )
    
    # Добавляем заголовок
    from bokeh.models import Div
    header = Div(text="""
    <h1 style="text-align: center; color: #2c3e50; margin: 20px;">
        Интерактивная визуализация данных
    </h1>
    <p style="text-align: center; color: #34495e;">
        Пример с различными типами графиков
    </p>
    <hr>
    """)
    
    doc.add_root(column(header, layout))
    doc.title = "Пример визуализации"

# Запускаем сервер
if __name__ == "__main__":
    print("=" * 50)
    print("Запуск сервера визуализации")
    print("=" * 50)
    print("Сервер запущен на: http://localhost:5006")
    print("Откройте этот адрес в браузере")
    print("\nНажмите Ctrl+C для остановки сервера")
    print("=" * 50)
    
    apps = {'/': Application(FunctionHandler(create_dashboard))}
    server = Server(apps, port=5006)
    server.start()
    server.io_loop.add_callback(server.show, "/")
    server.io_loop.start()