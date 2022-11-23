import telebot
import sqlite3
import os
from dotenv import load_dotenv
from telebot.types import InlineKeyboardButton
from telebot.types import InlineKeyboardMarkup
from funciones import *
from is_car import *
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from PIL import Image
import io
#from cv2 import cv


load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)

procesador = TrOCRProcessor.from_pretrained('microsoft/trocr-large-printed')
modelo = VisionEncoderDecoderModel.from_pretrained('microsoft/trocr-large-printed')


def detectar(dir_in, dir_out):
    # cargar imagen o imagenes
    imgs0 = load_images_from_folder(dir_in)
    img = cuadrante(imgs0)
    gris = filtro_gris(img)
    ths = filtro_th(gris,umbral=70)
    contorno, _ = contornos(img, ths)
    candidatos, _ = busqueda(img, contorno)
    candidatos, _ = busqueda2(img, candidatos)
    placas, _ = filtro3(img, candidatos)
    recortes = cortar(img, placas)
    x = guardar(recortes, dir_out)
    return recortes

def detectar_imagen(imagen):
    dir_out = "/home/rodrigo/Workspace/AI-Fred/aifreed/img/output"
    imgs = []
    imgs.append(imagen)
    print(f' imagen sola -> {imagen.shape}')
    # cargar imagen o imagenes
    img = cuadrante(imgs)
    gris = filtro_gris(img)
    ths = filtro_th(gris,umbral=70)
    contorno, _ = contornos(img, ths)
    candidatos, _ = busqueda(img, contorno)
    candidatos, _ = busqueda2(img, candidatos)
    placas, _ = filtro3(img, candidatos)
    recortes = cortar(img, placas)
    guardar(recortes, dir_out)
    return recortes

def bytes_imagen(img_str):
    nparry = np.asarray(bytearray(img_str), dtype="uint8")
    cv2image = cv2.imdecode(nparry, cv2.IMREAD_COLOR)
    return cv2image


def img_to_txt(images):
    txt = []
    for img in images:
        tensor_pixel = procesador(images=img, return_tensors="pt").pixel_values
        generated_ids = modelo.generate(tensor_pixel)
        txt.append(procesador.batch_decode(generated_ids, skip_special_tokens=True)[0])
    return txt

def consultarUsuario(chat_id):
    conexion = sqlite3.connect("db/aifred.sqlite3")
    cursor = conexion.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE chat_id = ?", (chat_id,))
    usuario = cursor.fetchone()
    conexion.close()
    return usuario

def consultarUsuario_pendiente():
    conexion = sqlite3.connect("db/aifred.sqlite3")
    cursor = conexion.cursor()
    cursor.execute("SELECT * FROM usuario_pendiente")
    usuario = cursor.fetchall()
    conexion.close()
    return usuario

def consultarVehiculosUsuario(chat_id):
    conexion = sqlite3.connect("db/aifred.sqlite3")
    cursor = conexion.cursor()
    cursor.execute("SELECT * FROM vehiculos_permitidos WHERE id_usuario = (SELECT id FROM usuarios WHERE chat_id = ?)", (chat_id,))
    vehiculos = cursor.fetchall()
    conexion.close()
    return vehiculos

def consultarPatentePendiente():
    conexion = sqlite3.connect("db/aifred.sqlite3")
    cursor = conexion.cursor()
    cursor.execute("SELECT patente FROM patente_pendiente")
    patente = cursor.fetchone()
    conexion.close()
    return patente

def eliminarPatentePendiente():
    conexion = sqlite3.connect("db/aifred.sqlite3")
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM patente_pendiente")
    conexion.commit()
    conexion.close()

def registrarVehiculo(chat_id, patente):
    patente = patente.upper()
    conexion = sqlite3.connect("db/aifred.sqlite3")
    cursor = conexion.cursor()
    cursor.execute("INSERT INTO vehiculos_permitidos (id_usuario, patente) VALUES ((SELECT id FROM usuarios WHERE chat_id = ?), ?)", (chat_id, patente))
    #cursor.execute("INSERT INTO vehiculos_permitidos (id_usuario, patente) VALUES (?, ?)", (chat_id, patente))
    conexion.commit()
    conexion.close()

def eliminarVehiculo(chat_id, patente):
    patente = patente.upper()
    conexion = sqlite3.connect("db/aifred.sqlite3")
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM vehiculos_permitidos WHERE id_usuario = (SELECT id FROM usuarios WHERE chat_id = ?) AND patente = ?", (chat_id, patente))
    conexion.commit()
    conexion.close()

def agregarUsuarioBD(chat_id,nombre, apellido):
    conexion = sqlite3.connect("db/aifred.sqlite3")
    cursor = conexion.cursor()
    cursor.execute("INSERT INTO usuarios (nombre, apellido, chat_id) VALUES (?, ?,?)", (nombre,apellido,chat_id))
    conexion.commit()
    conexion.close()

def agregarUsuarioParcela(chat_id, nombre):
    conexion = sqlite3.connect("db/aifred.sqlite3")
    cursor = conexion.cursor()
    cursor.execute("INSERT INTO usuarios (chat_id) VALUES (?,?)", (chat_id,nombre))
    conexion.commit()
    conexion.close()


@bot.message_handler(commands=['inicio'])
def send_welcome(message):
    bot.reply_to(message, "AIFred, tu porton inteligente")
    if consultarUsuario(message.chat.id) == None:
        bot.reply_to(message, "Para poder usar AIFred, debes registrarte")
        bot.reply_to(message, "Ponte en contacto con el administrador de la parcela")
        if consultarUsuario(message.chat.id) == None:
            if not message.chat.last_name == None: 
                agregarUsuarioBD(message.chat.id, message.chat.first_name, message.chat.last_name)
            else:
                agregarUsuarioBD(message.chat.id, message.chat.first_name, 'perez')
    else:
        bot.reply_to(message, "Bienvenido de nuevo, " + consultarUsuario(message.chat.id)[1])

@bot.message_handler(commands=['consultar'])
def consultar_vehiculos(message):
    if consultarUsuario(message.chat.id) == None:
        bot.reply_to(message, "Para poder usar AIFred, debes registrarte")
        #bot.reply_to(message, "Ponte en contacto con el administrador de la parcela")
    else:
        #bot.reply_to(message, "Estos son los vehiculos que tienes registrados:")
        patentes = "Estos son los vehiculos que tienes registrados: \n"
        for vehiculo in consultarVehiculosUsuario(message.chat.id):
            patentes = '{}{}\n'.format(patentes, vehiculo[2])
        bot.reply_to(message, patentes)

@bot.message_handler(commands=['registrar'])
def registrar_vehiculo(message):
    print('registrar por comando')
    texto_registrar = message.text.split()[1:]
    if not texto_registrar:
        texto = 'Debes ingresar una patente \n'
        texto += 'Ejemplo:\n'
        texto += f'<code>{message.text} AABB01 </code>'
        bot.send_message(message.chat.id, texto,parse_mode="html")
        #bot.reply_to(message,texto,parse_mode="html")

    else:
        for patente in texto_registrar:
            registrarVehiculo(message.chat.id,patente= patente)
        bot.send_message(message.chat.id, f'Patentes registradas:{texto_registrar}')
        #bot.reply_to(message, f'Patentes registradas:{texto_registrar}')


@bot.message_handler(commands=['borrar'])
def borrar_vehiculo(message):
    texto_registrar = message.text.split()[1:]
    if not texto_registrar:
        bot.reply_to(message, "Debes ingresar la patente del vehiculo /borrar AABB00")
    else:
        for patente in texto_registrar:
            eliminarVehiculo(message.chat.id,patente= patente)
        bot.reply_to(message, f'Patentes borrados:{texto_registrar}')

@bot.message_handler(commands=['pendientes'])
def usuarios_pendientes(message):
    if consultarUsuario(message.chat.id) == None:
        bot.reply_to(message, "Para poder usar AIFred, debes registrarte")
        bot.reply_to(message, "Ponte en contacto con el administrador de la parcela")
    else:
        print(consultarUsuario(message.chat.id)[0])
        if consultarUsuario(message.chat.id)[0] == 1 and consultarUsuario_pendiente() != None:
            bot.reply_to(message, "Estos son los usuarios pendientes de registrar:")
            for usuario in consultarUsuario_pendiente():
                bot.reply_to(message, usuario[0]+" - "+usuario[1])
        else:
            bot.reply_to(message, "Esta funcion es solo para el admin")


@bot.message_handler(commands=['demo'])
def video_test(message):
    dir_in = "/home/rodrigo/Workspace/AI-freed/img/input"
    dir_out = "/home/rodrigo/Workspace/AI-freed/img/output"
    patente = detectar(dir_in, dir_out)
    txt = img_to_txt(patente)
    print(txt)
    txt = limpiar(txt)
    bot.reply_to(message, txt)

@bot.message_handler(commands=['demo2'])
def video_test(message):
    camara()


def recibir_patente(patente):
    patente = patente.replace(" ", "")
    patente = patente.replace("-", "")
    patente = patente.upper()
    usuarios = []
    conexion = sqlite3.connect("db/aifred.sqlite3")
    cursor = conexion.cursor()
    cursor.execute("SELECT chat_id FROM usuarios")
    for usuario in cursor.fetchall():
        usuarios.append(usuario[0])
    #conexion.close()
    cursor = conexion.cursor()
    #insertar patente en la tabla de patentes pendientes
    cursor.execute("INSERT INTO patente_pendiente (patente) VALUES (?)", (patente,))
    conexion.commit()
    conexion.close()
    #enviar mensaje a todos los usuarios
    markup = InlineKeyboardMarkup(row_width=1)
    b1 = InlineKeyboardButton("si",callback_data="si")
    b2 = InlineKeyboardButton("no",callback_data="no")
    markup.add(b1,b2)
    for usuario in usuarios:
        bot.send_message(usuario, f"Se ha detectado un vehiculo con la patente : {patente} en el porton. Desea abrir el porton?",reply_markup=markup)


@bot.callback_query_handler(func=lambda x: True)
def boton_abrir(call):
    cid = call.from_user.id
    mid = call.message.id
    if call.data == "si":
        if consultarPatentePendiente() == None:
            bot.send_message(cid, "No hay vehiculos en el porton")
        else:
            patente = consultarPatentePendiente()[0]
            registrarVehiculo(cid, patente)
            eliminarPatentePendiente()
            bot.send_message(cid, f'Abriendo porton')
        bot.delete_message(cid,mid)
    elif(call.data == "no"):
        bot.delete_message(cid,mid)
        
@bot.message_handler(commands=['abrir'])
def abrir_porton(message):
    if consultarUsuario(message.chat.id) == None:
        bot.reply_to(message, "Para poder usar AIFred, debes registrarte")
        bot.reply_to(message, "Ponte en contacto con el administrador de la parcela")
    else:
        if consultarPatentePendiente() == None:
            bot.reply_to(message, "No hay vehiculos en el porton")
        else:
            patente = consultarPatentePendiente()[0]
            registrarVehiculo(message.chat.id, patente)
            eliminarPatentePendiente()
            bot.reply_to(message, "Abriendo porton")

@bot.message_handler(content_types=['text'])
def send_text(message):
    if message.text.startswith("/"):
        bot.reply_to(message, "No entiendo el comando")
    else:
        #bot.send_message(message.chat.id, "No estoy hecho para responder, solo para recibir comandos 🤖")
        recibir_patente(message.text)

@bot.message_handler(content_types=['photo'])
def send_photo(message):
    print('registrar por foto')
    msg = "{} - {}".format(" ",message.text) 
    fileID = message.photo[-1].file_id
    file_info = bot.get_file(fileID)
    downloaded_file = bot.download_file(file_info.file_path)
    imagen = bytes_imagen(downloaded_file)
    cv2.imwrite("/home/rodrigo/Workspace/AI-Fred/aifreed/img2/llega.jpg", imagen)
    print(msg)
    
    '''
    patente = detectar_imagen(imagen)
    texto = img_to_txt(patente)
    txt = texto[0]
    txt = txt.replace(" ", "")
    txt = txt.replace("-", "")
    txt = txt.replace(".", "")
    txt = txt.replace(":", "")
    txt = txt.upper()
    registrarVehiculo(message.chat.id,txt)
    bot.reply_to(message, f'patente registrada {txt}')
    '''


#main
if __name__ == '__main__':
    lista = [
            telebot.types.BotCommand(command="/abrir", description="Abre el porton si es que existe un auto"),
            telebot.types.BotCommand(command="/registrar", description="Registrar una patente nueva"),
            telebot.types.BotCommand(command="/consultar", description="Consulta los vehiculos que tienes registrados"),
            telebot.types.BotCommand(command="/inicio", description="Iniciar el bot"),
            ]
    bot.set_my_commands(lista)
    print("Bot iniciado")
    bot.polling(none_stop=True)
