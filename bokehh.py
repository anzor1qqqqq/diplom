# fleet_dashboard.py
# Запуск: python fleet_dashboard.py
# Открыть: http://localhost:5006

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
from bokeh.plotting import figure
from bokeh.server.server import Server
from bokeh.application import Application
from bokeh.application.handlers.function import FunctionHandler
from bokeh.layouts import row, column
from bokeh.models import (
    ColumnDataSource, HoverTool, Div,
    Select, DateRangeSlider, DataTable, TableColumn,
    NumberFormatter, StringFormatter
)
from bokeh.palettes import Category10, Spectral6
from bokeh.transform import factor_cmap
from datetime import date, timedelta

# ─────────────────────────────────────────
#  Подключение к БД
# ─────────────────────────────────────────
DB_URL = 'mysql+mysqlconnector://user:123@localhost:6033/order_desk'
engine = create_engine(DB_URL, pool_pre_ping=True)


def load_data():
    """Загружаем все нужные данные из MySQL одним вызовом."""
    with engine.connect() as conn:

        # 1. Поездки помесячно — пробег и расход
        trips_monthly = pd.read_sql(text("""
            SELECT
                DATE_FORMAT(started_at, '%Y-%m-01')  AS month,
                SUM(distance_km)                      AS total_km,
                SUM(fuel_used_l)                      AS total_fuel,
                COUNT(*)                              AS trip_count,
                AVG(distance_km)                      AS avg_km
            FROM trips
            WHERE started_at >= DATE_SUB(CURDATE(), INTERVAL 18 MONTH)
            GROUP BY month
            ORDER BY month
        """), conn)
        trips_monthly['month'] = pd.to_datetime(trips_monthly['month'])

        # 2. Пробег по автомобилю (помесячно)
        by_vehicle = pd.read_sql(text("""
            SELECT
                DATE_FORMAT(t.started_at, '%Y-%m-01') AS month,
                CONCAT(v.brand, ' ', v.model, ' (', v.plate, ')') AS vehicle,
                SUM(t.distance_km) AS km
            FROM trips t
            JOIN vehicles v ON v.id = t.vehicle_id
            WHERE t.started_at >= DATE_SUB(CURDATE(), INTERVAL 18 MONTH)
            GROUP BY month, vehicle
            ORDER BY month
        """), conn)
        by_vehicle['month'] = pd.to_datetime(by_vehicle['month'])

        # 3. Расходы на ТО помесячно
        maintenance_monthly = pd.read_sql(text("""
            SELECT
                DATE_FORMAT(service_date, '%Y-%m-01') AS month,
                SUM(cost)  AS total_cost,
                COUNT(*)   AS service_count
            FROM maintenance
            WHERE service_date >= DATE_SUB(CURDATE(), INTERVAL 18 MONTH)
            GROUP BY month
            ORDER BY month
        """), conn)
        maintenance_monthly['month'] = pd.to_datetime(maintenance_monthly['month'])

        # 4. Топ водителей
        top_drivers = pd.read_sql(text("""
            SELECT
                d.full_name,
                COUNT(*)           AS trips,
                SUM(t.distance_km) AS total_km,
                SUM(t.fuel_used_l) AS total_fuel
            FROM trips t
            JOIN drivers d ON d.id = t.driver_id
            WHERE t.started_at >= DATE_SUB(CURDATE(), INTERVAL 18 MONTH)
            GROUP BY d.id, d.full_name
            ORDER BY total_km DESC
        """), conn)

        # 5. Цель поездок
        by_purpose = pd.read_sql(text("""
            SELECT
                purpose,
                COUNT(*) AS cnt,
                SUM(distance_km) AS km
            FROM trips
            WHERE started_at >= DATE_SUB(CURDATE(), INTERVAL 18 MONTH)
            GROUP BY purpose
        """), conn)

    return trips_monthly, by_vehicle, maintenance_monthly, top_drivers, by_purpose


# ─────────────────────────────────────────
#  Dashboard factory
# ─────────────────────────────────────────
def create_dashboard(doc):
    trips_monthly, by_vehicle, maint_monthly, top_drivers, by_purpose = load_data()

    colors = Category10[10]

    # ── Заголовок ───────────────────────────────────────────
    header = Div(text="""
        <div style="
            background: linear-gradient(135deg,#1a1a2e,#16213e);
            padding:24px 32px; border-radius:12px; margin-bottom:16px;
        ">
          <h1 style="margin:0;color:#e94560;font-size:26px;">
            🚗 Дашборд автопарка
          </h1>
          <p style="margin:6px 0 0;color:#a8b2d8;font-size:13px;">
            Тренды за последние 18 месяцев · данные из MySQL
          </p>
        </div>
    """, width=1300)

    # ── KPI плашки ──────────────────────────────────────────
    total_km    = int(trips_monthly['total_km'].sum())
    total_trips = int(trips_monthly['trip_count'].sum())
    total_fuel  = int(trips_monthly['total_fuel'].sum())
    total_maint = int(maint_monthly['total_cost'].sum()) if len(maint_monthly) else 0

    def kpi_card(label, value, unit, color):
        return Div(text=f"""
            <div style="
                background:#1e2a3a; border-left:4px solid {color};
                border-radius:8px; padding:18px 22px; width:260px;
            ">
              <div style="color:#a8b2d8;font-size:12px;text-transform:uppercase;
                          letter-spacing:1px;">{label}</div>
              <div style="color:#fff;font-size:28px;font-weight:700;margin-top:6px;">
                {value:,} <span style="font-size:14px;color:#a8b2d8;">{unit}</span>
              </div>
            </div>
        """, width=280)

    kpi_row = row(
        kpi_card("Общий пробег",     total_km,    "км",  "#e94560"),
        kpi_card("Поездок",          total_trips, "шт",  "#0f3460"),
        kpi_card("Топливо",          total_fuel,  "л",   "#533483"),
        kpi_card("Расходы на ТО",    total_maint, "₽",   "#06a77d"),
    )

    # ── График 1: пробег и кол-во поездок по месяцам ────────
    x_months = list(trips_monthly['month'])

    src1 = ColumnDataSource(dict(
        month  = x_months,
        km     = list(trips_monthly['total_km']),
        trips  = list(trips_monthly['trip_count']),
        fuel   = list(trips_monthly['total_fuel']),
    ))

    p1 = figure(
        title="📈 Ежемесячный пробег (км)",
        x_axis_type="datetime",
        width=620, height=300,
        tools="pan,wheel_zoom,box_zoom,reset,save",
        toolbar_location="above",
    )
    p1.line('month', 'km', source=src1, line_width=2.5,
            color="#e94560", legend_label="Пробег км")
    p1.circle('month', 'km', source=src1, size=7,
              color="#e94560", alpha=0.8)
    p1.add_tools(HoverTool(tooltips=[
        ("Месяц",    "@month{%b %Y}"),
        ("Пробег",   "@km{0,0} км"),
        ("Поездок",  "@trips"),
        ("Топливо",  "@fuel{0,0} л"),
    ], formatters={"@month": "datetime"}, mode="vline"))
    p1.yaxis.axis_label = "км"
    p1.legend.location = "top_left"
    _style(p1)

    # ── График 2: расход топлива + ТО ───────────────────────
    # Объединяем поездки и ТО по месяцам
    merged = trips_monthly[['month','total_fuel']].copy()
    merged = merged.merge(
        maint_monthly[['month','total_cost']].rename(columns={'total_cost':'maint_cost'}),
        on='month', how='left'
    )
    merged['maint_cost'] = merged['maint_cost'].fillna(0)

    src2 = ColumnDataSource(dict(
        month = list(merged['month']),
        fuel  = list(merged['total_fuel']),
        maint = list(merged['maint_cost']),
    ))

    p2 = figure(
        title="⛽ Расход топлива и затраты на ТО",
        x_axis_type="datetime",
        width=620, height=300,
        tools="pan,wheel_zoom,box_zoom,reset,save",
        toolbar_location="above",
    )
    p2.line('month', 'fuel', source=src2, line_width=2.5,
            color="#533483", legend_label="Топливо (л)")
    p2.vbar('month', top='maint', source=src2, width=20*24*60*60*1000,
            color="#06a77d", alpha=0.6, legend_label="ТО (₽ / 100)")
    p2.add_tools(HoverTool(tooltips=[
        ("Месяц",   "@month{%b %Y}"),
        ("Топливо", "@fuel{0,0} л"),
        ("ТО",      "@maint{0,0} ₽"),
    ], formatters={"@month": "datetime"}, mode="vline"))
    p2.yaxis.axis_label = "л / ₽"
    p2.legend.location = "top_right"
    _style(p2)

    # ── График 3: пробег по автомобилям (линии) ─────────────
    vehicles = sorted(by_vehicle['vehicle'].unique())
    p3 = figure(
        title="🚙 Пробег по автомобилям",
        x_axis_type="datetime",
        width=620, height=320,
        tools="pan,wheel_zoom,box_zoom,reset,save",
        toolbar_location="above",
    )
    for i, veh in enumerate(vehicles):
        df_v = by_vehicle[by_vehicle['vehicle'] == veh].sort_values('month')
        src_v = ColumnDataSource(dict(
            month = list(df_v['month']),
            km    = list(df_v['km']),
            veh   = [veh] * len(df_v),
        ))
        color = Spectral6[i % 6]
        p3.line('month', 'km', source=src_v, line_width=2,
                color=color, legend_label=veh.split(' (')[0])
        p3.circle('month', 'km', source=src_v, size=5,
                  color=color, alpha=0.7)
    p3.add_tools(HoverTool(tooltips=[
        ("Месяц", "@month{%b %Y}"),
        ("Авто",  "@veh"),
        ("Пробег","@km{0,0} км"),
    ], formatters={"@month": "datetime"}))
    p3.legend.location = "top_left"
    p3.legend.click_policy = "hide"   # ← можно скрывать линии кликом
    p3.yaxis.axis_label = "км"
    _style(p3)

    # ── График 4: средняя дальность поездки ─────────────────
    src4 = ColumnDataSource(dict(
        month  = list(trips_monthly['month']),
        avg_km = list(trips_monthly['avg_km']),
    ))
    p4 = figure(
        title="📊 Средняя дальность поездки (км)",
        x_axis_type="datetime",
        width=620, height=320,
        tools="pan,wheel_zoom,box_zoom,reset,save",
        toolbar_location="above",
    )
    p4.vbar('month', top='avg_km', source=src4,
            width=22*24*60*60*1000, color="#0f3460", alpha=0.8)
    p4.add_tools(HoverTool(tooltips=[
        ("Месяц",   "@month{%b %Y}"),
        ("Ср. км",  "@avg_km{0.0} км"),
    ], formatters={"@month": "datetime"}, mode="vline"))
    p4.yaxis.axis_label = "км"
    _style(p4)

    # ── Таблица: топ водителей ───────────────────────────────
    src_drv = ColumnDataSource(top_drivers)
    cols_drv = [
        TableColumn(field="full_name",  title="Водитель",    width=200,
                    formatter=StringFormatter()),
        TableColumn(field="trips",      title="Поездок",     width=90,
                    formatter=NumberFormatter(format="0,0")),
        TableColumn(field="total_km",   title="Пробег (км)", width=120,
                    formatter=NumberFormatter(format="0,0.0")),
        TableColumn(field="total_fuel", title="Топливо (л)", width=120,
                    formatter=NumberFormatter(format="0,0.0")),
    ]
    drivers_table = DataTable(source=src_drv, columns=cols_drv,
                              width=580, height=220, index_position=None)
    drivers_header = Div(text="""
        <h3 style="color:#e94560;margin:16px 0 4px;">🏆 Топ водителей</h3>
    """, width=580)

    # ── Цель поездок (горизонтальный бар) ───────────────────
    purposes = list(by_purpose['purpose'])
    counts   = list(by_purpose['cnt'])
    src_pur  = ColumnDataSource(dict(purpose=purposes, cnt=counts))
    p5 = figure(
        title="🎯 Цель поездок",
        y_range=purposes,
        width=580, height=220,
        tools="",
        toolbar_location=None,
    )
    p5.hbar(y='purpose', right='cnt', source=src_pur,
            height=0.6,
            color=factor_cmap('purpose', palette=Spectral6, factors=purposes))
    p5.add_tools(HoverTool(tooltips=[("Цель","@purpose"),("Поездок","@cnt")]))
    p5.xaxis.axis_label = "Кол-во поездок"
    p5.ygrid.grid_line_color = None
    _style(p5)

    # ── Сборка дашборда ──────────────────────────────────────
    doc.add_root(column(
        header,
        kpi_row,
        Div(text="<hr style='border-color:#1e2a3a;margin:8px 0'>"),
        row(p1, p2),
        row(p3, p4),
        Div(text="<hr style='border-color:#1e2a3a;margin:8px 0'>"),
        row(
            column(drivers_header, drivers_table),
            p5,
        ),
    ))
    doc.title = "Автопарк · Аналитика"


def _style(p):
    """Тёмная тема для всех графиков."""
    p.background_fill_color = "#1e2a3a"
    p.border_fill_color      = "#141d2b"
    p.outline_line_color     = None
    p.title.text_color       = "#e2e8f0"
    p.title.text_font_size   = "14px"
    p.xaxis.axis_label_text_color = "#a8b2d8"
    p.yaxis.axis_label_text_color = "#a8b2d8"
    p.xaxis.major_label_text_color = "#a8b2d8"
    p.yaxis.major_label_text_color = "#a8b2d8"
    p.xgrid.grid_line_color  = "#1e2a3a"
    p.ygrid.grid_line_color  = "#1e2a3a"
    if p.legend:
        p.legend.background_fill_color = "#1a2535"
        p.legend.label_text_color      = "#a8b2d8"
        p.legend.border_line_color     = "#2d3748"


# ─────────────────────────────────────────
#  Запуск сервера
# ─────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("  🚗  Дашборд автопарка")
    print("=" * 55)
    print("  Сервер: http://localhost:5006")
    print("  Остановка: Ctrl+C")
    print("=" * 55)

    apps = {'/': Application(FunctionHandler(create_dashboard))}
    server = Server(apps, port=5006)
    server.start()
    server.io_loop.add_callback(server.show, "/")
    server.io_loop.start()