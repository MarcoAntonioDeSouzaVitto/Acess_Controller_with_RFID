
#include <WiFi.h>
#include <HTTPClient.h>
#include <SPI.h>
#include <MFRC522.h>

#define SS_PIN 21
#define RST_PIN 22
#define LEDVERDE_PIN 4
#define LEDVERMELHO_PIN 5

const char* ssid = "VITTO 71";
const char* senha = "Suely1974#";

// IP do computador que executa o Flask
const char* servidor = "http://192.168.1.9:5000/api/leitura";

MFRC522 mfrc522(SS_PIN, RST_PIN);

void setup() {
  Serial.begin(115200);

  pinMode(LEDVERDE_PIN, OUTPUT);
  digitalWrite(LEDVERDE_PIN, LOW);

  pinMode(LEDVERMELHO_PIN, OUTPUT);
  digitalWrite(LEDVERMELHO_PIN, LOW);

  SPI.begin();
  mfrc522.PCD_Init();

  WiFi.begin(ssid, senha);

  Serial.print("Conectando ao Wi-Fi");

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.println("Wi-Fi conectado!");
  Serial.println(WiFi.localIP());
  Serial.println("Aproxime seu cartao RFID...");
}

void loop() {

  if (!mfrc522.PICC_IsNewCardPresent()) {
    delay(50);
    return;
  }

  if (!mfrc522.PICC_ReadCardSerial()) {
    delay(50);
    return;
  }

  // Monta o UID no formato usado pelo Flask
  String uid = "";

  for (byte i = 0; i < mfrc522.uid.size; i++) {
    if (i > 0) uid += " ";

    if (mfrc522.uid.uidByte[i] < 0x10) {
      uid += "0";
    }

    uid += String(mfrc522.uid.uidByte[i], HEX);
  }

  uid.toUpperCase();

  Serial.println("UID: " + uid);

  if (WiFi.status() == WL_CONNECTED) {

    HTTPClient http;

    http.begin(servidor);
    http.addHeader("Content-Type", "application/json");
    http.setTimeout(5000);

    String dados = "{\"uid\":\"" + uid + "\"}";

    int resposta = http.POST(dados);

    if (resposta > 0) {
      String resultado = http.getString();

      Serial.println("Resposta do Flask:");
      Serial.println(resultado);

      // Verifica o campo "acesso" retornado pelo Flask
      if (resultado.indexOf("\"acesso\": \"Liberado\"") >= 0) {
        Serial.println("ACESSO LIBERADO");
        digitalWrite(LEDVERMELHO_PIN, LOW);
        digitalWrite(LEDVERDE_PIN, HIGH);
        delay(1000);
        digitalWrite(LEDVERDE_PIN, LOW);

      } else {
        Serial.println("ACESSO NEGADO");
        digitalWrite(LEDVERDE_PIN, LOW);
        digitalWrite(LEDVERMELHO_PIN, HIGH);
        delay(1000);
        digitalWrite(LEDVERMELHO_PIN, LOW);
      }

    } else {
      Serial.print("Erro HTTP: ");
      Serial.println(http.errorToString(resposta));
    }

    http.end();

  } else {
    Serial.println("Wi-Fi desconectado!");
  }

  mfrc522.PICC_HaltA();
  mfrc522.PCD_StopCrypto1();

  delay(300);
}
