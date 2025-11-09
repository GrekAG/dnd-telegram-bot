# Bot de Telegram para D&D 5e con IA

Este es un bot de Telegram, desarrollado en Python, que asiste a Directores de Juego (Dungeon Masters) de Dungeons &
Dragons 5e. El bot se conecta a la API de Google Gemini para generar PNJs (Personajes No Jugadores) creativos y
balanceados sobre la marcha.

## Funcionalidades

**/generar:** Inicia un flujo de conversación para crear un PNJ desde cero. El bot te preguntará por el nivel del grupo, su
composición, el tipo de PNJ deseado (Aliado, Enemigo, Jefe, etc.) y el contexto de la situación.

**/mejorar:** Te permite expandir una idea que ya tengas. Le das al bot tu concepto (ej: "un goblin ladrón llamado Krik") y
el nivel del grupo, y la IA generará una historia de fondo, estadísticas balanceadas, acciones y habilidades.

**/cancelar:** Detiene cualquier conversación activa en cualquier momento.

## Tecnologías Utilizadas

* **Python 3**

* `python-telegram-bot`: Para la interacción con la API de Telegram.

* `google-generativeai`: Para conectarse a la API de IA de Google Gemini.

* `python-dotenv`: Para manejar claves de API de forma segura.

## Cómo Instalar y Ejecutar

Sigue estos pasos para poner en marcha tu propia instancia del bot.

### 1. Clonar el Repositorio

Primero, clona este repositorio en tu máquina local.
```bash
# git clone [URL_DE_TU_REPO]

# cd [NOMBRE_DEL_PROYECTO]
```
### 2. Crear un Entorno Virtual

Es una buena práctica aislar las dependencias de tu proyecto.
```bash
# Crear el entorno virtual

python -m venv venv

# Activarlo (en Windows)

.\venv\Scripts\activate

# Activarlo (en macOS/Linux)

source venv/bin/activate
```
### 3. Instalar Dependencias

Instala todas las bibliotecas necesarias que están listadas en requirements.txt.
```bash
pip install -r requirements.txt
```

### 4. Configurar los Tokens de API (¡IMPORTANTE!)

Este proyecto utiliza un archivo `.env` para almacenar tus claves de API de forma segura. El archivo `.gitignore` está
configurado para nunca subir este archivo a GitHub.

En la carpeta principal de tu proyecto, crea un archivo llamado `.env`

Abre el archivo `.env` y añade tus dos claves:
```bash
TELEGRAM_BOT_TOKEN="AQUI_VA_TU_TOKEN_DE_TELEGRAM"
GEMINI_API_KEY="AQUI_VA_TU_API_KEY_DE_GEMINI"
```
(Reemplaza el texto con tus tokens reales).

### 5. Ejecutar el Bot

Una vez que tu entorno virtual esté activado, las dependencias estén instaladas y tu archivo .env esté configurado,
simplemente ejecuta el script:
```bash
python bot_mazmorra.py
```
Si todo está correcto, verás el mensaje `¡El bot está en marcha! Presiona Ctrl+C para detenerlo.` en tu terminal. ¡Ahora
puedes ir a Telegram y hablar con tu bot!