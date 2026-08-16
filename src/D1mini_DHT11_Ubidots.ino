/*
  D1 mini Pro + DHT11
  → WiFi
  → Ubidots MQTT
  → Temperature / Humidity

  Device : d1mini-dht11-02
  전송 주기 : 10초

  DHT11 DATA → D2 (GPIO4)
*/

#include <Arduino.h>
#include <ESP8266WiFi.h>
#include <ArduinoMqttClient.h>
#include <DHT.h>

#include "arduino_secrets.h"


// =====================================================
// DHT11
// =====================================================

#define DHTPIN  D2
#define DHTTYPE DHT11

DHT dht(DHTPIN, DHTTYPE);


// =====================================================
// WiFi / MQTT
// =====================================================

WiFiClient wifiClient;
MqttClient mqttClient(wifiClient);


// =====================================================
// Ubidots
// =====================================================

const char broker[] =
    "industrial.api.ubidots.com";

const int port = 1883;


// Ubidots Token은 arduino_secrets.h에 저장
// #define UBIDOTS_TOKEN "xxxx"
// 또는
// const char UBIDOTS_TOKEN[] = "xxxx";


// =====================================================
// Ubidots Device
// =====================================================

const char DEVICE_LABEL[] =
    "d1mini-dht11-02";


// =====================================================
// 전송 주기
// =====================================================

unsigned long previousMillis = 0;

const unsigned long interval = 10000;


// =====================================================
// 함수 선언
// =====================================================

void connectMQTT();


// =====================================================
// SETUP
// =====================================================

void setup() {

  Serial.begin(115200);

  delay(1000);

  Serial.println();
  Serial.println("================================");
  Serial.println(" D1 mini Pro + DHT11");
  Serial.println(" Ubidots MQTT Monitor");
  Serial.println("================================");


  // ---------------------------------------------------
  // DHT11 초기화
  // ---------------------------------------------------

  Serial.println("DHT11 초기화...");

  dht.begin();

  delay(2000);


  // ---------------------------------------------------
  // WiFi 연결
  // ---------------------------------------------------

  Serial.println();
  Serial.println("WiFi 연결 중...");

  WiFi.begin(
      SECRET_SSID,
      SECRET_PASS
  );


  while (WiFi.status() != WL_CONNECTED) {

    delay(500);

    Serial.print(".");
  }


  Serial.println();
  Serial.println("WiFi 연결 성공!");

  Serial.print("IP 주소: ");
  Serial.println(WiFi.localIP());


  // ---------------------------------------------------
  // MQTT 연결
  // ---------------------------------------------------

  connectMQTT();
}


// =====================================================
// LOOP
// =====================================================

void loop() {

  // ---------------------------------------------------
  // MQTT 처리
  // ---------------------------------------------------

  mqttClient.poll();


  // ---------------------------------------------------
  // MQTT 연결 확인
  // ---------------------------------------------------

  if (!mqttClient.connected()) {

    Serial.println();
    Serial.println("MQTT 연결 끊김.");
    Serial.println("재연결 중...");

    connectMQTT();
  }


  // ---------------------------------------------------
  // 10초마다 센서 측정 및 전송
  // ---------------------------------------------------

  unsigned long currentMillis =
      millis();


  if (
      currentMillis - previousMillis >= interval
  ) {

    previousMillis = currentMillis;


    // -----------------------------------------------
    // DHT11 측정
    // -----------------------------------------------

    float humidity =
        dht.readHumidity();

    float temperature =
        dht.readTemperature();


    // -----------------------------------------------
    // 센서 오류 확인
    // -----------------------------------------------

    if (
        isnan(humidity) ||
        isnan(temperature)
    ) {

      Serial.println();
      Serial.println("DHT11 측정 실패!");

      return;
    }


    // -----------------------------------------------
    // Ubidots MQTT Topic
    // -----------------------------------------------

    String topic =
        "/v1.6/devices/";

    topic += DEVICE_LABEL;


    // -----------------------------------------------
    // JSON 데이터
    // -----------------------------------------------

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


    // -----------------------------------------------
    // Serial Monitor
    // -----------------------------------------------

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
        " C"
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
}


// =====================================================
// Ubidots MQTT 연결
// =====================================================

void connectMQTT() {

  Serial.println();
  Serial.println(
      "Ubidots MQTT 브로커 연결..."
  );


  // ---------------------------------------------------
  // MQTT 인증
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

    Serial.print(
        "MQTT 연결 실패 rc="
    );

    Serial.println(
        mqttClient.connectError()
    );

    delay(2000);
  }


  Serial.println(
      "Ubidots MQTT 연결 성공!"
  );
}