#include <SPI.h>
#include <MFRC522.h>

#define SS_PIN 10
#define RST_PIN 9

#define LED_VERDE 7
#define LED_VERMELHO 4

#define BUZZER 8
#define BUZZER2 3

MFRC522 mfrc522(SS_PIN, RST_PIN);

// ===== CARTOES AUTORIZADOS =====
const byte uid1[] = {0x33, 0x4D, 0x33, 0xAD};
const byte uid2[] = {0x05, 0x65, 0xB0, 0xE3, 0x64, 0x03, 0xE9};

// ===== SOM NOS DOIS BUZZERS =====
void toneDual(unsigned int freq, unsigned long ms) {
  unsigned long meioPeriodo = 500000UL / freq;
  unsigned long inicio = millis();

  while (millis() - inicio < ms) {
    digitalWrite(BUZZER, HIGH);
    digitalWrite(BUZZER2, HIGH);
    delayMicroseconds(meioPeriodo);

    digitalWrite(BUZZER, LOW);
    digitalWrite(BUZZER2, LOW);
    delayMicroseconds(meioPeriodo);
  }

  digitalWrite(BUZZER, LOW);
  digitalWrite(BUZZER2, LOW);
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

// ===== ACESSO PERMITIDO =====
void acessoPermitido() {
  
  digitalWrite(LED_VERMELHO, LOW);
  digitalWrite(LED_VERDE, HIGH);

  somPermitido();

  delay(300);
  digitalWrite(LED_VERDE, LOW);
}

// ===== ACESSO NEGADO =====
void acessoNegado() {

  digitalWrite(LED_VERDE, LOW);
  digitalWrite(LED_VERMELHO, HIGH);

  somNegado();

  digitalWrite(LED_VERMELHO, LOW);
}

// ===== VERIFICAR CARTOES =====
bool cartaoAutorizado() {
  if (mfrc522.uid.size == sizeof(uid1) &&
      memcmp(mfrc522.uid.uidByte, uid1, sizeof(uid1)) == 0) {
    return true;
  }

  if (mfrc522.uid.size == sizeof(uid2) &&
      memcmp(mfrc522.uid.uidByte, uid2, sizeof(uid2)) == 0) {
    return true;
  }

  return false;
}

// ===== CONFIGURACAO INICIAL =====
void setup() {
  Serial.begin(9600);

  SPI.begin();
  mfrc522.PCD_Init();

  pinMode(LED_VERDE, OUTPUT);
  pinMode(LED_VERMELHO, OUTPUT);
  pinMode(BUZZER, OUTPUT);
  pinMode(BUZZER2, OUTPUT);

  digitalWrite(LED_VERDE, LOW);
  digitalWrite(LED_VERMELHO, LOW);
  digitalWrite(BUZZER, LOW);
  digitalWrite(BUZZER2, LOW);

}

// ===== LOOP PRINCIPAL =====
void loop() {
  if (!mfrc522.PICC_IsNewCardPresent()) {
    return;
  }

  if (!mfrc522.PICC_ReadCardSerial()) {
    return;
  }

  for (byte i = 0; i < mfrc522.uid.size; i++) {
    if (mfrc522.uid.uidByte[i] < 0x10) {
      Serial.print("0");
    }

    Serial.print(mfrc522.uid.uidByte[i], HEX);
    Serial.print(" ");
  }

  Serial.println();

  if (cartaoAutorizado()) {
    acessoPermitido();
  } else {
    acessoNegado();
  }

  mfrc522.PICC_HaltA();
  mfrc522.PCD_StopCrypto1();

  delay(500);
}