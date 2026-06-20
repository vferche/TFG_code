#!/bin/bash

# ==================================================
# Script para extracción y sincronización de clips 
# adaptado para macOS y nueva estructura.
# Nombres de archivo actualizados.
# ==================================================

USB_PATH="/Volumes/SSD_VID_PRJ"

# Rutas de los vídeos de origen con los nombres exactos
VIDEO_C="$USB_PATH/videos_originales/c/VID_20260522_163003.mp4"
VIDEO_D="$USB_PATH/videos_originales/d/VID_20260522_162746.mp4"
VIDEO_I="$USB_PATH/videos_originales/i/VID_20260522_163118.mp4"

# Rutas de los directorios de destino
OUT_C="$USB_PATH/clips_2/c"
OUT_D="$USB_PATH/clips_2/d"
OUT_I="$USB_PATH/clips_2/i"

# --- FUNCIONES ---
to_seconds() {
    IFS=: read -r h m s <<< "$1"

    if [ -z "$s" ]; then
        s=$m
        m=$h
        h=0
    fi

    echo $((10#$h*3600 + 10#$m*60 + 10#$s))
}

# --- LISTA DE CLIPS (Tiempo de inicio y Duración) ---
CLIPS=(
"00:08:54 7"   
"00:34:30 13"  
"00:09:07 3"   
"00:33:56 4"   
"00:09:15 11"  
"00:09:28 8"   
"00:28:00 6"   
"00:09:38 8"   
"00:09:50 4"   
"00:11:08 7"   
"00:13:22 8"   
"00:13:51 19"  
"00:13:31 9"   
"00:14:25 14"  
"00:16:08 18"  
"00:19:08 12"  
"00:22:14 8"   
"00:22:59 4"   
"00:28:16 15"  
"00:29:34 15"  
"00:39:39 6"  
)

# --- PREPARACIÓN DE DIRECTORIOS ---
mkdir -p "$OUT_C" "$OUT_D" "$OUT_I"
rm -f "$OUT_C"/*.mp4 "$OUT_D"/*.mp4 "$OUT_I"/*.mp4

# El contador empieza en 30
i=30

# --- BUCLE DE EXTRACCIÓN ---
for clip in "${CLIPS[@]}"; do
    START=$(echo $clip | awk '{print $1}')
    DUR=$(echo $clip | awk '{print $2}')

    SEC=$(to_seconds "$START")

    # --- AJUSTE DE SINCRONIZACIÓN ---
    SEC_D=$(echo "$SEC + 137" | bc)
    SEC_I=$(echo "$SEC - 75" | bc)

    echo "Procesando clip_$i.mp4 ..."
    echo "vid_c -> $START (Duración: $DUR)"
    echo "vid_d -> $SEC_D seg"
    echo "vid_i -> $SEC_I seg"
    echo "-----------------------------------"

    # Extracción de clips usando copy sin recodificar para máxima velocidad
    ffmpeg -ss "$START" -i "$VIDEO_C" -t "$DUR" -c copy "$OUT_C/clip_$i.mp4"
    ffmpeg -ss "$SEC_D" -i "$VIDEO_D" -t "$DUR" -c copy "$OUT_D/clip_$i.mp4"
    ffmpeg -ss "$SEC_I" -i "$VIDEO_I" -t "$DUR" -c copy "$OUT_I/clip_$i.mp4"

    ((i++))
done