import cv2
import numpy as np
import time
from datetime import datetime



def camara():
    cap = cv2.VideoCapture('video/vid_1.mp4')
    fgbg = cv2.bgsegm.createBackgroundSubtractorMOG()
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(3,3))
    frame_rate = 4
    prev = 0
    i = 0
    cv2.namedWindow('frame', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('frame', 1000, 500)
    while True:
        time_elapsed = time.time() - prev
        ret, frame = cap.read()
        if ret == False:
            print('Error o Fin del video')
            break
        if time_elapsed > 1./frame_rate:

            #Puntos donde se buscara
            area_pts = np.array([[500, 600],[1800,600],[1800,1000],[500,1000]])
            #Frame a gris
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)


            # recorte
            recorte = np.zeros(shape=(frame.shape[:2]), dtype=np.uint8)
            recorte = cv2.drawContours(recorte, [area_pts],-1,(255),-1)
            img_area = cv2.bitwise_and(gray,gray,mask=recorte)

            #Obtendremos la imagen binaria
            fgmask = fgbg.apply(img_area)
            fgmask = cv2.morphologyEx(fgmask, cv2.MORPH_OPEN, kernel)
            fgmask = cv2.dilate(fgmask, None, iterations=2)

            #Filtra contornes segun el area
            cnts = cv2.findContours(fgmask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]
            path = '/home/rodrigo/Workspace/AI-freed/img/output_video'

            for cnt in cnts:
                if cv2.contourArea(cnt) > 450000:
                    i = i+1
                    print(f'{i}--{cv2.contourArea(cnt)}')
                    cv2.imwrite(f'{path}/frame{datetime.now()}.png',frame)

            cv2.imshow('frame',frame)
            prev = time.time()
        k = cv2.waitKey(20)&0xFF
        if k == 27:
            break
    cap.release()
    cv2.destroyAllWindows()