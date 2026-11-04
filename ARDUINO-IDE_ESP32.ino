#include <WiFi.h>
#include <HTTPClient.h>
#include <SPI.h>
#include <MFRC522.h>

#define SS_PIN 21
#define RST_PIN 22
#define LEDVERDE_PIN 4
#define LEDVERMELHO_PIN 5
#define buzzer1 15
#define buzzer2 16

const char* ssid = "FIEP-CONV";
const char* senha = "resultadoindustria@2026";

// Controle do Heartbeat
unsigned long ultimoHeartbeat = 0;
const unsigned long intervaloHeartbeat = 5000;

// Endereços do Flask
const char* servidor = "http://10.196.48.233:5000/api/leitura";
const char* servidorStatus = "http://10.196.48.233:5000/api/esp/status";

MFRC522 mfrc522(SS_PIN, RST_PIN);


// FUNÇÃO HEARTBEAT
void enviarHeartbeat() {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(servidorStatus);
    http.addHeader("Content-Type", "application/json");
    http.setTimeout(2000);
    int resposta = http.POST("{}");
    http.end();
  } else {
    Serial.println("Wi-Fi desconectado!");
  }
}

void toneDual(unsigned int freq, unsigned long ms) {
  unsigned long meioPeriodo = 500000UL / freq;
  unsigned long inicio = millis();

  while (millis() - inicio < ms) {
    digitalWrite(buzzer1, HIGH);
    digitalWrite(buzzer2, HIGH);
    delayMicroseconds(meioPeriodo);

    digitalWrite(buzzer1, LOW);
    digitalWrite(buzzer2, LOW);
    delayMicroseconds(meioPeriodo);
  }

  digitalWrite(buzzer1, LOW);
  digitalWrite(buzzer2, LOW);
}

// ===== SOM DE PINTINHO: ACESSO PERMITIDO =====
void somPermitido() {
  toneDual(2200, 100);
  delay(40);

  toneDual(2800, 120);
  delay(40);

  toneDual(2200, 100);
  delay(30);

  toneDual(3000, 220);
}

// ===== SOM RAPIDO: ACESSO NEGADO =====
void somNegado() {
  toneDual(3000, 100);
  delay(50);

  toneDual(1800, 250);
}

void setup() {

  Serial.begin(115200);
  pinMode(buzzer1, OUTPUT);
  pinMode(buzzer2, OUTPUT);
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

  // HEARTBEAT: envia um sinal a cada 5 segundos
  if (millis() - ultimoHeartbeat >= intervaloHeartbeat) {

    ultimoHeartbeat = millis();

    enviarHeartbeat();
  }

  // VERIFICAÇÃO DO RFID
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
  // ENVIO DO UID PARA O FLASK
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

      // CORREÇÃO: procura só a palavra, independente de espaços no JSON
      if (resultado.indexOf("Liberado") >= 0) {

        Serial.println("ACESSO LIBERADO");

        digitalWrite(LEDVERMELHO_PIN, LOW);
        digitalWrite(LEDVERDE_PIN, HIGH);
        delay(1000);
        digitalWrite(LEDVERDE_PIN, LOW);
        somPermitido();
        
      } else {
        Serial.println("ACESSO NEGADO");
        digitalWrite(LEDVERDE_PIN, LOW);
        digitalWrite(LEDVERMELHO_PIN, HIGH);
        delay(1000);
        digitalWrite(LEDVERMELHO_PIN, LOW);
        somNegado();
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
