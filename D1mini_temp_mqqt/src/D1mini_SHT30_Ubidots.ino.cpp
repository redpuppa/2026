# 1 "C:\\Users\\sony\\AppData\\Local\\Temp\\tmpu9f7v2el"
#include <Arduino.h>
# 1 "C:/Users/sony/Documents/PlatformIO/Projects/2026/D1mini_temp_mqqt/src/D1mini_SHT30_Ubidots.ino"
# 12 "C:/Users/sony/Documents/PlatformIO/Projects/2026/D1mini_temp_mqqt/src/D1mini_SHT30_Ubidots.ino"
#include <Arduino.h>
#include <Wire.h>
#include <ESP8266WiFi.h>
#include <ArduinoMqttClient.h>

#include "arduino_secrets.h"






#define SHT30_ADDR 0x45






WiFiClient wifiClient;
MqttClient mqttClient(wifiClient);






const char broker[] =
  "industrial.api.ubidots.com";

const int port = 1883;






unsigned long previousMillis = 0;

const unsigned long interval = 10000;






bool readSHT30(
  float &temperature,
  float &humidity
);

void connectWiFi();

void connectMQTT();

void publishSensorData();
void setup();
void loop();
#line 74 "C:/Users/sony/Documents/PlatformIO/Projects/2026/D1mini_temp_mqqt/src/D1mini_SHT30_Ubidots.ino"
void setup() {

  Serial.begin(115200);

  delay(1000);

  Serial.println();
  Serial.println("================================");
  Serial.println(" D1 mini Pro + SHT30 + Ubidots");
  Serial.println("================================");






  Wire.begin(D2, D1);

  Serial.println("I2C 초기화 완료");






  Wire.beginTransmission(SHT30_ADDR);

  if (Wire.endTransmission() == 0) {

    Serial.println("SHT30 연결 성공!");

  } else {

    Serial.println("SHT30 연결 실패!");

    while (true) {
      delay(1000);
    }
  }






  connectWiFi();






  connectMQTT();
}






void loop() {


  mqttClient.poll();






  if (WiFi.status() != WL_CONNECTED) {

    Serial.println();
    Serial.println("Wi-Fi 연결 끊김");

    connectWiFi();
  }






  if (!mqttClient.connected()) {

    Serial.println();
    Serial.println("MQTT 연결 끊김");

    connectMQTT();
  }






  unsigned long currentMillis =
    millis();


  if (
    currentMillis - previousMillis >= interval
  ) {

    previousMillis = currentMillis;

    publishSensorData();
  }
}






bool readSHT30(
  float &temperature,
  float &humidity
) {
# 201 "C:/Users/sony/Documents/PlatformIO/Projects/2026/D1mini_temp_mqqt/src/D1mini_SHT30_Ubidots.ino"
  Wire.beginTransmission(SHT30_ADDR);

  Wire.write(0x2C);
  Wire.write(0x06);

  if (Wire.endTransmission() != 0) {

    return false;
  }



  delay(20);
# 227 "C:/Users/sony/Documents/PlatformIO/Projects/2026/D1mini_temp_mqqt/src/D1mini_SHT30_Ubidots.ino"
  if (Wire.requestFrom(SHT30_ADDR, 6) != 6) {

    return false;
  }


  uint16_t rawTemperature =
    ((uint16_t)Wire.read() << 8)
    | Wire.read();

  Wire.read();


  uint16_t rawHumidity =
    ((uint16_t)Wire.read() << 8)
    | Wire.read();

  Wire.read();






  temperature =
    -45.0 +
    175.0 *
    ((float)rawTemperature / 65535.0);


  humidity =
    100.0 *
    ((float)rawHumidity / 65535.0);


  return true;
}






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






void connectMQTT() {

  Serial.println();
  Serial.println("Ubidots MQTT 브로커 연결...");
# 317 "C:/Users/sony/Documents/PlatformIO/Projects/2026/D1mini_temp_mqqt/src/D1mini_SHT30_Ubidots.ino"
  mqttClient.setUsernamePassword(
    UBIDOTS_TOKEN,
    ""
  );






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






void publishSensorData() {

  float temperature;
  float humidity;






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
# 384 "C:/Users/sony/Documents/PlatformIO/Projects/2026/D1mini_temp_mqqt/src/D1mini_SHT30_Ubidots.ino"
  String topic =
    "/v1.6/devices/";

  topic += DEVICE_LABEL;






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