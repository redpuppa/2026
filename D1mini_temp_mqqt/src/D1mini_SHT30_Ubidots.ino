/*
  D1 mini Pro + SHT30
  → Wi-Fi
  → Ubidots MQTT

  SHT30 I2C address : 0x45
  SDA                : D2
  SCL                : D1
  전송 주기           : 10초
*/

#include <Arduino.h>
#include <Wire.h>
#include <ESP8266WiFi.h>
#include <ArduinoMqttClient.h>

#include "arduino_secrets.h"


// =====================================================
// SHT30
// =====================================================

#define SHT30_ADDR 0x45


// =====================================================
// Wi-Fi / MQTT
// =====================================================

WiFiClient wifiClient;
MqttClient mqttClient(wifiClient);


// =====================================================
// Ubidots
// =====================================================

const char broker[] =
  "industrial.api.ubidots.com";

const int port = 1883;


// =====================================================
// 전송 주기
// =====================================================

unsigned long previousMillis = 0;

const unsigned long interval = 10000;


// =====================================================
// 함수 선언
// =====================================================

bool readSHT30(
  float &temperature,
  float &humidity
);

void connectWiFi();

void connectMQTT();

void publishSensorData();


// =====================================================
// SETUP
// =====================================================

void setup() {

  Serial.begin(115200);

  delay(1000);

  Serial.println();
  Serial.println("================================");
  Serial.println(" D1 mini Pro + SHT30 + Ubidots");
  Serial.println("================================");


  // ---------------------------------------------------
  // I2C
  // ---------------------------------------------------

  Wire.begin(D2, D1);

  Serial.println("I2C 초기화 완료");


  // ---------------------------------------------------
  // SHT30 확인
  // ---------------------------------------------------

  Wire.beginTransmission(SHT30_ADDR);

  if (Wire.endTransmission() == 0) {

    Serial.println("SHT30 연결 성공!");

  } else {

    Serial.println("SHT30 연결 실패!");

    while (true) {
      delay(1000);
    }
  }


  // ---------------------------------------------------
  // Wi-Fi
  // ---------------------------------------------------

  connectWiFi();


  // ---------------------------------------------------
  // MQTT
  // ---------------------------------------------------

  connectMQTT();
}


// =====================================================
// LOOP
// =====================================================

void loop() {

  // MQTT 처리
  mqttClient.poll();


  // ---------------------------------------------------
  // Wi-Fi 연결 확인
  // ---------------------------------------------------

  if (WiFi.status() != WL_CONNECTED) {

    Serial.println();
    Serial.println("Wi-Fi 연결 끊김");

    connectWiFi();
  }


  // ---------------------------------------------------
  // MQTT 연결 확인
  // ---------------------------------------------------

  if (!mqttClient.connected()) {

    Serial.println();
    Serial.println("MQTT 연결 끊김");

    connectMQTT();
  }


  // ---------------------------------------------------
  // 10초마다 전송
  // ---------------------------------------------------

  unsigned long currentMillis =
    millis();


  if (
    currentMillis - previousMillis >= interval
  ) {

    previousMillis = currentMillis;

    publishSensorData();
  }
}


// =====================================================
// SHT30 측정
// =====================================================

bool readSHT30(
  float &temperature,
  float &humidity
) {

  // ---------------------------------------------------
  // SHT30 Single Shot Measurement
  //
  // High repeatability
  // Clock stretching enabled
  // ---------------------------------------------------

  Wire.beginTransmission(SHT30_ADDR);

  Wire.write(0x2C);
  Wire.write(0x06);

  if (Wire.endTransmission() != 0) {

    return false;
  }


  // 측정 완료 대기
  delay(20);


  // ---------------------------------------------------
  // 6 byte 수신
  //
  // Temperature MSB
  // Temperature LSB
  // Temperature CRC
  // Humidity MSB
  // Humidity LSB
  // Humidity CRC
  // ---------------------------------------------------

  if (Wire.requestFrom(SHT30_ADDR, 6) != 6) {

    return false;
  }


  uint16_t rawTemperature =
    ((uint16_t)Wire.read() << 8)
    | Wire.read();

  Wire.read();   // Temperature CRC


  uint16_t rawHumidity =
    ((uint16_t)Wire.read() << 8)
    | Wire.read();

  Wire.read();   // Humidity CRC


  // ---------------------------------------------------
  // SHT30 변환 공식
  // ---------------------------------------------------

  temperature =
    -45.0 +
    175.0 *
    ((float)rawTemperature / 65535.0);


  humidity =
    100.0 *
    ((float)rawHumidity / 65535.0);


  return true;
}


// =====================================================
// Wi-Fi 연결
// =====================================================

void connectWiFi() {

  Serial.println();
  Serial.println("Wi-Fi 연결 중...");


  WiFi.begin(
    SECRET_SSID,
    SECRET_PASS
  );


  while (
    WiFi.status() != WL_CONNECTED
  ) {

    delay(500);

    Serial.print(".");
  }


  Serial.println();
  Serial.println("Wi-Fi 연결 성공!");

  Serial.print("IP 주소: ");
  Serial.println(WiFi.localIP());
}


// =====================================================
// Ubidots MQTT 연결
// =====================================================

void connectMQTT() {

  Serial.println();
  Serial.println("Ubidots MQTT 브로커 연결...");


  // ---------------------------------------------------
  // Ubidots 인증
  //
  // Username = Token
  // Password = 빈 문자열
  // ---------------------------------------------------

  mqttClient.setUsernamePassword(
    UBIDOTS_TOKEN,
    ""
  );


  // ---------------------------------------------------
  // MQTT 연결
  // ---------------------------------------------------

  while (
    !mqttClient.connect(
      broker,
      port
    )
  ) {

    Serial.print("MQTT 연결 실패 rc=");
    Serial.println(
      mqttClient.connectError()
    );

    delay(2000);
  }


  Serial.println(
    "Ubidots MQTT 연결 성공!"
  );
}


// =====================================================
// 센서 데이터 → Ubidots
// =====================================================

void publishSensorData() {

  float temperature;
  float humidity;


  // ---------------------------------------------------
  // SHT30 읽기
  // ---------------------------------------------------

  if (
    !readSHT30(
      temperature,
      humidity
    )
  ) {

    Serial.println(
      "SHT30 데이터 읽기 실패!"
    );

    return;
  }


  // ---------------------------------------------------
  // Ubidots Topic
  //
  // /v1.6/devices/DEVICE_LABEL
  // ---------------------------------------------------

  String topic =
    "/v1.6/devices/";

  topic += DEVICE_LABEL;


  // ---------------------------------------------------
  // JSON
  // ---------------------------------------------------

  mqttClient.beginMessage(
    topic
  );


  mqttClient.print(
    "{\"temperature\":"
  );

  mqttClient.print(
    temperature,
    2
  );


  mqttClient.print(
    ",\"humidity\":"
  );

  mqttClient.print(
    humidity,
    2
  );

  mqttClient.print(
    "}"
  );


  mqttClient.endMessage();


  // ---------------------------------------------------
  // Serial Monitor
  // ---------------------------------------------------

  Serial.println();
  Serial.println(
    "===== Ubidots Publish ====="
  );

  Serial.print(
    "Device      : "
  );

  Serial.println(
    DEVICE_LABEL
  );

  Serial.print(
    "Temperature : "
  );

  Serial.print(
    temperature,
    2
  );

  Serial.println(
    " °C"
  );

  Serial.print(
    "Humidity    : "
  );

  Serial.print(
    humidity,
    2
  );

  Serial.println(
    " %"
  );

  Serial.println(
    "==========================="
  );
}