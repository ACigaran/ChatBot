import telebot
from telebot import types
import google.generativeai as genai
import os
from dotenv import load_dotenv
import logging
import sqlite3

# CONEXION CON EL BOT Y LA API DE GEMINI
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_KEY = os.getenv("GOOGLE_API_KEY")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# VALIDACION DE LOS TOKENS
if not TELEGRAM_TOKEN or not API_KEY:
    print("¡Error! Asegúrate de que TELEGRAM_BOT_TOKEN y GOOGLE_API_KEY están definidos en tu archivo .env")
    exit()

bot = telebot.TeleBot(TELEGRAM_TOKEN)
logger.info("Bot de Telegram inicializado.")

try:
    genai.configure(api_key=API_KEY)
    generation_config = {"temperature": 0.7, "top_p": 1, "top_k": 1, "max_output_tokens": 2048}
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    ]
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash-latest",
        generation_config=generation_config,
        safety_settings=safety_settings
    )
    logger.info("Modelo Gemini 'gemini-1.5-flash-latest' inicializado.")
except Exception as e:
    logger.error(f"Error al configurar o inicializar Gemini: {e}")
    exit()

# COMANDO INICIAL DEL BOT
@bot.message_handler(commands=['start'])
def send_welcome(message):
    logger.info(f"Comando /start recibido de {message.from_user.username} (ID: {message.from_user.id})")
    bot.reply_to(message, f'¡Hola {message.from_user.first_name}! Soy un bot asistente. Puedes usar /help para ver mis comandos.')

@bot.message_handler(commands=['help'])
def send_help(message):
    logger.info(f"Comando /help recibido de {message.from_user.username}")
    help_text = """
Aquí tienes los comandos que entiendo:
/start - Inicia la conversación.
/help - Muestra esta ayuda.
/cuenta - Puedes acceder a tus cajas de ahorro.
/gasto - Ingresar un nuevo gasto a una de tus cajas de ahorro.
/cargar - Carga un monto de dinero a tus cajas de ahorro.
/save - Puedes guardar tu id de telegram y nombre de usuario en nuestra base de datos.
/leave - Elimina tus datos guardados con /save de nuestra base de datos.

Si me escribes cualquier otra cosa, intentaré ayudarte usando IA y te recordaré los comandos si es relevante.
"""
    bot.reply_to(message, help_text)

# COMANDO PARA VER LAS CUENTAS/CAJAS DE AHORRO EN PESOS Y DOLARES
def get_cuenta(id: int):
    conn = sqlite3.connect('telegram_bot.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT name, dinero FROM cuentas
        WHERE id = ?
    ''', (id,))
    cuenta = cursor.fetchone()
    if cuenta[0] == "Cuenta Pesos":
        moneda = "$"
    elif cuenta[0] == "Cuenta Dolares":
        moneda = "U$S"
    return f'{cuenta[0]} con un total de {moneda} {cuenta[1]}'

@bot.message_handler(commands=['cuenta'])
def send_options(message):
    logger.info(f"Comando /cuenta recibido de {message.from_user.username}")
    markup = types.InlineKeyboardMarkup(row_width=2) 
    btn_peso = types.InlineKeyboardButton('Pesos', callback_data='cuenta_pesos')
    btn_dolar = types.InlineKeyboardButton('Dolares', callback_data='cuenta_dolares')
    markup.add(btn_peso, btn_dolar) 
    bot.send_message(message.chat.id, "¿A que caja de ahorro desea acceder?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('cuenta_'))
def callback_query(call):
    logger.info(f"Callback query '{call.data}' recibido de {call.from_user.username}")
    response_text = ""
    if call.data == 'cuenta_pesos':
        response_text =  get_cuenta(1)
    elif call.data == 'cuenta_dolares':
        response_text = get_cuenta(2)
    bot.answer_callback_query(call.id, response_text)
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f"Selecciono su {response_text}")

# COMANDO PARA AGREGAR GASTOS
def insert_gasto(cuenta: str, costo: int):
    conn = sqlite3.connect('telegram_bot.db')
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT dinero FROM cuentas
            WHERE name = ?
        ''', (cuenta,))
        dineroCuenta = cursor.fetchone()
        compararAhorro = dineroCuenta[0]
        if compararAhorro < costo:
            return "¡No tiene dinero suficiente en su cuenta para realizar esta compra!"
        else:
            nuevo_saldo = compararAhorro - costo
            cursor.execute('''
                UPDATE cuentas SET dinero = ? WHERE name = ?
            ''', (nuevo_saldo, cuenta))
            logger.info(f"Gasto de {costo} registrado en '{cuenta}'. Nuevo saldo: {nuevo_saldo}")
            conn.commit()
            cursor.close()
            conn.close()
            return f"Compra realizada ${costo:,.2f}.\nNuevo saldo en {cuenta} es de ${nuevo_saldo:,.2f}"
    except Exception as e:
        logger.error(f"Error inesperado al procesar gasto para '{cuenta}': {e}")
        return "Ocurrió un error inesperado al procesar el gasto."

@bot.message_handler(commands=['gasto'])
def send_options(message):
    logger.info(f"Comando /gasto recibido de {message.from_user.username}")
    markup = types.InlineKeyboardMarkup(row_width=4)
    btn_calzado = types.InlineKeyboardButton('👟 $ 1500 - Calzado', callback_data='gasto_calzado')
    btn_mediaLuna = types.InlineKeyboardButton('🍕 $ 90 - MediaLuna', callback_data='gasto_mediaLuna')
    btn_monitor = types.InlineKeyboardButton('📺 U$S 200 - Monitor', callback_data='gasto_monitor')
    btn_psPlus = types.InlineKeyboardButton('🎮 U$S 40 - PsPlus', callback_data='gasto_psPlus')
    markup.add(btn_calzado, btn_mediaLuna, btn_monitor, btn_psPlus) 
    bot.send_message(message.chat.id, "¿Que desea comprar actualmente?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('gasto_'))
def callback_query(call):
    logger.info(f"Callback query '{call.data}' recibido de {call.from_user.username}")
    response_text = ""

    gasto_info = {
        'gasto_calzado': {'cuenta': "Cuenta Pesos", 'costo': 1500},
        'gasto_mediaLuna': {'cuenta': "Cuenta Pesos", 'costo': 90},
        'gasto_monitor': {'cuenta': "Cuenta Dolares", 'costo': 200},
        'gasto_psPlus': {'cuenta': "Cuenta Dolares", 'costo': 40}
    }

    if call.data in gasto_info:
        info = gasto_info[call.data]
        response_text = insert_gasto(info['cuenta'], info['costo'])

    bot.answer_callback_query(call.id, response_text)
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text={response_text})

# DEPOSITAR SALDO
def depositar_saldo(cuenta: str, dinero: int):
    conn = sqlite3.connect('telegram_bot.db')
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT dinero FROM cuentas
            WHERE name = ?
        ''', (cuenta,))
        dineroCuenta = cursor.fetchone()
        saldoActual = dineroCuenta[0]
        nuevo_saldo = saldoActual + dinero
        cursor.execute('''
            UPDATE cuentas SET dinero = ? WHERE name = ?
        ''', (nuevo_saldo, cuenta))
        logger.info(f"Deposito de {dinero} registrado en '{cuenta}'. Nuevo saldo {nuevo_saldo}")
        conn.commit()
        cursor.close()
        conn.close()
        return f"Carga realizada ${dinero:,.2f}.\nNuevo saldo en {cuenta} es de ${nuevo_saldo:,.2f}"
    except Exception as e:
        logger.error(f"Error inesperado al procesar carga para '{cuenta}': {e}")
        return "Ocurrió un error inesperado al procesar la carga."


@bot.message_handler(commands=['cargar'])
def cargar_saldo(message):
    logger.info(f"Comando /cargar recibido de {message.from_user.username}")
    markup = types.InlineKeyboardMarkup(row_width=4) 
    btn_min_peso = types.InlineKeyboardButton('📥$ 500', callback_data='cargar_500P')
    btn_max_peso = types.InlineKeyboardButton('📥$ 1000', callback_data='cargar_1000P')
    btn_min_dolar = types.InlineKeyboardButton('📥U$S 25', callback_data='cargar_25D')
    btn_max_dolar = types.InlineKeyboardButton('📥U$S 100', callback_data='cargar_100D')
    markup.add(btn_min_peso, btn_max_peso, btn_min_dolar, btn_max_dolar) 
    bot.send_message(message.chat.id, "¿Cuando dinero desea cargar?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('cargar_'))
def callback_query(call):
    logger.info(f"Callback query '{call.data}' recibido de {call.from_user.username}")
    response_text = ""

    gasto_info = {
        'cargar_500P': {'cuenta': "Cuenta Pesos", 'costo': 500},
        'cargar_1000P': {'cuenta': "Cuenta Pesos", 'costo': 1000},
        'cargar_25D': {'cuenta': "Cuenta Dolares", 'costo': 25},
        'cargar_100D': {'cuenta': "Cuenta Dolares", 'costo': 100}
    }

    if call.data in gasto_info:
        info = gasto_info[call.data]
        response_text = depositar_saldo(info['cuenta'], info['costo'])

    bot.answer_callback_query(call.id, response_text)
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text={response_text})

# COMANDO PARA GUARDAR EL NOMBRE DE USUARIO E IP DE TELEGRAM EN LA BASE DE DATOS
def insert_user(telegram_id: int, name: str):
    conn = sqlite3.connect('telegram_bot.db')
    cursor = conn.cursor()

    cursor.execute('''
        INSERT OR IGNORE INTO users (telegram_id, name)
        VALUES (?, ?)
    ''', (telegram_id, name))
    conn.commit()
    cursor.close()
    conn.close()

@bot.message_handler(commands=['save'])
def save_user(message):
    logger.info(f"Comando /save recibido de {message.from_user.username} (ID: {message.from_user.id})")
    telegram_id = message.from_user.id
    name = message.from_user.first_name
    insert_user(telegram_id, name)
    bot.reply_to(message, f'¡Bienvenido {name}! Tu información fue guardada con exito.')

# COMANDO PARA BORRAR TU NOMBRE E IP DE TELEGRAM GUARDADOS EN LA BASE DE DATOS
def remove_user(telegram_id: int):
    conn = sqlite3.connect('telegram_bot.db')
    cursor = conn.cursor()
    cursor.execute('''
    SELECT * FROM users WHERE telegram_id = ?
    ''', (telegram_id,))
    usuarioGuardado = cursor.fetchone()
    if usuarioGuardado is None:
        return f"No se encontró un usuario con ID.\nNo se puede borrar."
    else:
        cursor.execute('''
        DELETE FROM users WHERE telegram_id = ?
        ''', (telegram_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return f'¡Tu información fue eliminada con exito!'

@bot.message_handler(commands=['leave'])
def save_user(message):
    logger.info(f"Comando /leave recibido de {message.from_user.username} (ID: {message.from_user.id})")
    telegram_id = message.from_user.id
    mensajillo = remove_user(telegram_id)
    bot.reply_to(message, mensajillo)

# CUALQUIER MENSAJE QUE NO SEA UN COMANDO VALIDO SERA RESPONDIDO POR EL BOT
@bot.message_handler(func=lambda message: not message.text.startswith('/'))
def handle_non_command_message(message):
    user_input = message.text
    user_info = f"{message.from_user.username} (ID: {message.from_user.id})"
    logger.info(f"Mensaje no-comando recibido de {user_info}: '{user_input}'")
    prompt_context = f"""
    Eres un asistente amigable dentro de un bot de Telegram. Un usuario te ha enviado el siguiente mensaje:
    "{user_input}"
    Tu tarea es responder a la consulta del usuario de forma útil y concisa.
    Además, si la consulta del usuario parece relacionada con alguna funcionalidad existente, sugiérele amablemente el comando apropiado.
    Los comandos disponibles son:
    - /start - Inicia la conversación.
    - /help - Muestra esta ayuda.
    - /cuenta - Puedes acceder a tus cajas de ahorro.
    - /gasto - Ingresar un nuevo gasto a una de tus cajas de ahorro.
    - /cargar - Carga un monto de dinero a tus cajas de ahorro.
    - /save - Puedes guardar tu id de telegram y nombre de usuario en nuestra base de datos.
    - /leave - Elimina tus datos guardados con /save de nuestra base de datos.

    Ejemplos de cómo podrías responder:
    - Si el usuario pregunta "¿Qué puedes hacer?" o "¿Ayuda?", responde algo como: "¡Claro! Puedo hacer algunas cosas. Puedes ver todos mis comandos con /help."
    - Si el usuario pregunta algo general como "¿Cómo estás?", responde normalmente y quizás añade: "Recuerda que puedes usar /help para ver lo que puedo hacer."
    - Si el usuario simplemente charla, responde a la conversación. No es necesario mencionar los comandos en cada mensaje si no es relevante.

    Responde directamente al usuario. No digas "Como asistente...".
    """
    try:
        # Llama a la API de Gemini
        # Usaremos streaming como tenías, pero procesaremos la respuesta
        response_stream = model.generate_content(prompt_context, stream=True)

        full_response = ""
        for chunk in response_stream:
            # Asegúrate de que el chunk tenga texto antes de añadirlo
            if hasattr(chunk, 'text'):
                full_response += chunk.text
            else:
                logger.warning("Recibido chunk sin atributo 'text' de Gemini.")


        # Verifica si la respuesta generada no está vacía
        if full_response:
            logger.info(f"Respuesta de Gemini generada para {user_info}.")
            bot.reply_to(message, full_response)
        else:
            # Puede pasar si Gemini bloquea la respuesta por seguridad o no genera nada
            logger.warning(f"Gemini no generó texto como respuesta para {user_info}. Prompt Feedback: {response_stream.prompt_feedback if hasattr(response_stream, 'prompt_feedback') else 'N/A'}")
            bot.reply_to(message, "No pude generar una respuesta para eso en este momento. ¿Quizás podrías intentar reformularlo o usar /help para ver los comandos?")

    except Exception as e:
        logger.error(f"Error al interactuar con Gemini API para {user_info}: {e}", exc_info=True) # Muestra traceback
        # Intenta obtener feedback si está disponible en el error
        error_details = str(e)
        # A veces, información útil está en los argumentos del error
        # if hasattr(e, 'args') and e.args:
        #     # Intenta buscar información de bloqueo (esto puede variar según el error)
        #     if "response" in str(e.args[0]).lower() and "block" in str(e.args[0]).lower():
        #          error_details += "\n(Posiblemente bloqueado por filtros de seguridad de Gemini)"

        bot.reply_to(message, f"Lo siento, ocurrió un error inesperado al procesar tu mensaje con la IA.\nDetalle: {error_details}\nIntenta de nuevo más tarde o usa /help.")

    #bot.reply_to(message, response_stream)

if __name__ == "__main__":
    logger.info("Iniciando el bot...")
    #bot.polling(none_stop=True)
    bot.infinity_polling(logger_level=logging.DEBUG) # Método más robusto, con reconexión y logs detallados si se necesita
    logger.info("El bot se ha detenido.")