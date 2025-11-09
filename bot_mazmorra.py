import logging
import os
import google.generativeai as genai
import json
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

# Importamos la función para cargar variables de entorno
from dotenv import load_dotenv

# Cargamos las variables del archivo .env al entorno de os
load_dotenv()

# --- Configuración ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Configura el logging para ver errores
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configura el cliente de Gemini
try:
    genai.configure(api_key=GEMINI_API_KEY)
except Exception as e:
    logger.error(f"Error al configurar Gemini: {e}. ¿Falta la API key?")

# --- Definición de Estados para la Conversación ---
# Estados para /generar
(
    ESTADO_NIVEL,
    ESTADO_GRUPO,
    ESTADO_TIPO_NPC,
    ESTADO_CONTEXTO,
) = range(4)

# Estados para /mejorar
(
    ESTADO_MEJORAR_TIPO,
    ESTADO_MEJORAR_DESC,
    ESTADO_MEJORAR_NIVEL,
) = range(4, 7)

# Opciones de teclado reutilizables
OPCIONES_NPC = [
    ["Aliado", "Enemigo"],
    ["Misión", "Criatura"],
    ["Jefe (Boss)"],
]


# --- Comandos del Bot ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja el comando /start. Saluda al usuario."""
    await update.message.reply_text(
        "¡Hola, Dungeon Master! Soy tu asistente de IA para Dungeons & Dragons 5e.\n\n"
        "Usa /generar para crear un PNJ desde cero.\n"
        "Usa /mejorar para expandir una idea que ya tengas.\n"
        "Usa /cancelar en cualquier momento para detener la creación."
    )
    return ConversationHandler.END


# --- Flujo /generar ---

async def generar_npc_inicio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia la conversación para generar un PNJ."""
    await update.message.reply_text(
        "¡Perfecto! Vamos a crear un PNJ desde cero.\n\n"
        "Primero, ¿cuál es el 'nivel promedio' del grupo? (Ej: 3)"
    )
    return ESTADO_NIVEL


async def recibir_nivel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Almacena el nivel y pregunta por la composición del grupo."""
    nivel = update.message.text
    try:
        # Validamos que sea un número
        context.user_data["nivel"] = int(nivel)
    except ValueError:
        await update.message.reply_text(
            "Eso no parece un número. Por favor, dime solo el nivel promedio. (Ej: 5)"
        )
        return ESTADO_NIVEL

    await update.message.reply_text(
        f"Nivel {nivel}, ¡entendido!\n\n"
        "Ahora, ¿quiénes componen el grupo? (Ej: un mago, un bárbaro y un pícaro)"
    )
    return ESTADO_GRUPO


async def recibir_grupo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Almacena el grupo y pregunta por el tipo de PNJ."""
    context.user_data["grupo"] = update.message.text

    reply_markup = ReplyKeyboardMarkup(
        OPCIONES_NPC, one_time_keyboard=True, resize_keyboard=True
    )

    await update.message.reply_text(
        "¡Genial! ¿Qué tipo de PNJ necesitas?", reply_markup=reply_markup
    )
    return ESTADO_TIPO_NPC


async def recibir_tipo_npc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Almacena el tipo de PNJ y pregunta por el contexto."""
    tipo_npc = update.message.text
    context.user_data["tipo_npc"] = tipo_npc

    await update.message.reply_text(
        f"Un/a {tipo_npc}. ¡Perfecto!\n\n"
        "Finalmente, ¿cuál es el 'contexto'? (Ej: en un castillo abandonado en las montañas)",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ESTADO_CONTEXTO


async def recibir_contexto_y_generar(
        update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Recibe el contexto, recopila todos los datos y llama a la API de Gemini
    para el modo 'generar'.
    """
    context.user_data["contexto"] = update.message.text

    mensaje_espera = await update.message.reply_text(
        "Entendido. Estoy forjando a tu PNJ en las profundidades de la IA... 🧙‍♂️✨\n"
        "Esto puede tardar un momento."
    )

    # Recopila toda la información
    info_completa = {
        "nivel": context.user_data.get("nivel"),
        "grupo": context.user_data.get("grupo"),
        "tipo_npc": context.user_data.get("tipo_npc"),
        "contexto": context.user_data.get("contexto"),
    }

    try:
        # Llama a la función principal de IA en modo 'generar'
        npc_json_string = await llamar_a_gemini(info_completa, modo="generar")
        npc_data = json.loads(npc_json_string)
        respuesta_formateada = formatear_respuesta_npc(npc_data)

        await mensaje_espera.edit_text(
            respuesta_formateada, parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Error al generar PNJ: {e}")
        await mensaje_espera.edit_text(
            "¡Oh no! Hubo un error al contactar a la forja de IA. 🙈\n"
            f"Detalle: {e}\n\n"
            "Por favor, intenta de nuevo con /generar."
        )

    context.user_data.clear()
    return ConversationHandler.END


# --- Flujo /mejorar ---

async def mejorar_npc_inicio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia la conversación para mejorar un PNJ."""
    reply_markup = ReplyKeyboardMarkup(
        OPCIONES_NPC, one_time_keyboard=True, resize_keyboard=True
    )
    await update.message.reply_text(
        "¡Vamos a mejorar tu idea! ¿Qué tipo de PNJ es?",
        reply_markup=reply_markup,
    )
    return ESTADO_MEJORAR_TIPO


async def recibir_mejorar_tipo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Almacena el tipo y pregunta por la descripción base."""
    context.user_data["tipo_npc"] = update.message.text
    await update.message.reply_text(
        f"¡Un/a {context.user_data['tipo_npc']}! ¿Cuál es tu idea base?\n\n"
        "(Ej: un bandido de poca monta llamado Find que roba a los ancianos)",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ESTADO_MEJORAR_DESC


async def recibir_mejorar_desc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Almacena la descripción y pregunta por el nivel."""
    context.user_data["descripcion_base"] = update.message.text
    await update.message.reply_text(
        "¡Suena prometedor! ¿Para qué 'nivel promedio' de grupo lo estás balanceando? (Ej: 4)"
    )
    return ESTADO_MEJORAR_NIVEL


async def recibir_mejorar_nivel_y_generar(
        update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Recibe el nivel, recopila todos los datos y llama a la API de Gemini
    para el modo 'mejorar'.
    """
    try:
        context.user_data["nivel"] = int(update.message.text)
    except ValueError:
        await update.message.reply_text(
            "Eso no parece un número. Por favor, dime solo el nivel promedio. (Ej: 4)"
        )
        return ESTADO_MEJORAR_NIVEL

    mensaje_espera = await update.message.reply_text(
        "¡Entendido! Tomando tu idea y añadiendo estadísticas, historia y... ¡magia! ✨\n"
        "Esto puede tardar un momento."
    )

    # Recopila toda la información
    info_completa = {
        "nivel": context.user_data.get("nivel"),
        "tipo_npc": context.user_data.get("tipo_npc"),
        "descripcion_base": context.user_data.get("descripcion_base"),
    }

    try:
        # Llama a la función principal de IA en modo 'mejorar'
        npc_json_string = await llamar_a_gemini(info_completa, modo="mejorar")
        npc_data = json.loads(npc_json_string)
        respuesta_formateada = formatear_respuesta_npc(npc_data)

        await mensaje_espera.edit_text(
            respuesta_formateada, parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Error al mejorar PNJ: {e}")
        await mensaje_espera.edit_text(
            "¡Oh no! Hubo un error al contactar a la forja de IA. 🙈\n"
            f"Detalle: {e}\n\n"
            "Por favor, intenta de nuevo con /mejorar."
        )

    context.user_data.clear()
    return ConversationHandler.END


# --- Lógica de IA (Gemini) ---

async def llamar_a_gemini(info: dict, modo: str) -> str:
    """
    Construye el prompt, define el esquema JSON y llama a la API de Gemini.
    El 'modo' puede ser 'generar' o 'mejorar'.
    """

    # 1. Definir el esquema JSON (es el mismo para ambos modos)
    schema_npc = {
        "type": "OBJECT",
        "properties": {
            "nombre": {"type": "STRING"},
            "tipo": {"type": "STRING", "description": f"Confirma el tipo: {info['tipo_npc']}"},
            "descripcion_visual": {"type": "STRING", "description": "Cómo se ve y actúa."},
            "historia_contexto": {"type": "STRING",
                                  "description": "Historia, motivaciones y cómo encaja en el contexto."},
            "cr_sugerido": {"type": "NUMBER",
                            "description": "Challenge Rating (CR) numérico sugerido, balanceado para el grupo."},
            "estadisticas": {
                "type": "OBJECT",
                "properties": {
                    "PV": {"type": "NUMBER", "description": "Puntos de Vida (Hit Points)"},
                    "CA": {"type": "NUMBER", "description": "Clase de Armadura (Armor Class)"},
                    "FUE": {"type": "NUMBER"}, "DES": {"type": "NUMBER"}, "CON": {"type": "NUMBER"},
                    "INT": {"type": "NUMBER"}, "SAB": {"type": "NUMBER"}, "CAR": {"type": "NUMBER"},
                }
            },
            "acciones": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "nombre": {"type": "STRING"},
                        "tipo": {"type": "STRING", "description": "Ej: 'Ataque de arma Melee'"},
                        "descripcion": {"type": "STRING", "description": "Ej: '+5 al golpear, 1d8+3 daño cortante.'"}
                    }
                }
            },
            "habilidades_especiales": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {"nombre": {"type": "STRING"}, "descripcion": {"type": "STRING"}}
                },
                "description": "Habilidades pasivas o activas especiales (clave para Jefes)."
            },
            "mision_propuesta": {
                "type": "STRING",
                "description": "Solo si el tipo es 'Misión'. Describe la misión que ofrece."
            }
        },
        "required": ["nombre", "tipo", "descripcion_visual", "historia_contexto", "cr_sugerido", "estadisticas",
                     "acciones"]
    }

    # 2. Definir System Prompt y User Prompt según el modo
    system_prompt_base = (
        "Eres 'Mazemaster AI', un asistente experto en Dungeons & Dragons 5e. "
        "Tu tarea es generar un PNJ (NPC) completo y balanceado. "
        "DEBES seguir estas reglas de equilibrio de D&D 5e:\n"
        f"1. El PNJ debe estar balanceado para un grupo de 4 jugadores de nivel {info['nivel']}.\n"
        "2. Si piden un 'Jefe (Boss)', el CR debe ser 1 o 2 niveles MÁS ALTO que el nivel del grupo, "
        "y DEBE tener 'habilidades_especiales' o 'acciones legendarias' simples.\n"
        "3. Si es un 'Aliado', su CR debe ser MENOR que el nivel del grupo (aprox. nivel/2) para no robar protagonismo.\n"
        "4. Si es una 'Criatura' hostil, trátala como un 'Enemigo' estándar.\n"
        "5. Si es 'Misión', enfócate en 'historia_contexto' y 'mision_propuesta'. El CR puede ser 0.\n"
        "6. DEBES responder ÚNICAMENTE con el objeto JSON que se adhiere al esquema solicitado."
    )

    if modo == "generar":
        system_prompt = system_prompt_base + "\n7. Basa la descripción e historia en el contexto proporcionado por el usuario."
        user_prompt = (
            "Por favor, genera un PNJ desde cero con las siguientes características:\n"
            f"- Nivel del Grupo: {info['nivel']}\n"
            f"- Composición del Grupo: {info['grupo']}\n"
            f"- Tipo de PNJ Solicitado: {info['tipo_npc']}\n"
            f"- Contexto Actual: {info['contexto']}\n\n"
            "Genera la respuesta JSON estructurada."
        )
    elif modo == "mejorar":
        system_prompt = system_prompt_base + "\n7. Debes tomar la 'idea base' del usuario y expandirla creativamente en la descripción e historia."
        user_prompt = (
            "Por favor, toma mi idea base y conviértela en un PNJ completo y balanceado:\n"
            f"- Nivel del Grupo: {info['nivel']}\n"
            f"- Tipo de PNJ Solicitado: {info['tipo_npc']}\n"
            f"- Mi Idea Base: \"{info['descripcion_base']}\"\n\n"
            "Expande esta idea, dale vida, estadísticas, historia y acciones. Genera la respuesta JSON estructurada."
        )
    else:
        raise ValueError("Modo de IA no válido.")

    # 4. Configuración del modelo Gemini
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash-preview-09-2025",
        system_instruction=system_prompt,
        generation_config={
            "response_mime_type": "application/json",
            "response_schema": schema_npc
        }
    )

    # 5. Llamada a la API
    logger.info(f"Llamando a la API de Gemini en modo '{modo}'...")
    response = await model.generate_content_async(user_prompt)

    logger.info("Respuesta recibida de Gemini.")
    return response.text


def formatear_respuesta_npc(data: dict) -> str:
    """Convierte el JSON del PNJ en un mensaje de Telegram legible (Markdown)."""

    s = f"### {data.get('nombre', 'PNJ Sin Nombre')} ({data.get('tipo', 'Tipo Desconocido')}) ###\n\n"
    s += f"**CR Sugerido:** {data.get('cr_sugerido', 'N/A')}\n\n"
    s += f"_{data.get('descripcion_visual', 'Sin descripción.')}_\n\n"
    s += f"**Contexto/Historia:**\n{data.get('historia_contexto', 'Sin historia.')}\n\n"

    # Misión (si existe)
    if data.get('mision_propuesta'):
        s += f"**Misión Propuesta:**\n{data.get('mision_propuesta')}\n\n"

    # Estadísticas
    stats = data.get('estadisticas', {})
    s += "--- **Estadísticas Base** ---\n"
    s += f"**PV:** {stats.get('PV', 'N/A')} | **CA:** {stats.get('CA', 'N/A')}\n"
    s += (
        f"FUE: {stats.get('FUE', 10)} | DES: {stats.get('DES', 10)} | CON: {stats.get('CON', 10)} | "
        f"INT: {stats.get('INT', 10)} | SAB: {stats.get('SAB', 10)} | CAR: {stats.get('CAR', 10)}\n\n"
    )

    # Acciones
    s += "--- **Acciones** ---\n"
    acciones = data.get('acciones', [])
    if not acciones:
        s += "_Este PNJ parece inofensivo._\n"
    for accion in acciones:
        s += f"**{accion.get('nombre', 'Acción')}:** ({accion.get('tipo', '')}) {accion.get('descripcion', '')}\n"

    # Habilidades Especiales
    habilidades = data.get('habilidades_especiales', [])
    if habilidades:
        s += "\n--- **Habilidades Especiales** ---\n"
        for hab in habilidades:
            s += f"**{hab.get('nombre', 'Habilidad')}:** {hab.get('descripcion', '')}\n"

    return s


async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela la conversación actual."""
    await update.message.reply_text(
        "¡Creación de PNJ cancelada! Nos vemos en la próxima aventura.",
        reply_markup=ReplyKeyboardRemove(),
    )
    context.user_data.clear()
    return ConversationHandler.END


# --- Función Principal (Main) ---

def main() -> None:
    """Inicia el bot de Telegram y se pone a la escucha."""

    if TELEGRAM_BOT_TOKEN == "TU_TOKEN_DE_TELEGRAM_AQUI" or GEMINI_API_KEY == "TU_API_KEY_DE_GEMINI_AQUI":
        logger.warning("¡ADVERTENCIA! No se encontraron los tokens de API.")
        print("Error: Debes configurar TELEGRAM_BOT_TOKEN y GEMINI_API_KEY para que el bot funcione.")
        print(
            "Puedes establecerlas como variables de entorno o directamente en el código (no recomendado para producción).")
        return

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # --- Manejador de Conversación para /generar ---
    conv_handler_generar = ConversationHandler(
        entry_points=[CommandHandler("generar", generar_npc_inicio)],
        states={
            ESTADO_NIVEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_nivel)],
            ESTADO_GRUPO: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_grupo)],
            ESTADO_TIPO_NPC: [
                MessageHandler(
                    filters.Regex("^(Aliado|Enemigo|Misión|Criatura|Jefe \(Boss\))$"),
                    recibir_tipo_npc,
                )
            ],
            ESTADO_CONTEXTO: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, recibir_contexto_y_generar
                )
            ],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )

    # --- Manejador de Conversación para /mejorar ---
    conv_handler_mejorar = ConversationHandler(
        entry_points=[CommandHandler("mejorar", mejorar_npc_inicio)],
        states={
            ESTADO_MEJORAR_TIPO: [
                MessageHandler(
                    filters.Regex("^(Aliado|Enemigo|Misión|Criatura|Jefe \(Boss\))$"),
                    recibir_mejorar_tipo,
                )
            ],
            ESTADO_MEJORAR_DESC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_mejorar_desc)
            ],
            ESTADO_MEJORAR_NIVEL: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, recibir_mejorar_nivel_y_generar
                )
            ],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler_generar)
    application.add_handler(conv_handler_mejorar)
    application.add_handler(CommandHandler("cancelar", cancelar))  # Fallback global

    print("¡El bot está en marcha! Presiona Ctrl+C para detenerlo.")
    application.run_polling()


if __name__ == "__main__":
    main()
