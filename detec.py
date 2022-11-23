from funciones import *



dir_in = "/home/rodrigo/Workspace/AI-freed/img/input"
dir_out = "/home/rodrigo/Workspace/AI-Fred/img/output_video"


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

x = guardar(recortes, "/home/rodrigo/Workspace/AI-freed/img/output")
