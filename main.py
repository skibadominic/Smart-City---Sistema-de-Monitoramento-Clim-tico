import network
import ntptime
import urequests
import ujson
from machine import Pin, ADC, I2C
from time import sleep, localtime, time
from ssd1306 import SSD1306_I2C
import dht
import gc

TOKEN = ""
CHAT_ID = ""
alerta_enviado = False

wifi_conectado = False
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect('Wokwi-GUEST', '')
max_wait = 30

while max_wait > 0 and wlan.status() != 1010:
    if wlan.status() < 0: break
    max_wait -= 1
    sleep(1)

if wlan.status() == 1010:
    wifi_conectado = True
    gc.collect()
    try:
        ntptime.settime()
    except Exception as e:
        pass

sensor_dht = dht.DHT22(Pin(13))
pot = ADC(Pin(34))
pot.atten(ADC.ATTN_11DB)
i2c = I2C(0, scl=Pin(22), sda=Pin(21))
oled = SSD1306_I2C(128, 64, i2c)
led_r = Pin(25, Pin.OUT)
led_g = Pin(26, Pin.OUT)
led_b = Pin(27, Pin.OUT)

fuso_horario_offset = -3 * 3600

def set_rgb(r, g, b):
    led_r.value(not r)
    led_g.value(not g)
    led_b.value(not b)

def enviar_telegram(mensagem):
    gc.collect()
    try:
        url = "https://api.telegram.org/bot" + TOKEN + "/sendMessage?chat_id=" + CHAT_ID + "&text=" + mensagem
        resposta = urequests.get(url)
        resposta.close()
    except Exception as e:
        pass

WEATHER_CODES = {
    0: "Ceu limpo", 1: "Com nuvens", 2: "Com nuvens", 3: "Com nuvens",
    45: "Nevoeiro", 48: "Nevoeiro", 51: "Garoa", 53: "Garoa", 55: "Garoa",
    56: "Garoa", 57: "Garoa", 61: "Chuva", 63: "Chuva", 65: "Chuva",
    66: "Chuva", 67: "Chuva", 71: "Neve", 73: "Neve", 75: "Neve",
    77: "Neve", 85: "Neve", 86: "Neve", 80: "Pancadas", 81: "Pancadas",
    82: "Pancadas", 95: "Trovejadas", 96: "Trovejadas", 99: "Trovejadas"
}

def get_weather_code_desc(code):
    return WEATHER_CODES.get(int(code), "N/A")

def get_weather_forecast():
    global alerta_enviado
    if not wifi_conectado:
        return "Sem Conexao", "N/A"
    
    url = "https://api.open-meteo.com/v1/forecast?latitude=-25.43&longitude=-49.27&current_weather=true&hourly=precipitation_probability&timezone=America/Sao_Paulo&forecast_days=1"
    
    gc.collect()
    try:
        response = urequests.get(url)
        data = ujson.loads(response.text)
        response.close()

        current = data['current_weather']
        desc = get_weather_code_desc(current['weathercode'])
        
        agora = localtime(time() + fuso_horario_offset)
        hora_atual_idx = agora[3]
        rain_chance = data['hourly']['precipitation_probability'][hora_atual_idx]
        
        if (desc in ["Chuva", "Garoa", "Pancadas", "Trovejadas"]) and (not alerta_enviado):
            enviar_telegram("ALERTA:%20Vai%20chover%20em%20breve!%20%20Não%20se%20esqueça%20do%20seu%20Guarda-Chuva!🌧️")
            alerta_enviado = True
        elif (desc not in ["Chuva", "Garoa", "Pancadas", "Trovejadas"]):
            alerta_enviado = False
        
        return desc, str(rain_chance)
    except Exception as e:
        return "Modo Offline", "N/A"

def mostra_tela_relogio():
    set_rgb(0, 0, 0)
    agora = localtime(time() + fuso_horario_offset)
    data_str = f"{agora[2]:02d}/{agora[1]:02d}/{agora[0]}"
    hora_str = f"{agora[3]:02d}:{agora[4]:02d}:{agora[5]:02d}"
    oled.fill(0)
    oled.text("DATA & HORA", 20, 0)
    oled.text(data_str, 24, 24)
    oled.text(hora_str, 32, 40)
    oled.show()

def mostra_tela_sensores():
    try:
        sensor_dht.measure()
        temp = sensor_dht.temperature()
        umid = sensor_dht.humidity()
    except OSError:
        temp, umid = 0.0, 0.0 

    qualidade = int(pot.read() / 4) 
    
    if qualidade < 300:
        status = "Boa"
        set_rgb(0, 1, 0)
    elif qualidade < 700:
        status = "Moderada"
        set_rgb(1, 1, 0)
    else:
        status = "Ruim"
        set_rgb(1, 0, 0)

    oled.fill(0)
    oled.text("SMART CITY", 20, 0)
    oled.text(f"Temp: {temp:.1f}C", 0, 18)
    oled.text(f"Umid: {umid:.1f}%", 0, 30)
    oled.text(f"Ar: {status}", 0, 42)
    oled.show()

def mostra_tela_previsao():
    set_rgb(0, 0, 0)
    descricao, chance_chuva = get_weather_forecast()
    oled.fill(0)
    oled.text("CURITIBA", 0, 0)
    oled.text(descricao[:16], 0, 24)
    oled.text("Chance de chuva:", 0, 42)
    oled.text(f"{chance_chuva}%", 0, 52)
    oled.show()

telas = [
    mostra_tela_relogio,
    mostra_tela_sensores,
    mostra_tela_previsao
]
tela_atual_idx = 0

while True:
    telas[tela_atual_idx]()
    tela_atual_idx = (tela_atual_idx + 1) % len(telas)
    sleep(4)
