// ============================================================
//  Controle de acesso RFID (ESP32 + MFRC522) -> Flask no Render
//  Envia o UID por HTTPS (POST JSON) para o dominio publico.
// ============================================================
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <SPI.h>
#include <MFRC522.h>
#include <time.h>

#define SS_PIN 21
#define RST_PIN 22
#define LEDVERDE_PIN 4
#define LEDVERMELHO_PIN 5
#define buzzer1 15
#define buzzer2 16

// ---------- Wi-Fi ----------
const char* ssid = "VITTO 71";
const char* senha = "Suely1974#";

// ---------- Servidor no Render ----------
// Sem "http://" antigo, sem IP e sem porta: agora e HTTPS (porta 443 automatica).
const char* URL_LEITURA = "https://html-esp32.onrender.com/api/leitura";
const char* URL_STATUS  = "https://html-esp32.onrender.com/api/esp/status";

// ---------- Seguranca TLS ----------
// 0 = NAO valida o certificado do servidor (usa setInsecure). Serve para testar
//     o fluxo, mas qualquer um na rede poderia se passar pelo servidor.
// 1 = valida o certificado com o certificado raiz colado abaixo (recomendado).
#define VALIDAR_CERTIFICADO 0

#if VALIDAR_CERTIFICADO
// Cole aqui o certificado RAIZ (formato PEM) do seu dominio.
const char* rootCA = R"EOF(
-----BEGIN CERTIFICATE-----
COLE_AQUI_O_CERTIFICADO_RAIZ
-----END CERTIFICATE-----
)EOF";
#endif

// ---------- Heartbeat ----------
unsigned long ultimoHeartbeat = 0;
const unsigned long intervaloHeartbeat = 5000;
bool servidorOk = false;

// ---------- Wi-Fi: controle de reconexao ----------
unsigned long ultimaTentativaWifi = 0;

MFRC522 mfrc522(SS_PIN, RST_PIN);
WiFiClientSecure clienteSeguro;   // cliente HTTPS unico, reaproveitado entre requisicoes

// Resultado da interpretacao da resposta do Flask
enum Resultado { RES_LIBERADO, RES_NEGADO, RES_INVALIDO };

// ------------------------------------------------------------
//  Interpreta a resposta de /api/leitura.
//  So aceita HTTP 200 contendo a chave "acesso". Assim, uma pagina de erro ou
//  de "servidor acordando" nunca e confundida com "Negado".
// ------------------------------------------------------------
Resultado interpretarResposta(int codigo, const String& corpo) {
  if (codigo != 200) return RES_INVALIDO;
  if (corpo.indexOf("\"acesso\"") < 0) return RES_INVALIDO;
  if (corpo.indexOf("Liberado") >= 0) return RES_LIBERADO;
  if (corpo.indexOf("Negado") >= 0) return RES_NEGADO;
  return RES_INVALIDO;
}

// ------------------------------------------------------------
//  Configura a validacao do HTTPS
// ------------------------------------------------------------
void configurarTLS() {
#if VALIDAR_CERTIFICADO
  clienteSeguro.setCACert(rootCA);
  Serial.println("TLS: validando certificado do servidor.");
#else
  clienteSeguro.setInsecure();
  Serial.println("TLS: ATENCAO - certificado NAO esta sendo validado (setInsecure).");
#endif
}

// ------------------------------------------------------------
//  Hora via NTP (necessaria para validar certificados HTTPS)
// ------------------------------------------------------------
void sincronizarHora() {
  configTime(0, 0, "pool.ntp.org", "time.google.com");
  struct tm info;
  Serial.print("Sincronizando hora (NTP)");
  for (int i = 0; i < 20; i++) {
    if (getLocalTime(&info, 500)) {
      Serial.println(" ok");
      return;
    }
    Serial.print(".");
  }
  Serial.println(" falhou (necessaria apenas se VALIDAR_CERTIFICADO = 1)");
}

// ------------------------------------------------------------
//  POST JSON com tentativas.
//  Retorna o codigo HTTP (>0) ou um valor <= 0 em caso de falha.
//  Repete em erro de conexao e em erro 5xx (ex.: servidor acordando).
// ------------------------------------------------------------
int enviarPost(const char* url, const String& corpo, String& resposta,
               int tentativas, int timeoutMs) {
  int codigo = -100;   // -100 = sem Wi-Fi
  resposta = "";

  for (int t = 1; t <= tentativas; t++) {
    if (WiFi.status() != WL_CONNECTED) {
      codigo = -100;
      break;
    }

    unsigned long t0 = millis();
    HTTPClient http;
    http.setReuse(true);
    http.setConnectTimeout(timeoutMs);
    http.setTimeout(timeoutMs);

    if (!http.begin(clienteSeguro, url)) {
      codigo = -101;   // URL invalida
      break;
    }
    http.addHeader("Content-Type", "application/json");

    codigo = http.POST(corpo);
    if (codigo > 0) {
      resposta = http.getString();   // le o corpo inteiro (necessario para reaproveitar a conexao)
    }
    http.end();

    // Sucesso, ou erro "definitivo" (4xx): nao adianta repetir
    if (codigo > 0 && codigo < 500) return codigo;

    // Falha: fecha a conexao (pode estar velha) e tenta de novo
    clienteSeguro.stop();
    Serial.print("Tentativa ");
    Serial.print(t);
    Serial.print("/");
    Serial.print(tentativas);
    Serial.print(" falhou. Codigo: ");
    Serial.print(codigo);
    Serial.print(" ");
    Serial.print(HTTPClient::errorToString(codigo));
    // Diagnostico: quanto demorou, forca do sinal Wi-Fi e memoria livre
    Serial.print(" | tempo(ms): ");
    Serial.print(millis() - t0);
    Serial.print(" | RSSI(dBm): ");
    Serial.print(WiFi.RSSI());
    Serial.print(" | heap livre: ");
    Serial.println(ESP.getFreeHeap());
    if (t < tentativas) delay(1500);
  }
  return codigo;
}

// ------------------------------------------------------------
//  Heartbeat: avisa o Flask que o ESP32 esta vivo
// ------------------------------------------------------------
bool heartbeatOk(int timeoutMs, int tentativas) {
  String resp;
  int codigo = enviarPost(URL_STATUS, "{}", resp, tentativas, timeoutMs);
  return (codigo == 200 && resp.indexOf("Heartbeat") >= 0);
}

void enviarHeartbeat() {
  if (WiFi.status() != WL_CONNECTED) return;

  bool ok = heartbeatOk(6000, 1);
  if (ok != servidorOk) {   // so escreve no Serial quando o estado muda
    servidorOk = ok;
    if (ok) Serial.println("Servidor respondendo (online).");
    else Serial.println("Servidor SEM resposta.");
  }
}

// ------------------------------------------------------------
//  Na partida: "acorda" o servidor do Render (plano gratuito dorme)
// ------------------------------------------------------------
void acordarServidor() {
  Serial.println("Contactando o servidor (pode levar ~1 min se estava dormindo)...");
  for (int i = 1; i <= 6; i++) {
    if (heartbeatOk(20000, 1)) {
      servidorOk = true;
      Serial.println("Servidor pronto!");
      return;
    }
    Serial.print("Aguardando servidor... ");
    Serial.print(i);
    Serial.println("/6");
    delay(2000);
  }
  Serial.println("Servidor nao respondeu agora; o heartbeat continuara tentando.");
}

// ------------------------------------------------------------
//  Wi-Fi
// ------------------------------------------------------------
bool conectarWiFi(unsigned long limiteMs) {
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(ssid, senha);

  unsigned long inicio = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - inicio < limiteMs) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  return WiFi.status() == WL_CONNECTED;
}

// ------------------------------------------------------------
//  Sons e sinais
// ------------------------------------------------------------
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

// ===== FALHA DE COMUNICACAO: os dois LEDs piscam 3x + bipe grave =====
// (diferente de "Negado", para voce saber que o problema e a rede/servidor)
void sinalErro() {
  for (int i = 0; i < 3; i++) {
    digitalWrite(LEDVERDE_PIN, HIGH);
    digitalWrite(LEDVERMELHO_PIN, HIGH);
    toneDual(1000, 120);
    digitalWrite(LEDVERDE_PIN, LOW);
    digitalWrite(LEDVERMELHO_PIN, LOW);
    delay(120);
  }
}

// ============================================================
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

  Serial.print("Conectando ao Wi-Fi");
  while (!conectarWiFi(20000)) {
    Serial.println("Nao conectou. Tentando de novo...");
    WiFi.disconnect();
    delay(1000);
    Serial.print("Conectando ao Wi-Fi");
  }

  Serial.println("Wi-Fi conectado!");
  Serial.println(WiFi.localIP());

  configurarTLS();
  sincronizarHora();
  acordarServidor();

  Serial.println("Aproxime seu cartao RFID...");
}

// ============================================================
void loop() {

  // RECONEXAO Wi-Fi (a cada 10 s, sem travar o programa)
  if (WiFi.status() != WL_CONNECTED) {
    if (millis() - ultimaTentativaWifi >= 10000) {
      ultimaTentativaWifi = millis();
      Serial.println("Wi-Fi desconectado! Reconectando...");
      WiFi.disconnect();
      WiFi.begin(ssid, senha);
    }
  }

  // HEARTBEAT: envia um sinal a cada 5 segundos
  if (millis() - ultimoHeartbeat >= intervaloHeartbeat) {
    ultimoHeartbeat = millis();
    enviarHeartbeat();
  }

  // VERIFICACAO DO RFID
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

  // ENVIO DO UID PARA O FLASK (HTTPS)
  String dados = "{\"uid\":\"" + uid + "\"}";
  String resultado;

  Serial.println("Enviando ao servidor...");
  unsigned long tLeitura = millis();
  int codigo = enviarPost(URL_LEITURA, dados, resultado, 2, 10000);

  Serial.print("HTTP: ");
  Serial.print(codigo);
  Serial.print(" | tempo total da requisicao (ms): ");
  Serial.println(millis() - tLeitura);

  Resultado r = interpretarResposta(codigo, resultado);

  if (r == RES_LIBERADO) {

    Serial.println("Resposta do Flask:");
    Serial.println(resultado);
    Serial.println("ACESSO LIBERADO");

    digitalWrite(LEDVERMELHO_PIN, LOW);
    digitalWrite(LEDVERDE_PIN, HIGH);
    delay(1000);
    digitalWrite(LEDVERDE_PIN, LOW);
    somPermitido();

  } else if (r == RES_NEGADO) {

    Serial.println("Resposta do Flask:");
    Serial.println(resultado);
    Serial.println("ACESSO NEGADO");

    digitalWrite(LEDVERDE_PIN, LOW);
    digitalWrite(LEDVERMELHO_PIN, HIGH);
    delay(1000);
    digitalWrite(LEDVERMELHO_PIN, LOW);
    somNegado();

  } else {

    // Sem Wi-Fi, servidor fora do ar, timeout ou resposta inesperada
    Serial.println("FALHA NA COMUNICACAO - leitura NAO registrada.");
    if (resultado.length() > 0) {
      Serial.println("Corpo recebido:");
      Serial.println(resultado);
    }
    sinalErro();
  }

  mfrc522.PICC_HaltA();
  mfrc522.PCD_StopCrypto1();
  delay(300);
}
