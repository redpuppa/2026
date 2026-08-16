import tkinter as tk
import requests
import threading
import time
from datetime import datetime, timedelta

import matplotlib
matplotlib.use("TkAgg")

import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from ubidots_secrets import UBIDOTS_TOKEN


# =====================================================
# Matplotlib 한글 설정
# =====================================================

plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False


# =====================================================
# Ubidots 설정
# =====================================================

BASE_URL = (
    "https://industrial.api.ubidots.com"
    "/api/v1.6/devices"
)

RESAMPLE_URL = (
    "https://industrial.api.ubidots.com"
    "/api/v1.6/data/stats/resample/"
)

HEADERS = {
    "X-Auth-Token": UBIDOTS_TOKEN,
    "Content-Type": "application/json",
}


# =====================================================
# Device 설정
# =====================================================

DEVICES = {
    "d1mini-sht30-01": "센서 1  SHT30",
    "d1mini-sht30-02": "센서 2  SHT30",
    "d1mini-dht11-02": "센서 3  DHT11",
}


# =====================================================
# 센서 이름
# =====================================================

SENSOR_NAMES = {

    "d1mini-sht30-01":
        ("센서 1", "SHT30"),

    "d1mini-sht30-02":
        ("센서 2", "SHT30"),

    "d1mini-dht11-02":
        ("센서 3", "DHT11"),
}


# =====================================================
# 그래프 센서별 색상
# =====================================================

SENSOR_COLORS = {

    "d1mini-sht30-01":
        "tab:blue",

    "d1mini-sht30-02":
        "tab:orange",

    "d1mini-dht11-02":
        "tab:green",
}


# =====================================================
# 정상 범위
#
# 필요하면 이 부분만 수정
# =====================================================

TEMP_MIN = 0.0
TEMP_MAX = 50.0

HUMIDITY_MIN = 20.0
HUMIDITY_MAX = 80.0


# =====================================================
# 그래프 기간
# =====================================================

PERIODS = {

    "24시간": {
        "hours": 24,
        "period": "10T",
    },

    "1주일": {
        "hours": 24 * 7,
        "period": "1H",
    },

    "1개월": {
        "hours": 24 * 30,
        "period": "3H",
    },
}


selected_period = "24시간"


# =====================================================
# 센서 현재 데이터
# =====================================================

sensor_data = {}

for device_label in DEVICES:

    sensor_data[device_label] = {

        "temperature": None,

        "humidity": None,

        "status": "연결 대기",

        "normal": False,
    }


# =====================================================
# Ubidots Variable ID
# =====================================================

variable_ids = {}


# =====================================================
# GUI Widget 저장
# =====================================================

sensor_widgets = {}


# =====================================================
# 신호등 저장
# =====================================================

warning_lamps = {}

warning_blink_state = {}


# =====================================================
# 그래프 데이터
# =====================================================

current_history = None

temperature_lines = []

humidity_lines = []

temperature_annotation = None

humidity_annotation = None


# =====================================================
# Device의 Variable ID 읽기
# =====================================================

def load_variable_ids():

    global variable_ids

    variable_ids = {}

    for device_label in DEVICES:

        try:

            url = f"{BASE_URL}/{device_label}"

            response = requests.get(
                url,
                headers=HEADERS,
                timeout=10,
            )

            response.raise_for_status()

            device = response.json()

            variables_url = device.get(
                "variables_url"
            )

            if not variables_url:

                print(
                    f"{device_label}: "
                    "variables_url 없음"
                )

                continue


            response = requests.get(
                variables_url,
                headers=HEADERS,
                timeout=10,
            )

            response.raise_for_status()

            variables = response.json()


            variable_ids[device_label] = {}


            for variable in variables.get(
                "results",
                []
            ):

                label = variable.get(
                    "label"
                )

                variable_id = variable.get(
                    "id"
                )


                if label in (
                    "temperature",
                    "humidity",
                ):

                    variable_ids[
                        device_label
                    ][label] = variable_id


            print(
                f"{device_label}: "
                f"{variable_ids[device_label]}"
            )


        except Exception as e:

            print(
                f"Variable ID 오류 "
                f"{device_label}: {e}"
            )


# =====================================================
# 정상 / 비정상 판단
# =====================================================

def check_sensor_normal(
    temperature,
    humidity
):

    if temperature is None:
        return False

    if humidity is None:
        return False


    if not (
        TEMP_MIN
        <= temperature
        <= TEMP_MAX
    ):

        return False


    if not (
        HUMIDITY_MIN
        <= humidity
        <= HUMIDITY_MAX
    ):

        return False


    return True


# =====================================================
# 현재값 가져오기
# =====================================================

def get_current_values():

    for device_label in DEVICES:

        try:

            url = f"{BASE_URL}/{device_label}"


            response = requests.get(
                url,
                headers=HEADERS,
                timeout=5,
            )

            response.raise_for_status()

            device = response.json()


            variables_url = device.get(
                "variables_url"
            )


            response = requests.get(
                variables_url,
                headers=HEADERS,
                timeout=5,
            )

            response.raise_for_status()

            variables = response.json()


            temperature = None

            humidity = None


            for variable in variables.get(
                "results",
                []
            ):

                label = variable.get(
                    "label"
                )

                last_value = variable.get(
                    "last_value"
                )


                if not last_value:
                    continue


                value = last_value.get(
                    "value"
                )


                if label == "temperature":

                    temperature = value


                elif label == "humidity":

                    humidity = value


            normal = check_sensor_normal(
                temperature,
                humidity
            )


            sensor_data[
                device_label
            ]["temperature"] = temperature


            sensor_data[
                device_label
            ]["humidity"] = humidity


            sensor_data[
                device_label
            ]["normal"] = normal


            if normal:

                sensor_data[
                    device_label
                ]["status"] = "정상"

            else:

                sensor_data[
                    device_label
                ]["status"] = "비정상"


        except Exception as e:

            print(
                f"{device_label} "
                f"현재값 오류: {e}"
            )


            sensor_data[
                device_label
            ]["temperature"] = None


            sensor_data[
                device_label
            ]["humidity"] = None


            sensor_data[
                device_label
            ]["normal"] = False


            sensor_data[
                device_label
            ]["status"] = "통신 오류"


# =====================================================
# 과거 데이터 가져오기
# =====================================================

def get_history():

    global variable_ids


    if not variable_ids:

        load_variable_ids()


    ids = []


    for device_label in DEVICES:

        if device_label not in variable_ids:

            return {}


        if (
            "temperature"
            not in variable_ids[device_label]
        ):

            return {}


        if (
            "humidity"
            not in variable_ids[device_label]
        ):

            return {}


        ids.append(
            variable_ids[
                device_label
            ]["temperature"]
        )


        ids.append(
            variable_ids[
                device_label
            ]["humidity"]
        )


    # -------------------------------------------------
    # 시간 범위
    # -------------------------------------------------

    end_time = datetime.now()


    hours = PERIODS[
        selected_period
    ]["hours"]


    start_time = (
        end_time
        - timedelta(hours=hours)
    )


    start_ms = int(
        start_time.timestamp()
        * 1000
    )


    end_ms = int(
        end_time.timestamp()
        * 1000
    )


    period = PERIODS[
        selected_period
    ]["period"]


    # -------------------------------------------------
    # Ubidots 요청
    # -------------------------------------------------

    payload = {

        "variables": ids,

        "aggregation": "mean",

        "period": period,

        "join_dataframes": True,

        "start": start_ms,

        "end": end_ms,

        "tz": "Asia/Seoul",

        "precision": 2,
    }


    print(
        f"그래프 데이터 요청 "
        f"({selected_period})"
    )


    response = requests.post(
        RESAMPLE_URL,
        headers=HEADERS,
        json=payload,
        timeout=60,
    )


    response.raise_for_status()


    data = response.json()


    # -------------------------------------------------
    # 결과 저장 구조
    # -------------------------------------------------

    history = {}


    for device_label in DEVICES:

        history[device_label] = {

            "temperature": [],

            "humidity": [],
        }


    results = data.get(
        "results",
        []
    )


    # -------------------------------------------------
    # 데이터 해석
    # -------------------------------------------------

    for row in results:

        if not row:
            continue


        timestamp = row[0]


        dt = datetime.fromtimestamp(
            timestamp / 1000
        )


        index = 1


        for device_label in DEVICES:

            if index >= len(row):

                break


            temperature = row[index]


            humidity = None


            if index + 1 < len(row):

                humidity = row[
                    index + 1
                ]


            index += 2


            if temperature is not None:

                history[
                    device_label
                ]["temperature"].append(
                    (
                        dt,
                        temperature
                    )
                )


            if humidity is not None:

                history[
                    device_label
                ]["humidity"].append(
                    (
                        dt,
                        humidity
                    )
                )


    print(
        f"그래프 데이터 "
        f"{len(results)}개 구간 수신"
    )


    return history


# =====================================================
# X축 설정
# =====================================================

def configure_xaxis(ax):

    if selected_period == "24시간":

        ax.xaxis.set_major_locator(
            mdates.HourLocator(
                interval=2
            )
        )

        ax.xaxis.set_major_formatter(
            mdates.DateFormatter(
                "%m-%d %H:%M"
            )
        )


    elif selected_period == "1주일":

        ax.xaxis.set_major_locator(
            mdates.DayLocator(
                interval=1
            )
        )

        ax.xaxis.set_major_formatter(
            mdates.DateFormatter(
                "%m-%d"
            )
        )


    elif selected_period == "1개월":

        ax.xaxis.set_major_locator(
            mdates.DayLocator(
                interval=5
            )
        )

        ax.xaxis.set_major_formatter(
            mdates.DateFormatter(
                "%m-%d"
            )
        )


    # =================================================
    # X축 글자를 수평으로
    # =================================================

    ax.tick_params(
        axis="x",
        labelrotation=0
    )


    for label in ax.get_xticklabels():

        label.set_rotation(0)

        label.set_horizontalalignment(
            "center"
        )


# =====================================================
# 그래프 그리기
# =====================================================

def draw_graphs(history):

    global current_history

    global temperature_lines
    global humidity_lines

    global temperature_annotation
    global humidity_annotation


    current_history = history


    ax_temperature.clear()

    ax_humidity.clear()


    temperature_lines = []

    humidity_lines = []


    # =================================================
    # 온도 그래프
    # =================================================

    for (
        device_label,
        device_name
    ) in DEVICES.items():

        values = history.get(
            device_label,
            {}
        ).get(
            "temperature",
            []
        )


        if not values:

            continue


        times = [

            item[0]

            for item in values
        ]


        temperatures = [

            item[1]

            for item in values
        ]


        line, = ax_temperature.plot(

            times,

            temperatures,

            label=device_name,

            color=SENSOR_COLORS[
                device_label
            ],

            linewidth=1.8,
        )


        line.device_label = (
            device_label
        )

        line.sensor_name = (
            device_name
        )

        line.variable_name = (
            "온도"
        )


        temperature_lines.append(
            line
        )


    # -------------------------------------------------
    # 온도 제목
    # -------------------------------------------------

    ax_temperature.set_title(

        f"온도 추이  ({selected_period})",

        fontsize=15,

        fontweight="bold",

        pad=18,
    )


    ax_temperature.set_ylabel(
        "온도 (°C)"
    )


    ax_temperature.grid(
        True,
        alpha=0.3
    )


    ax_temperature.legend(
        loc="upper left"
    )


    configure_xaxis(
        ax_temperature
    )


    # =================================================
    # 습도 그래프
    # =================================================

    for (
        device_label,
        device_name
    ) in DEVICES.items():

        values = history.get(
            device_label,
            {}
        ).get(
            "humidity",
            []
        )


        if not values:

            continue


        times = [

            item[0]

            for item in values
        ]


        humidities = [

            item[1]

            for item in values
        ]


        line, = ax_humidity.plot(

            times,

            humidities,

            label=device_name,

            color=SENSOR_COLORS[
                device_label
            ],

            linewidth=1.8,
        )


        line.device_label = (
            device_label
        )

        line.sensor_name = (
            device_name
        )

        line.variable_name = (
            "습도"
        )


        humidity_lines.append(
            line
        )


    # -------------------------------------------------
    # 습도 제목
    # -------------------------------------------------

    ax_humidity.set_title(

        f"습도 추이  ({selected_period})",

        fontsize=15,

        fontweight="bold",

        pad=12,
    )


    ax_humidity.set_ylabel(
        "습도 (%)"
    )


    ax_humidity.grid(
        True,
        alpha=0.3
    )


    ax_humidity.legend(
        loc="upper left"
    )


    configure_xaxis(
        ax_humidity
    )


    # =================================================
    # 온도 Annotation
    # =================================================

    temperature_annotation = (
        ax_temperature.annotate(

            "",

            xy=(0, 0),

            xytext=(15, 15),

            textcoords="offset points",

            bbox=dict(

                boxstyle="round",

                fc="white",

                ec="gray",

                alpha=0.95,
            ),

            arrowprops=dict(
                arrowstyle="->"
            ),
        )
    )


    temperature_annotation.set_visible(
        False
    )


    # =================================================
    # 습도 Annotation
    # =================================================

    humidity_annotation = (
        ax_humidity.annotate(

            "",

            xy=(0, 0),

            xytext=(15, 15),

            textcoords="offset points",

            bbox=dict(

                boxstyle="round",

                fc="white",

                ec="gray",

                alpha=0.95,
            ),

            arrowprops=dict(
                arrowstyle="->"
            ),
        )
    )


    humidity_annotation.set_visible(
        False
    )


    # =================================================
    # 그래프 Layout
    # =================================================

    figure.subplots_adjust(

        left=0.08,

        right=0.98,

        # 제목 잘림 방지
        top=0.90,

        bottom=0.10,

        # 두 그래프 사이
        # 충분한 간격
        hspace=0.50,
    )


    canvas.draw_idle()


# =====================================================
# 가장 가까운 데이터 포인트 찾기
# =====================================================

def find_nearest_point(
    event,
    ax,
    lines
):

    if event.inaxes != ax:

        return None


    if event.xdata is None:

        return None


    best = None

    best_distance = float(
        "inf"
    )


    for line in lines:

        xdata = line.get_xdata(
            orig=False
        )

        ydata = line.get_ydata(
            orig=False
        )


        for index in range(
            len(xdata)
        ):

            x = xdata[index]

            y = ydata[index]


            try:

                display_point = (
                    ax.transData.transform(
                        (x, y)
                    )
                )


                distance = (

                    (
                        display_point[0]
                        - event.x
                    ) ** 2

                    +

                    (
                        display_point[1]
                        - event.y
                    ) ** 2

                )


                if distance < best_distance:

                    best_distance = distance

                    best = (
                        line,
                        index,
                        x,
                        y
                    )


            except Exception:

                pass


    if best is None:

        return None


    # 마우스가 너무 멀면 표시하지 않음

    if best_distance > 2500:

        return None


    return best


# =====================================================
# 마우스 이동
# =====================================================

def on_mouse_move(event):

    global temperature_annotation

    global humidity_annotation


    # =================================================
    # 온도
    # =================================================

    point = find_nearest_point(

        event,

        ax_temperature,

        temperature_lines
    )


    if point:

        line, index, x, y = point


        dt = mdates.num2date(
            x
        ).replace(
            tzinfo=None
        )


        temperature_annotation.xy = (
            x,
            y
        )


        temperature_annotation.set_text(

            f"{line.sensor_name}\n"

            f"{dt.strftime('%Y-%m-%d %H:%M')}\n"

            f"온도 : {y:.2f} °C"
        )


        temperature_annotation.set_visible(
            True
        )


    else:

        temperature_annotation.set_visible(
            False
        )


    # =================================================
    # 습도
    # =================================================

    point = find_nearest_point(

        event,

        ax_humidity,

        humidity_lines
    )


    if point:

        line, index, x, y = point


        dt = mdates.num2date(
            x
        ).replace(
            tzinfo=None
        )


        humidity_annotation.xy = (
            x,
            y
        )


        humidity_annotation.set_text(

            f"{line.sensor_name}\n"

            f"{dt.strftime('%Y-%m-%d %H:%M')}\n"

            f"습도 : {y:.2f} %"
        )


        humidity_annotation.set_visible(
            True
        )


    else:

        humidity_annotation.set_visible(
            False
        )


    canvas.draw_idle()


# =====================================================
# 현재 센서 카드 갱신
# =====================================================

def refresh_display():

    for device_label in DEVICES:

        data = sensor_data[
            device_label
        ]


        widgets = sensor_widgets[
            device_label
        ]


        temperature = data[
            "temperature"
        ]


        humidity = data[
            "humidity"
        ]


        normal = data[
            "normal"
        ]


        status = data[
            "status"
        ]


        # ---------------------------------------------
        # 온도
        # ---------------------------------------------

        if temperature is not None:

            widgets[
                "temperature"
            ].config(

                text=
                f"{temperature:.2f} °C"
            )


        else:

            widgets[
                "temperature"
            ].config(

                text=
                "--.-- °C"
            )


        # ---------------------------------------------
        # 습도
        # ---------------------------------------------

        if humidity is not None:

            widgets[
                "humidity"
            ].config(

                text=
                f"{humidity:.2f} %"
            )


        else:

            widgets[
                "humidity"
            ].config(

                text=
                "--.-- %"
            )


        # ---------------------------------------------
        # 상태
        # ---------------------------------------------

        if normal:

            widgets[
                "status"
            ].config(

                text="정상",

                fg="green"
            )


        else:

            widgets[
                "status"
            ].config(

                text=status,

                fg="red"
            )


    # -----------------------------------------------
    # 마지막 갱신
    # -----------------------------------------------

    update_time.config(

        text=(

            "마지막 갱신 : "

            + time.strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        )
    )


# =====================================================
# 원형 신호등 점멸
# =====================================================

def blink_warning_lamps():

    for device_label in DEVICES:

        data = sensor_data[
            device_label
        ]


        lamp_data = warning_lamps.get(
            device_label
        )


        if lamp_data is None:

            continue


        lamp_canvas, lamp_circle = (
            lamp_data
        )


        # =================================================
        # 정상
        # =================================================

        if data["normal"]:

            lamp_canvas.itemconfig(

                lamp_circle,

                fill="green",

                outline="darkgreen"
            )


        # =================================================
        # 비정상
        # =================================================

        else:

            current = (
                warning_blink_state.get(
                    device_label,
                    False
                )
            )


            if current:

                lamp_canvas.itemconfig(

                    lamp_circle,

                    fill="red",

                    outline="darkred"
                )


            else:

                lamp_canvas.itemconfig(

                    lamp_circle,

                    fill="white",

                    outline="red"
                )


            warning_blink_state[
                device_label
            ] = not current


    # 0.5초마다 실행

    root.after(
        500,
        blink_warning_lamps
    )


# =====================================================
# 현재값 수집 Thread
# =====================================================

def current_data_thread():

    while True:

        get_current_values()


        # GUI Thread에서 실행

        root.after(
            0,
            refresh_display
        )


        # 10초

        time.sleep(10)


# =====================================================
# 그래프 업데이트 Thread
# =====================================================

def graph_update_thread():

    try:

        history = get_history()


        root.after(

            0,

            lambda h=history:
            draw_graphs(h)
        )


    except Exception as e:

        print(
            "그래프 업데이트 오류:",
            e
        )


# =====================================================
# 그래프 업데이트 시작
# =====================================================

def start_graph_update():

    thread = threading.Thread(

        target=graph_update_thread,

        daemon=True
    )


    thread.start()


# =====================================================
# 그래프 5분 자동 갱신
# =====================================================

def automatic_graph_refresh():

    start_graph_update()


    root.after(

        5 * 60 * 1000,

        automatic_graph_refresh
    )


# =====================================================
# 기간 변경
# =====================================================

def change_period(period):

    global selected_period


    selected_period = period


    # 버튼 상태 변경

    for (
        name,
        button
    ) in period_buttons.items():

        if name == period:

            button.config(
                relief="sunken"
            )

        else:

            button.config(
                relief="raised"
            )


    # 그래프 즉시 갱신

    start_graph_update()


# =====================================================
# GUI 시작
# =====================================================

root = tk.Tk()


root.title(
    "Ubidots 온습도 모니터"
)


root.geometry(
    "1200x950"
)


root.minsize(
    1000,
    800
)


# =====================================================
# 제목
# =====================================================

title = tk.Label(

    root,

    text=
    "UBIDOTS 온습도 모니터",

    font=(
        "Arial",
        24,
        "bold"
    )
)


title.pack(
    pady=(15, 3)
)


# =====================================================
# 마지막 갱신 시간
# =====================================================

update_time = tk.Label(

    root,

    text=
    "마지막 갱신 : --",

    font=(
        "Arial",
        10
    )
)


update_time.pack(
    pady=(0, 10)
)


# =====================================================
# 센서 카드 영역
# =====================================================

cards_frame = tk.Frame(
    root
)


cards_frame.pack(

    fill="x",

    padx=15,

    pady=5
)


# =====================================================
# 센서 카드 3개
# =====================================================

for column, (
    device_label,
    device_name
) in enumerate(
    DEVICES.items()
):

    # =================================================
    # 전체 카드
    # =================================================

    card = tk.Frame(

        cards_frame,

        relief="solid",

        borderwidth=1
    )


    card.grid(

        row=0,

        column=column,

        sticky="nsew",

        padx=6
    )


    cards_frame.columnconfigure(

        column,

        weight=1
    )


    # =================================================
    # 카드 내부
    #
    # 센서 : 측정값 = 3 : 7
    # =================================================

    card.columnconfigure(
        0,
        weight=3
    )


    card.columnconfigure(
        1,
        weight=7
    )


    # =================================================
    # 왼쪽 30%
    # =================================================

    left_frame = tk.Frame(
        card
    )


    left_frame.grid(

        row=0,

        column=0,

        sticky="nsew",

        padx=(10, 5),

        pady=10
    )


    # =================================================
    # 센서 번호 / 종류
    # =================================================

    sensor_number, sensor_type = (
        SENSOR_NAMES[
            device_label
        ]
    )


    sensor_number_label = tk.Label(

        left_frame,

        text=sensor_number,

        font=(
            "Arial",
            18,
            "bold"
        )
    )


    sensor_number_label.pack(

        pady=(5, 0)
    )


    sensor_type_label = tk.Label(

        left_frame,

        text=sensor_type,

        font=(
            "Arial",
            11,
            "bold"
        )
    )


    sensor_type_label.pack(

        pady=(2, 10)
    )


    # =================================================
    # 원형 신호등
    # =================================================

    lamp_canvas = tk.Canvas(

        left_frame,

        width=32,

        height=32,

        highlightthickness=0,

        bg=left_frame.cget(
            "bg"
        )
    )


    lamp_canvas.pack(

        pady=(5, 2)
    )


    lamp_circle = (
        lamp_canvas.create_oval(

            5,

            5,

            27,

            27,

            fill="green",

            outline="darkgreen",

            width=1
        )
    )


    warning_lamps[
        device_label
    ] = (

        lamp_canvas,

        lamp_circle
    )


    warning_blink_state[
        device_label
    ] = False


    # =================================================
    # 상태 글자
    # =================================================

    status_label = tk.Label(

        left_frame,

        text="정상",

        font=(
            "Arial",
            10,
            "bold"
        ),

        fg="green"
    )


    status_label.pack()


    # =================================================
    # 오른쪽 70%
    # =================================================

    right_frame = tk.Frame(
        card
    )


    right_frame.grid(

        row=0,

        column=1,

        sticky="nsew",

        padx=(5, 10),

        pady=8
    )


    # =================================================
    # 온도
    # =================================================

    temperature_title = tk.Label(

        right_frame,

        text="온도",

        font=(
            "Arial",
            11
        )
    )


    temperature_title.pack(

        pady=(2, 0)
    )


    temperature_label = tk.Label(

        right_frame,

        text="--.-- °C",

        font=(
            "Arial",
            19,
            "bold"
        )
    )


    temperature_label.pack(

        pady=(0, 4)
    )


    # =================================================
    # 구분선
    # =================================================

    separator = tk.Frame(

        right_frame,

        height=1,

        bg="gray"
    )


    separator.pack(

        fill="x",

        padx=5,

        pady=3
    )


    # =================================================
    # 습도
    # =================================================

    humidity_title = tk.Label(

        right_frame,

        text="습도",

        font=(
            "Arial",
            11
        )
    )


    humidity_title.pack(

        pady=(2, 0)
    )


    humidity_label = tk.Label(

        right_frame,

        text="--.-- %",

        font=(
            "Arial",
            19,
            "bold"
        )
    )


    humidity_label.pack(

        pady=(0, 3)
    )


    # =================================================
    # Widget 저장
    # =================================================

    sensor_widgets[
        device_label
    ] = {

        "temperature":
            temperature_label,

        "humidity":
            humidity_label,

        "status":
            status_label,
    }


# =====================================================
# 기간 버튼
# =====================================================

period_frame = tk.Frame(
    root
)


period_frame.pack(
    pady=10
)


period_buttons = {}


for period in PERIODS:

    button = tk.Button(

        period_frame,

        text=period,

        width=10,

        font=(
            "Arial",
            11,
            "bold"
        ),

        command=lambda p=period:
        change_period(p)
    )


    button.pack(

        side="left",

        padx=5
    )


    period_buttons[
        period
    ] = button


# 24시간 기본 선택

period_buttons[
    "24시간"
].config(
    relief="sunken"
)


# =====================================================
# Matplotlib Figure
# =====================================================

figure, (
    ax_temperature,
    ax_humidity
) = plt.subplots(

    2,

    1,

    figsize=(
        11,
        7
    )
)


canvas = FigureCanvasTkAgg(

    figure,

    master=root
)


canvas.get_tk_widget().pack(

    fill="both",

    expand=True,

    padx=15,

    pady=5
)


# =====================================================
# 마우스 이벤트
# =====================================================

canvas.mpl_connect(

    "motion_notify_event",

    on_mouse_move
)


# =====================================================
# Variable ID 확인
# =====================================================

load_variable_ids()


# =====================================================
# 현재값 Thread 시작
# =====================================================

current_thread = threading.Thread(

    target=current_data_thread,

    daemon=True
)


current_thread.start()


# =====================================================
# 최초 그래프
# =====================================================

start_graph_update()


# =====================================================
# 그래프 5분 자동 갱신
# =====================================================

root.after(

    5 * 60 * 1000,

    automatic_graph_refresh
)


# =====================================================
# 신호등 시작
# =====================================================

root.after(

    500,

    blink_warning_lamps
)


# =====================================================
# GUI 실행
# =====================================================

root.mainloop()