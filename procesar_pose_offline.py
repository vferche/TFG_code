#!/usr/bin/env python3
import subprocess
import sys
import os
import importlib.util
import urllib.request
import csv
import cv2

# ── Auto-instalación de librerías ────────────────────────────────────────────
LIBRERIAS = ["opencv-python", "mediapipe"]

def instalar_si_falta(paquetes):
    mapeo = {"opencv-python": "cv2", "mediapipe": "mediapipe"}
    pendientes = [p for p in paquetes if not importlib.util.find_spec(mapeo.get(p, p))]
    if not pendientes: return
    print("=" * 58)
    print("  Instalando librerías necesarias...")
    print("=" * 58)
    for paquete in pendientes:
        subprocess.run([sys.executable, "-m", "pip", "install", paquete], capture_output=True)
    print("  Librerías listas.\n")

instalar_si_falta(LIBRERIAS)

import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
from mediapipe.tasks.python.vision.pose_landmarker import PoseLandmarksConnections as PLC
from mediapipe.tasks.python.vision.hand_landmarker import HandLandmarksConnections as HLC

# ── Rutas de modelos ──────────────────────────────────────────────────────────
DIR_SCRIPT = os.path.dirname(os.path.abspath(__file__))
RUTA_POSE  = os.path.join(DIR_SCRIPT, "pose_landmarker_full.task")
RUTA_MANOS = os.path.join(DIR_SCRIPT, "hand_landmarker.task")

URLS_MODELOS = {
    RUTA_POSE: "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task",
    RUTA_MANOS: "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task",
}

def descargar_si_falta(ruta, url):
    if not os.path.exists(ruta):
        print(f"  Descargando modelo {os.path.basename(ruta)}...")
        urllib.request.urlretrieve(url, ruta)

# ── Carga de modelos ──────────────────────────────────────────────────────────
print("=" * 58)
print("  Inicializando modelos (Pose + Manos)")
print("=" * 58)

descargar_si_falta(RUTA_POSE, URLS_MODELOS[RUTA_POSE])
pose_model = mp_vision.PoseLandmarker.create_from_options(
    mp_vision.PoseLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=RUTA_POSE),
        num_poses=1,
        min_pose_detection_confidence=0.3,
        min_pose_presence_confidence=0.3,
        min_tracking_confidence=0.3,
    )
)

descargar_si_falta(RUTA_MANOS, URLS_MODELOS[RUTA_MANOS])
hands_model = mp_vision.HandLandmarker.create_from_options(
    mp_vision.HandLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=RUTA_MANOS),
        num_hands=2,
        min_hand_detection_confidence=0.3,
        min_hand_presence_confidence=0.3,
        min_tracking_confidence=0.3,
    )
)

# ── Rutas de Entrada y Creación de Estructura de Salida ──────────────────────
RUTAS_BASE_USB = [
    "/Volumes/SSD_VID_PRJ/clips",
    "/Volumes/SSD_VID_PRJ/clips_2"
]
CARPETAS_ANALIZAR = ["c", "d", "i"]

CARPETA_VIDEOS = os.path.join(DIR_SCRIPT, "procesados_videos")
CARPETA_DATOS = os.path.join(DIR_SCRIPT, "procesados_datos_csv")

for carpeta in CARPETAS_ANALIZAR:
    os.makedirs(os.path.join(CARPETA_VIDEOS, carpeta), exist_ok=True)
    os.makedirs(os.path.join(CARPETA_DATOS, carpeta), exist_ok=True)

lista_videos = []

# Buscar vídeos en todas las rutas origen
for ruta_base in RUTAS_BASE_USB:
    nombre_base_origen = os.path.basename(ruta_base)
    
    for carpeta in CARPETAS_ANALIZAR:
        ruta_carpeta_origen = os.path.join(ruta_base, carpeta)
        
        if os.path.exists(ruta_carpeta_origen):
            for archivo in sorted(os.listdir(ruta_carpeta_origen)):
                if archivo.lower().endswith((".mp4", ".avi", ".mov", ".mkv")):
                    lista_videos.append((nombre_base_origen, carpeta, archivo, os.path.join(ruta_carpeta_origen, archivo)))

if not lista_videos:
    print(f"\n[!] No se encontraron vídeos en las rutas: {RUTAS_BASE_USB}")
    sys.exit(1)

print(f"\nSe procesarán {len(lista_videos)} vídeos en total de forma consecutiva.")
print(f"  - Todos los vídeos se guardarán en: {CARPETA_VIDEOS} / [c|d|i]")
print(f"  - Todos los CSV se guardarán en: {CARPETA_DATOS} / [c|d|i]\n")

# ── Helpers de dibujo ────────────────────────────────────────────────────────
def dibujar_esqueleto(frame, res_pose, res_hands):
    h, w = frame.shape[:2]
    
    if res_pose and res_pose.pose_landmarks:
        lms = res_pose.pose_landmarks[0]
        for conn in PLC.POSE_LANDMARKS:
            a, b = conn.start, conn.end
            if a > 10 and b > 10: # Omitir conexiones faciales
                if min(lms[a].visibility, lms[b].visibility) > 0.3:
                    pa = (int(lms[a].x * w), int(lms[a].y * h))
                    pb = (int(lms[b].x * w), int(lms[b].y * h))
                    cv2.line(frame, pa, pb, (0, 200, 80), 2)

    if res_hands and res_hands.hand_landmarks:
        for i, hand_lms in enumerate(res_hands.hand_landmarks):
            lado = res_hands.handedness[i][0].display_name
            color = (255, 160, 0) if lado == "Left" else (0, 140, 255)
            for conn in HLC.HAND_CONNECTIONS:
                pa = (int(hand_lms[conn.start].x * w), int(hand_lms[conn.start].y * h))
                pb = (int(hand_lms[conn.end].x * w), int(hand_lms[conn.end].y * h))
                cv2.line(frame, pa, pb, color, 2)

# ── Bucle de Procesamiento ───────────────────────────────────────────────────
for idx, (base_origen, carpeta_origen, nombre_archivo, ruta_video) in enumerate(lista_videos):
    print(f"[{idx + 1}/{len(lista_videos)}] Procesando {carpeta_origen}/{nombre_archivo} ... ", end="", flush=True)
    
    cap = cv2.VideoCapture(ruta_video)
    if not cap.isOpened():
        print("[!] Error al abrir.")
        continue

    ancho = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    alto = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Conservamos el nombre original sin añadir prefijos
    nombre_base = nombre_archivo.rsplit('.', 1)[0]
    
    # Guardar todo directamente en la subcarpeta correspondiente (c, d o i)
    ruta_vid_salida = os.path.join(CARPETA_VIDEOS, carpeta_origen, f"{nombre_base}.mp4")
    out = cv2.VideoWriter(ruta_vid_salida, cv2.VideoWriter_fourcc(*'mp4v'), fps, (ancho, alto))

    ruta_csv = os.path.join(CARPETA_DATOS, carpeta_origen, f"{nombre_base}.csv")
    with open(ruta_csv, mode='w', newline='') as file_csv:
        writer = csv.writer(file_csv)
        
        # Sufijo dinámico basado en la carpeta actual ('c', 'd' o 'i')
        s = f"_{carpeta_origen}"
        
        # Cabeceras dinámicas para el CSV
        writer.writerow([
            "Frame", "Tiempo_seg", 
            f"HombroIzq_X{s}", f"HombroIzq_Y{s}", f"HombroDer_X{s}", f"HombroDer_Y{s}", 
            f"CodoIzq_X{s}", f"CodoIzq_Y{s}", f"CodoDer_X{s}", f"CodoDer_Y{s}", 
            f"MunecaIzq_X{s}", f"MunecaIzq_Y{s}", f"MunecaDer_X{s}", f"MunecaDer_Y{s}"
        ])

        frames_procesados = 0

        while True:
            ok, frame = cap.read()
            if not ok: break

            tiempo_actual_segundos = frames_procesados / fps
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

            res_pose  = pose_model.detect(mp_img)
            res_hands = hands_model.detect(mp_img)

            hi_x, hi_y = "", ""
            hd_x, hd_y = "", ""
            ci_x, ci_y = "", ""
            cd_x, cd_y = "", ""
            mi_x, mi_y = "", ""
            md_x, md_y = "", ""

            if res_pose and res_pose.pose_landmarks:
                lms = res_pose.pose_landmarks[0]
                
                if lms[11].visibility > 0.3: hi_x, hi_y = round(lms[11].x, 4), round(lms[11].y, 4)
                if lms[12].visibility > 0.3: hd_x, hd_y = round(lms[12].x, 4), round(lms[12].y, 4)
                
                if lms[13].visibility > 0.3: ci_x, ci_y = round(lms[13].x, 4), round(lms[13].y, 4)
                if lms[14].visibility > 0.3: cd_x, cd_y = round(lms[14].x, 4), round(lms[14].y, 4)
                
                if lms[15].visibility > 0.3: mi_x, mi_y = round(lms[15].x, 4), round(lms[15].y, 4)
                if lms[16].visibility > 0.3: md_x, md_y = round(lms[16].x, 4), round(lms[16].y, 4)

            writer.writerow([
                frames_procesados, round(tiempo_actual_segundos, 3), 
                hi_x, hi_y, hd_x, hd_y, 
                ci_x, ci_y, cd_x, cd_y, 
                mi_x, mi_y, md_x, md_y
            ])

            frame_vis = frame.copy()
            dibujar_esqueleto(frame_vis, res_pose, res_hands)
            out.write(frame_vis)
            
            frames_procesados += 1
            if frames_procesados % 60 == 0:
                print(f"{int((frames_procesados / total_frames) * 100) if total_frames > 0 else 0}% ", end="", flush=True)

    cap.release()
    out.release()
    print(" ✓ Completado")