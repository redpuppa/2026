# ============================================================
# UBIDOTS 온습도 모니터
# Android / Pydroid 3 / Kivy
#
# 최종 버전
#
# 기능
#   1. Ubidots 현재 온습도 표시
#   2. 센서 3개 상태 표시
#   3. timestamp 기반 센서 생존 여부 판단
#   4. 온습도 정상 범위 판단
#   5. 온도 그래프
#   6. 습도 그래프
#   7. 24시간 / 1주일 / 1개월
#
# 센서 카드의 센서명/온도/습도 글자색
#   → 아래 그래프의 센서 색상과 동일
#
# 센서 상태
#   최근 데이터 + 정상 범위
#       → 정상
#
#   최근 데이터 + 범위 이상
#       → 비정상
#
#   마지막 데이터가 30초 이상 오래됨
#       → 센서 응답 없음
#
#   Ubidots 통신 오류
#       → 통신 오류
# ============================================================


import threading
import time

from datetime import datetime, timedelta

import requests


# ============================================================
# Kivy
# ============================================================

from kivy.app import App
from kivy.clock import Clock

from kivy.graphics import (
    Color,
    Ellipse,
    Line,
    Rectangle
)

from kivy.metrics import dp

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget

from kivy.core.text import Label as CoreLabel
from kivy.core.window import Window


# ============================================================
# 한글 폰트
# ============================================================

FONT_PATH = (
    "/system/fonts/NotoSansCJK-Regular.ttc"
)


# ============================================================
# Ubidots Token
# ============================================================

try:

    from ubidots_secrets import UBIDOTS_TOKEN

except Exception:

    UBIDOTS_TOKEN = ""


# ============================================================
# Ubidots 설정
# ============================================================

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


# ============================================================
# Device
# ============================================================

DEVICES = {

    "d1mini-sht30-01":
        "센서 1  SHT30",

    "d1mini-sht30-02":
        "센서 2  SHT30",

    "d1mini-dht11-02":
        "센서 3  DHT11",
}


# ============================================================
# 센서 이름
# ============================================================

SENSOR_NAMES = {

    "d1mini-sht30-01":
        ("센서 1", "SHT30"),

    "d1mini-sht30-02":
        ("센서 2", "SHT30"),

    "d1mini-dht11-02":
        ("센서 3", "DHT11"),
}


# ============================================================
# 센서별 그래프 색상
#
# ★ 카드의 글자색도 이 색상을 사용한다.
# ============================================================

SENSOR_COLORS = {

    # 센서 1 → 파란색
    "d1mini-sht30-01":
        (0.10, 0.45, 0.90, 1),

    # 센서 2 → 주황색
    "d1mini-sht30-02":
        (1.00, 0.45, 0.05, 1),

    # 센서 3 → 초록색
    "d1mini-dht11-02":
        (0.10, 0.65, 0.15, 1),
}


# ============================================================
# 정상 범위
# ============================================================

TEMP_MIN = 0.0
TEMP_MAX = 50.0

HUMIDITY_MIN = 20.0
HUMIDITY_MAX = 80.0


# ============================================================
# 센서 생존 판정
# ============================================================

MAX_DATA_AGE = 30


# ============================================================
# 그래프 기간
# ============================================================

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


# ============================================================
# 현재 센서 데이터
# ============================================================

sensor_data = {}


for device_label in DEVICES:

    sensor_data[device_label] = {

        "temperature": None,

        "humidity": None,

        "status": "연결 대기",

        "normal": False,
    }


# ============================================================
# Variable ID
# ============================================================

variable_ids = {}


# ============================================================
# 그래프 데이터
# ============================================================

current_history = {}


# ============================================================
# 그래프 요청 Lock
# ============================================================

graph_lock = threading.Lock()


# ============================================================
# 정상 여부
# ============================================================

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


# ============================================================
# Device Variable ID 읽기
# ============================================================

def load_variable_ids():

    global variable_ids


    variable_ids = {}


    for device_label in DEVICES:

        try:

            url = (
                f"{BASE_URL}/{device_label}"
            )


            response = requests.get(

                url,

                headers=HEADERS,

                timeout=10
            )


            response.raise_for_status()


            device = response.json()


            variables_url = device.get(
                "variables_url"
            )


            if not variables_url:

                print(

                    device_label,

                    "variables_url 없음"
                )

                continue


            response = requests.get(

                variables_url,

                headers=HEADERS,

                timeout=10
            )


            response.raise_for_status()


            variables = response.json()


            variable_ids[
                device_label
            ] = {}


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

                device_label,

                variable_ids[
                    device_label
                ]
            )


        except Exception as e:

            print(

                "Variable ID 오류:",

                device_label,

                e
            )


# ============================================================
# 현재값 가져오기
# ============================================================

def get_current_values():

    if not UBIDOTS_TOKEN:

        print(
            "UBIDOTS_TOKEN이 없습니다."
        )

        return


    for device_label in DEVICES:

        try:

            # =================================================
            # Device
            # =================================================

            url = (
                f"{BASE_URL}/{device_label}"
            )


            response = requests.get(

                url,

                headers=HEADERS,

                timeout=10
            )


            response.raise_for_status()


            device = response.json()


            variables_url = device.get(
                "variables_url"
            )


            if not variables_url:

                raise Exception(
                    "variables_url 없음"
                )


            # =================================================
            # Variables
            # =================================================

            response = requests.get(

                variables_url,

                headers=HEADERS,

                timeout=10
            )


            response.raise_for_status()


            variables = response.json()


            temperature = None

            humidity = None

            temperature_timestamp = None

            humidity_timestamp = None


            # =================================================
            # 온도 / 습도
            # =================================================

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


                timestamp = last_value.get(
                    "timestamp"
                )


                if label == "temperature":

                    temperature = value

                    temperature_timestamp = (
                        timestamp
                    )


                elif label == "humidity":

                    humidity = value

                    humidity_timestamp = (
                        timestamp
                    )


            # =================================================
            # timestamp 확인
            # =================================================

            if (

                temperature_timestamp is None

                or

                humidity_timestamp is None

            ):

                sensor_data[
                    device_label
                ]["temperature"] = temperature


                sensor_data[
                    device_label
                ]["humidity"] = humidity


                sensor_data[
                    device_label
                ]["normal"] = False


                sensor_data[
                    device_label
                ]["status"] = (
                    "센서 응답 없음"
                )


                continue


            # =================================================
            # timestamp → seconds
            # =================================================

            now = time.time()


            temperature_time = (

                float(
                    temperature_timestamp
                )
                /
                1000.0
            )


            humidity_time = (

                float(
                    humidity_timestamp
                )
                /
                1000.0
            )


            temperature_age = (

                now
                -
                temperature_time
            )


            humidity_age = (

                now
                -
                humidity_time
            )


            # =================================================
            # 센서 생존 여부
            # =================================================

            if (

                temperature_age
                > MAX_DATA_AGE

                or

                humidity_age
                > MAX_DATA_AGE

            ):

                sensor_data[
                    device_label
                ]["temperature"] = temperature


                sensor_data[
                    device_label
                ]["humidity"] = humidity


                sensor_data[
                    device_label
                ]["normal"] = False


                sensor_data[
                    device_label
                ]["status"] = (
                    "센서 응답 없음"
                )


                print(

                    device_label,

                    "센서 응답 없음",

                    f"T={temperature_age:.1f}s",

                    f"H={humidity_age:.1f}s"
                )


                continue


            # =================================================
            # 온습도 정상 여부
            # =================================================

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


            print(

                device_label,

                f"T={temperature}",

                f"H={humidity}",

                f"age={temperature_age:.1f}s"
            )


        except Exception as e:

            print(

                device_label,

                "통신 오류:",

                e
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
            ]["status"] = (
                "통신 오류"
            )


# ============================================================
# 과거 데이터
# ============================================================

def get_history():

    global variable_ids


    if not variable_ids:

        load_variable_ids()


    ids = []


    for device_label in DEVICES:

        if device_label not in variable_ids:

            print(

                "Variable ID 없음:",

                device_label
            )

            return {}


        if (

            "temperature"

            not in

            variable_ids[
                device_label
            ]

        ):

            print(

                "temperature ID 없음:",

                device_label
            )

            return {}


        if (

            "humidity"

            not in

            variable_ids[
                device_label
            ]

        ):

            print(

                "humidity ID 없음:",

                device_label
            )

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


    # ========================================================
    # 시간
    # ========================================================

    end_time = datetime.now()


    hours = PERIODS[
        selected_period
    ]["hours"]


    start_time = (

        end_time
        -
        timedelta(
            hours=hours
        )
    )


    start_ms = int(

        start_time.timestamp()
        *
        1000
    )


    end_ms = int(

        end_time.timestamp()
        *
        1000
    )


    period = PERIODS[
        selected_period
    ]["period"]


    print()

    print(
        "================================"
    )

    print(
        "그래프 요청:",
        selected_period
    )

    print(
        "시작:",
        start_time
    )

    print(
        "종료:",
        end_time
    )

    print(
        "================================"
    )


    # ========================================================
    # Ubidots Resample
    # ========================================================

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


    response = requests.post(

        RESAMPLE_URL,

        headers=HEADERS,

        json=payload,

        timeout=60
    )


    response.raise_for_status()


    data = response.json()


    results = data.get(

        "results",

        []
    )


    print(

        "Resample 결과:",

        len(results),

        "개"
    )


    # ========================================================
    # History 초기화
    # ========================================================

    history = {}


    for device_label in DEVICES:

        history[device_label] = {

            "temperature": [],

            "humidity": [],
        }


    # ========================================================
    # Resample 데이터
    #
    # [timestamp,
    #  T1,H1,
    #  T2,H2,
    #  T3,H3]
    # ========================================================

    for row in results:

        if not row:

            continue


        if len(row) < 7:

            print(

                "잘못된 row:",

                row
            )

            continue


        # ====================================================
        # timestamp
        # ====================================================

        try:

            timestamp = float(
                row[0]
            )


            dt = datetime.fromtimestamp(

                timestamp / 1000.0
            )


        except Exception as e:

            print(

                "timestamp 오류:",

                e
            )

            continue


        # ====================================================
        # 센서 1
        # ====================================================

        add_history_value(

            history,

            "d1mini-sht30-01",

            dt,

            row[1],

            row[2]
        )


        # ====================================================
        # 센서 2
        # ====================================================

        add_history_value(

            history,

            "d1mini-sht30-02",

            dt,

            row[3],

            row[4]
        )


        # ====================================================
        # 센서 3
        # ====================================================

        add_history_value(

            history,

            "d1mini-dht11-02",

            dt,

            row[5],

            row[6]
        )


    # ========================================================
    # 시간순 정렬
    # ========================================================

    for device_label in DEVICES:

        history[
            device_label
        ]["temperature"].sort(

            key=lambda item: item[0]
        )


        history[
            device_label
        ]["humidity"].sort(

            key=lambda item: item[0]
        )


    # ========================================================
    # 데이터 확인
    # ========================================================

    print()

    print(
        "========== GRAPH DATA =========="
    )


    for device_label in DEVICES:

        print(

            device_label,

            "T:",

            len(

                history[
                    device_label
                ]["temperature"]
            ),

            "H:",

            len(

                history[
                    device_label
                ]["humidity"]
            )
        )


    print(
        "================================"
    )


    return history


# ============================================================
# History 데이터 추가
# ============================================================

def add_history_value(

    history,

    device_label,

    dt,

    temperature,

    humidity

):

    if temperature is not None:

        try:

            history[
                device_label
            ]["temperature"].append(

                (

                    dt,

                    float(
                        temperature
                    )
                )
            )

        except Exception:

            pass


    if humidity is not None:

        try:

            history[
                device_label
            ]["humidity"].append(

                (

                    dt,

                    float(
                        humidity
                    )
                )
            )

        except Exception:

            pass


# ============================================================
# 그래프 Widget
# ============================================================

class SensorGraph(Widget):

    def __init__(

        self,

        graph_type="temperature",

        **kwargs

    ):

        super().__init__(**kwargs)


        self.graph_type = graph_type

        self.history = {}


        self.bind(

            pos=self.redraw,

            size=self.redraw
        )


    # ========================================================
    # 데이터 설정
    # ========================================================

    def set_history(

        self,

        history

    ):

        self.history = history

        self.redraw()


    # ========================================================
    # 텍스트
    # ========================================================

    def draw_text(

        self,

        text,

        x,

        y,

        font_size=12,

        text_color=None

    ):

        label = CoreLabel(

            text=str(text),

            font_name=FONT_PATH,

            font_size=dp(font_size)
        )


        label.refresh()


        if text_color is None:

            text_color = (

                0.1,
                0.1,
                0.1,
                1
            )


        Color(
            *text_color
        )


        Rectangle(

            texture=label.texture,

            pos=(x, y),

            size=label.texture.size
        )


    # ========================================================
    # 그래프
    # ========================================================

    def redraw(

        self,

        *args

    ):

        self.canvas.clear()


        # ====================================================
        # 배경
        # ====================================================

        with self.canvas:

            Color(

                1,
                1,
                1,
                1
            )


            Rectangle(

                pos=self.pos,

                size=self.size
            )


        # ====================================================
        # 그래프 영역
        # ====================================================

        left = (

            self.x
            +
            dp(45)
        )


        right = (

            self.right
            -
            dp(15)
        )


        bottom = (

            self.y
            +
            dp(30)
        )


        top = (

            self.top
            -
            dp(40)
        )


        width = right - left

        height = top - bottom


        if width <= 0 or height <= 0:

            return


        # ====================================================
        # 제목
        # ====================================================

        if self.graph_type == "temperature":

            title = (

                f"온도 추이 ({selected_period})"
            )

        else:

            title = (

                f"습도 추이 ({selected_period})"
            )


        with self.canvas:

            self.draw_text(

                title,

                self.x + dp(10),

                self.top - dp(28),

                15
            )


        # ====================================================
        # Y축
        # ====================================================

        if self.graph_type == "temperature":

            ymin = 0.0

            ymax = 50.0

        else:

            ymin = 0.0

            ymax = 100.0


        # ====================================================
        # Grid
        # ====================================================

        with self.canvas:

            Color(

                0.82,
                0.82,
                0.82,
                1
            )


            for i in range(6):

                value = (

                    ymin
                    +
                    (
                        ymax - ymin
                    )
                    *
                    i
                    /
                    5
                )


                py = (

                    bottom
                    +
                    height
                    *
                    i
                    /
                    5
                )


                Line(

                    points=[

                        left,
                        py,
                        right,
                        py
                    ],

                    width=1
                )


                self.draw_text(

                    f"{value:g}",

                    self.x + dp(5),

                    py - dp(7),

                    9
                )


        # ====================================================
        # 모든 데이터
        # ====================================================

        all_values = []


        for device_label in DEVICES:

            values = (

                self.history.get(

                    device_label,

                    {}
                ).get(

                    self.graph_type,

                    []
                )
            )


            all_values.extend(
                values
            )


        # ====================================================
        # 데이터 없음
        # ====================================================

        if not all_values:

            with self.canvas:

                self.draw_text(

                    "데이터 없음",

                    left + dp(20),

                    bottom + height / 2,

                    14
                )


            return


        # ====================================================
        # 전체 시간 범위
        # ====================================================

        min_time = min(

            item[0]

            for item in all_values
        )


        max_time = max(

            item[0]

            for item in all_values
        )


        total_seconds = (

            max_time
            -
            min_time
        ).total_seconds()


        if total_seconds <= 0:

            total_seconds = 1


        # ====================================================
        # 센서별 선
        # ====================================================

        for device_label in DEVICES:

            values = (

                self.history.get(

                    device_label,

                    {}
                ).get(

                    self.graph_type,

                    []
                )
            )


            if len(values) < 2:

                continue


            # =================================================
            # 센서 색상
            # =================================================

            color = SENSOR_COLORS[
                device_label
            ]


            points = []


            for dt, value in values:

                try:

                    value = float(value)

                except Exception:

                    continue


                # ---------------------------------------------
                # X
                # ---------------------------------------------

                x_ratio = (

                    (
                        dt
                        -
                        min_time
                    ).total_seconds()
                    /
                    total_seconds
                )


                px = (

                    left
                    +
                    width
                    *
                    x_ratio
                )


                # ---------------------------------------------
                # Y
                # ---------------------------------------------

                y_ratio = (

                    value
                    -
                    ymin
                ) / (

                    ymax
                    -
                    ymin
                )


                y_ratio = max(

                    0.0,

                    min(
                        1.0,
                        y_ratio
                    )
                )


                py = (

                    bottom
                    +
                    height
                    *
                    y_ratio
                )


                points.extend(

                    [
                        px,
                        py
                    ]
                )


            # =================================================
            # 선
            # =================================================

            if len(points) >= 4:

                with self.canvas:

                    Color(
                        *color
                    )


                    Line(

                        points=points,

                        width=dp(1.5)
                    )


        # ====================================================
        # X축
        # ====================================================

        with self.canvas:

            Color(

                0.25,
                0.25,
                0.25,
                1
            )


            Line(

                points=[

                    left,
                    bottom,
                    right,
                    bottom
                ],

                width=1
            )


        # ====================================================
        # X축 시간
        # ====================================================

        with self.canvas:

            self.draw_text(

                min_time.strftime(
                    "%m-%d %H:%M"
                ),

                left,

                self.y + dp(8),

                8
            )


            max_text = (

                max_time.strftime(
                    "%m-%d %H:%M"
                )
            )


            self.draw_text(

                max_text,

                right - dp(75),

                self.y + dp(8),

                8
            )


# ============================================================
# 센서 카드
# ============================================================

class SensorCard(BoxLayout):

    def __init__(

        self,

        device_label,

        **kwargs

    ):

        super().__init__(

            orientation="horizontal",

            **kwargs
        )


        self.device_label = device_label


        self.padding = dp(8)

        self.spacing = dp(5)


        # ====================================================
        # ★ 센서별 색상
        # ====================================================

        self.sensor_color = SENSOR_COLORS[
            device_label
        ]


        # ====================================================
        # 카드 배경
        # ====================================================

        with self.canvas.before:

            Color(

                0.88,
                0.88,
                0.88,
                1
            )


            self.card_background = Rectangle(

                pos=self.pos,

                size=self.size
            )


        self.bind(

            pos=self.update_background,

            size=self.update_background
        )


        # ====================================================
        # 왼쪽 30%
        # ====================================================

        left = BoxLayout(

            orientation="vertical",

            size_hint_x=0.3
        )


        sensor_number, sensor_type = (

            SENSOR_NAMES[
                device_label
            ]
        )


        # ====================================================
        # ★ 센서 번호
        # 그래프 색상과 동일
        # ====================================================

        self.sensor_label = Label(

            text=sensor_number,

            font_name=FONT_PATH,

            font_size=dp(18),

            bold=True,

            color=self.sensor_color
        )


        left.add_widget(
            self.sensor_label
        )


        # ====================================================
        # ★ 센서 종류
        # 그래프 색상과 동일
        # ====================================================

        self.type_label = Label(

            text=sensor_type,

            font_name=FONT_PATH,

            font_size=dp(11),

            bold=True,

            color=self.sensor_color
        )


        left.add_widget(
            self.type_label
        )


        # ====================================================
        # 신호등
        # ====================================================

        self.lamp = Widget(

            size_hint_y=None,

            height=dp(40)
        )


        self.lamp.bind(

            pos=self.draw_lamp,

            size=self.draw_lamp
        )


        left.add_widget(
            self.lamp
        )


        # ====================================================
        # 상태
        # ====================================================

        self.status_label = Label(

            text="연결 대기",

            font_name=FONT_PATH,

            font_size=dp(10),

            bold=True,

            color=(

                0.1,
                0.6,
                0.1,
                1
            )
        )


        left.add_widget(
            self.status_label
        )


        self.add_widget(left)


        # ====================================================
        # 오른쪽 70%
        # ====================================================

        right = BoxLayout(

            orientation="vertical",

            size_hint_x=0.7
        )


        # ====================================================
        # ★ 온도 제목
        # 센서별 그래프 색상과 동일
        # ====================================================

        self.temperature_title = Label(

            text="온도",

            font_name=FONT_PATH,

            font_size=dp(11),

            color=self.sensor_color,

            size_hint_y=0.22
        )


        right.add_widget(

            self.temperature_title
        )


        # ====================================================
        # ★ 온도 값
        # 센서별 그래프 색상과 동일
        # ====================================================

        self.temperature_label = Label(

            text="--.-- °C",

            font_name=FONT_PATH,

            font_size=dp(18),

            bold=True,

            color=self.sensor_color,

            size_hint_y=0.30
        )


        right.add_widget(

            self.temperature_label
        )


        # ====================================================
        # 구분선
        # ====================================================

        separator = Widget(

            size_hint_y=None,

            height=dp(1)
        )


        with separator.canvas:

            Color(

                0.65,
                0.65,
                0.65,
                1
            )


            Rectangle(

                pos=separator.pos,

                size=separator.size
            )


        separator.bind(

            pos=lambda obj, value:

            self.update_separator(
                separator
            ),

            size=lambda obj, value:

            self.update_separator(
                separator
            )
        )


        right.add_widget(separator)


        # ====================================================
        # ★ 습도 제목
        # 센서별 그래프 색상과 동일
        # ====================================================

        self.humidity_title = Label(

            text="습도",

            font_name=FONT_PATH,

            font_size=dp(11),

            color=self.sensor_color,

            size_hint_y=0.22
        )


        right.add_widget(

            self.humidity_title
        )


        # ====================================================
        # ★ 습도 값
        # 센서별 그래프 색상과 동일
        # ====================================================

        self.humidity_label = Label(

            text="--.-- %",

            font_name=FONT_PATH,

            font_size=dp(18),

            bold=True,

            color=self.sensor_color,

            size_hint_y=0.30
        )


        right.add_widget(

            self.humidity_label
        )


        self.add_widget(right)


        self.blink_state = False


    # ========================================================
    # 카드 배경
    # ========================================================

    def update_background(

        self,

        *args

    ):

        self.card_background.pos = self.pos

        self.card_background.size = self.size


    # ========================================================
    # 구분선
    # ========================================================

    def update_separator(

        self,

        widget

    ):

        widget.canvas.clear()


        with widget.canvas:

            Color(

                0.65,
                0.65,
                0.65,
                1
            )


            Rectangle(

                pos=widget.pos,

                size=widget.size
            )


    # ========================================================
    # 신호등
    # ========================================================

    def draw_lamp(

        self,

        *args

    ):

        self.lamp.canvas.clear()


        data = sensor_data[
            self.device_label
        ]


        normal = data[
            "normal"
        ]


        with self.lamp.canvas:

            # -----------------------------------------------
            # 정상
            # -----------------------------------------------

            if normal:

                Color(

                    0.0,
                    0.65,
                    0.0,
                    1
                )


            # -----------------------------------------------
            # 비정상
            # -----------------------------------------------

            else:

                if self.blink_state:

                    Color(

                        1.0,
                        0.0,
                        0.0,
                        1
                    )

                else:

                    Color(

                        0.95,
                        0.95,
                        0.95,
                        1
                    )


            size = dp(24)


            Ellipse(

                pos=(

                    self.lamp.center_x
                    -
                    size / 2,

                    self.lamp.center_y
                    -
                    size / 2
                ),

                size=(

                    size,
                    size
                )
            )


    # ========================================================
    # 카드 데이터 갱신
    # ========================================================

    def update_data(

        self

    ):

        data = sensor_data[
            self.device_label
        ]


        temperature = data[
            "temperature"
        ]


        humidity = data[
            "humidity"
        ]


        # ====================================================
        # ★ 온도
        # ====================================================

        if temperature is not None:

            self.temperature_label.text = (

                f"{temperature:.2f} °C"
            )

        else:

            self.temperature_label.text = (
                "--.-- °C"
            )


        # ====================================================
        # ★ 습도
        # ====================================================

        if humidity is not None:

            self.humidity_label.text = (

                f"{humidity:.2f} %"
            )

        else:

            self.humidity_label.text = (
                "--.-- %"
            )


        # ====================================================
        # 상태
        # ====================================================

        status = data[
            "status"
        ]


        self.status_label.text = status


        if data["normal"]:

            self.status_label.color = (

                0.0,
                0.65,
                0.0,
                1
            )

        else:

            self.status_label.color = (

                0.85,
                0.05,
                0.05,
                1
            )


        self.draw_lamp()


# ============================================================
# 메인 App
# ============================================================

class UbidotsApp(App):

    def build(self):

        self.title = (
            "Ubidots 온습도 모니터"
        )


        Window.clearcolor = (

            1,
            1,
            1,
            1
        )


        # ====================================================
        # 전체 화면
        # ====================================================

        root = BoxLayout(

            orientation="vertical",

            padding=dp(10),

            spacing=dp(6)
        )


        # ====================================================
        # 제목
        # ====================================================

        root.add_widget(

            Label(

                text="UBIDOTS 온습도 모니터",

                font_name=FONT_PATH,

                font_size=dp(25),

                bold=True,

                color=(

                    0.03,
                    0.03,
                    0.03,
                    1
                ),

                size_hint_y=None,

                height=dp(48)
            )
        )


        # ====================================================
        # 마지막 갱신
        # ====================================================

        self.update_time = Label(

            text="마지막 갱신 : --",

            font_name=FONT_PATH,

            font_size=dp(10),

            color=(

                0.2,
                0.2,
                0.2,
                1
            ),

            size_hint_y=None,

            height=dp(25)
        )


        root.add_widget(
            self.update_time
        )


        # ====================================================
        # 센서 카드
        # ====================================================

        cards = GridLayout(

            cols=3,

            spacing=dp(6),

            size_hint_y=None,

            height=dp(190)
        )


        self.cards = {}


        for device_label in DEVICES:

            card = SensorCard(

                device_label
            )


            self.cards[
                device_label
            ] = card


            cards.add_widget(card)


        root.add_widget(cards)


        # ====================================================
        # 기간 버튼
        # ====================================================

        period_box = BoxLayout(

            orientation="horizontal",

            spacing=dp(6),

            size_hint_y=None,

            height=dp(48)
        )


        self.period_buttons = {}


        for period in PERIODS:

            button = Button(

                text=period,

                font_name=FONT_PATH,

                font_size=dp(13),

                background_normal="",

                background_color=(

                    0.25,
                    0.25,
                    0.25,
                    1
                )
            )


            button.bind(

                on_press=

                lambda btn,

                p=period:

                self.change_period(p)
            )


            self.period_buttons[
                period
            ] = button


            period_box.add_widget(button)


        root.add_widget(period_box)


        # ====================================================
        # 온도 그래프
        # ====================================================

        self.temperature_graph = (

            SensorGraph(

                "temperature"
            )
        )


        root.add_widget(

            self.temperature_graph
        )


        # ====================================================
        # 습도 그래프
        # ====================================================

        self.humidity_graph = (

            SensorGraph(

                "humidity"
            )
        )


        root.add_widget(

            self.humidity_graph
        )


        # ====================================================
        # 기본 버튼
        # ====================================================

        self.set_selected_button()


        # ====================================================
        # 현재값 Thread
        # ====================================================

        Clock.schedule_once(

            self.start_current_thread,

            0.5
        )


        # ====================================================
        # 최초 그래프
        # ====================================================

        Clock.schedule_once(

            self.start_graph_thread,

            1.0
        )


        # ====================================================
        # 화면 갱신
        # ====================================================

        Clock.schedule_interval(

            self.update_display,

            1
        )


        # ====================================================
        # 신호등
        # ====================================================

        Clock.schedule_interval(

            self.blink_lamps,

            0.5
        )


        # ====================================================
        # 그래프 자동 갱신
        # ====================================================

        Clock.schedule_interval(

            self.start_graph_thread,

            5 * 60
        )


        return root


    # ========================================================
    # 현재값 Thread 시작
    # ========================================================

    def start_current_thread(

        self,

        *args

    ):

        thread = threading.Thread(

            target=self.current_thread,

            daemon=True
        )


        thread.start()


    # ========================================================
    # 현재값 반복
    # ========================================================

    def current_thread(

        self

    ):

        while True:

            get_current_values()

            time.sleep(10)


    # ========================================================
    # 화면 갱신
    # ========================================================

    def update_display(

        self,

        dt

    ):

        for device_label in DEVICES:

            self.cards[
                device_label
            ].update_data()


        self.update_time.text = (

            "마지막 갱신 : "

            +

            datetime.now().strftime(

                "%Y-%m-%d %H:%M:%S"
            )
        )


    # ========================================================
    # 신호등
    # ========================================================

    def blink_lamps(

        self,

        dt

    ):

        for device_label in DEVICES:

            card = self.cards[
                device_label
            ]


            data = sensor_data[
                device_label
            ]


            if not data["normal"]:

                card.blink_state = (

                    not card.blink_state
                )

            else:

                card.blink_state = False


            card.draw_lamp()


    # ========================================================
    # 그래프 Thread
    # ========================================================

    def start_graph_thread(

        self,

        *args

    ):

        if graph_lock.locked():

            print(
                "그래프 요청 진행 중 → 새 요청 무시"
            )

            return


        thread = threading.Thread(

            target=self.graph_thread,

            daemon=True
        )


        thread.start()


    # ========================================================
    # 그래프 데이터 수집
    # ========================================================

    def graph_thread(

        self

    ):

        with graph_lock:

            try:

                history = get_history()


                print(
                    "그래프 데이터 수집 완료"
                )


                Clock.schedule_once(

                    lambda dt:

                    self.update_graphs(
                        history
                    ),

                    0
                )


            except Exception as e:

                print(

                    "그래프 오류:",

                    e
                )


    # ========================================================
    # 그래프 갱신
    # ========================================================

    def update_graphs(

        self,

        history

    ):

        global current_history


        if not history:

            print(
                "그래프 데이터 없음"
            )

            return


        current_history = history


        self.temperature_graph.set_history(

            history
        )


        self.humidity_graph.set_history(

            history
        )


    # ========================================================
    # 기간 변경
    # ========================================================

    def change_period(

        self,

        period

    ):

        global selected_period


        if period == selected_period:

            return


        selected_period = period


        print(

            "기간 변경:",

            selected_period
        )


        self.set_selected_button()


        self.start_graph_thread()


    # ========================================================
    # 선택 버튼
    # ========================================================

    def set_selected_button(

        self

    ):

        for (

            period,

            button

        ) in self.period_buttons.items():


            if period == selected_period:

                button.background_color = (

                    0.08,
                    0.25,
                    0.45,
                    1
                )

            else:

                button.background_color = (

                    0.30,
                    0.30,
                    0.30,
                    1
                )


# ============================================================
# 실행
# ============================================================

if __name__ == "__main__":

    UbidotsApp().run()