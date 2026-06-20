if [ ! -f "/ffmpeg_bin" ]; then
    echo "========================================================="
    echo " Descargando conversor de vídeo (FFmpeg)..."
    echo "========================================================="
    apt-get update && apt-get install -y wget xz-utils
    wget -q https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz
    tar -xf ffmpeg-release-amd64-static.tar.xz
    cp ffmpeg-*-static/ffmpeg /ffmpeg_bin
    chmod +x /ffmpeg_bin
    echo "¡Conversor listo!"
fi

for carpeta in c d i; do
    mkdir -p "/data/openface_csv/$carpeta"
    for num in {1..50}; do
        for video in /data/$carpeta/*clip*${num}.*; do
            # Evitar procesar los archivos temporales si se interrumpió antes
            if [[ "$video" != *"temp_"* ]] && [ -f "$video" ]; then
                echo "========================================================="
                echo " Procesando perspectiva [$carpeta] - Vídeo: $(basename "$video")"
                echo "========================================================="
                
                nombre_base=$(basename "$video" | cut -d. -f1)
                temp_video="/data/$carpeta/temp_${nombre_base}.mp4"
                
                echo " -> Convirtiendo a H.264 (tarda unos segundos)..."
                # Añadido -nostdin para evitar que se pause esperando comandos
                /ffmpeg_bin -nostdin -y -i "$video" -c:v libx264 -preset fast -an "$temp_video" -loglevel error
                
                # Comprobar que el video temporal se creó correctamente
                if [ -f "$temp_video" ]; then
                    echo " -> Extrayendo microexpresiones con OpenFace..."
                    /home/openface-build/build/bin/FeatureExtraction -f "$temp_video" -out_dir "/data/openface_csv/$carpeta/"
                    
                    echo " -> Limpiando..."
                    rm -f "$temp_video"
                else
                    echo " ERROR: No se pudo convertir el vídeo $video"
                fi
            fi
        done
    done
done
echo "¡TODOS LOS CLIPS DEL 1 AL 50 PROCESADOS CON ÉXITO!"