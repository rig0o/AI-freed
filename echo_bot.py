import telebot
import sqlite3
import os
from dotenv import load_dotenv
#from modelo import *
from funciones import *
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
def detectar_bytes(img_str):
    nparr = np.fromstring(img_str, np.uint8)
    img_np = cv2.imdecode(nparr, cv2.CV_LOAD_IMAGE_COLOR)
    imgs2 = [img_np]
    # cargar imagen o imagenes
    img = cuadrante(imgs2)
    gris = filtro_gris(img)
    ths = filtro_th(gris,umbral=70)
    contorno, _ = contornos(img, ths)
    candidatos, _ = busqueda(img, contorno)
    candidatos, _ = busqueda2(img, candidatos)
    placas, _ = filtro3(img, candidatos)
    recortes = cortar(img, placas)
    x = guardar(recortes, '/home/rodrigo/Workspace/AI-Fred/aifreed/img/output')
    return recortes


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
    conexion = sqlite3.connect("db/aifred.sqlite3")
    cursor = conexion.cursor()
    cursor.execute("INSERT INTO vehiculos_permitidos (id_usuario, patente) VALUES ((SELECT id FROM usuarios WHERE chat_id = ?), ?)", (chat_id, patente))
    conexion.commit()
    conexion.close()

def eliminarVehiculo(chat_id, patente):
    conexion = sqlite3.connect("db/aifred.sqlite3")
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM vehiculos_permitidos WHERE id_usuario = (SELECT id FROM usuarios WHERE chat_id = ?) AND patente = ?", (chat_id, patente))
    conexion.commit()
    conexion.close()

def agregarUsuarioBD(chat_id,nombre):
    conexion = sqlite3.connect("db/aifred.sqlite3")
    cursor = conexion.cursor()
    cursor.execute("INSERT INTO usuario_pendiente (chat_id, nombre) VALUES (?, ?)", (chat_id, nombre))
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
        if consultarUsuario(message.chat.id) == None and consultarUsuario_pendiente(message.chat.id) == None:
            agregarUsuarioBD(message.chat.id, message.chat.first_name)
    else:
        bot.reply_to(message, "Bienvenido de nuevo, " + consultarUsuario(message.chat.id)[1])

@bot.message_handler(commands=['consultar'])
def consultar_vehiculos(message):
    if consultarUsuario(message.chat.id) == None:
        bot.reply_to(message, "Para poder usar AIFred, debes registrarte")
        bot.reply_to(message, "Ponte en contacto con el administrador de la parcela")
    else:
        bot.reply_to(message, "Estos son los vehiculos que tienes registrados:")
        for vehiculo in consultarVehiculosUsuario(message.chat.id):
            bot.reply_to(message, vehiculo[2])

@bot.message_handler(commands=['registrar'])
def registrar_vehiculo(message):
    texto_registrar = " ".join(message.text.split()[1:])
    if not texto_registrar:
        bot.reply_to(message, "Debes ingresar la patente del vehiculo")
        return 1
    else:
        return 0

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


@bot.message_handler(commands=['test'])
def imgen_test(message):
    dir_in = "/home/rodrigo/Workspace/AI-Fred/aifreed/img/input"
    dir_out = "/home/rodrigo/Workspace/AI-Fred/aifreed/img/output"
    patente = detectar(dir_in, dir_out)
    txt = img_to_txt(patente)
    recibir_patente(txt)
    bot.reply_to(message, txt)


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
    conexion.close()
    for usuario in usuarios:
        bot.send_message(usuario, f"Se ha detectado un vehiculo con la patente : {patente} en el porton. Desea abrir el porton?")


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
            registrar_vehiculo(message.chat.id, patente)
            eliminarPatentePendiente()
            bot.reply_to(message, "Abriendo porton")

@bot.message_handler(content_types=['text'])
def send_text(message):
    if message.text.startswith("/"):
        bot.reply_to(message, "No entiendo el comando")
    else:
        bot.send_message(message.chat.id, "No estoy hecho para responder, solo para recibir comandos 🤖")

@bot.message_handler(content_types=['photo'])
def send_photo(message):
    #save photo
    fileID = message.photo[-1].file_id
    file_info = bot.get_file(fileID)
    downloaded_file = bot.download_file(file_info.file_path)
    src = 'img2/' + fileID + '.jpg'
    
    with open(src, 'wb') as new_file:
        new_file.write(downloaded_file)

#main
if __name__ == '__main__':


    lista = [telebot.types.BotCommand(command="/inicio", description="Iniciar el bot"),
                telebot.types.BotCommand(command="/consultar", description="Consulta los vehiculos que tienes registrados"),
                telebot.types.BotCommand(command="/abrir", description="Abre el porton si es que existe un auto"),]
    bot.set_my_commands(lista)
    print("Bot iniciado")
    bot.polling(none_stop=True)