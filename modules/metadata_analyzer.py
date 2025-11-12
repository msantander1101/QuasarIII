import exifread
from PIL import Image
import io
import base64


def extraer_metadata(imagen_bytes):
    """
    Extrae metadata EXIF y básica de imágenes
    """
    metadata = {}

    # Leer con PIL
    img = Image.open(imagen_bytes)
    metadata['formato'] = img.format
    metadata['modo'] = img.mode
    metadata['dimensiones'] = f"{img.width}x{img.height}"

    # EXIF data
    imagen_bytes.seek(0)
    tags = exifread.process_file(imagen_bytes)

    for tag, valor in tags.items():
        if tag not in ('JPEGThumbnail', 'TIFFThumbnail'):
            metadata[tag] = str(valor)

    # Buscar GPS
    gps_tags = ['GPS GPSLatitude', 'GPS GPSLongitude', 'GPS GPSLatitudeRef', 'GPS GPSLongitudeRef']
    if any(tag in metadata for tag in gps_tags):
        metadata['contiene_ubicacion'] = True

    return metadata


def get_gps_coords(metadata):
    """
    Convierte datos EXIF GPS a coordenadas decimales
    """
    if 'GPS GPSLatitude' in metadata and 'GPS GPSLongitude' in metadata:
        lat = convertir_gps_a_decimal(metadata['GPS GPSLatitude'])
        lon = convertir_gps_a_decimal(metadata['GPS GPSLongitude'])

        # Ajustar signo según referencia
        if 'GPS GPSLatitudeRef' in metadata and metadata['GPS GPSLatitudeRef'] == 'S':
            lat = -lat
        if 'GPS GPSLongitudeRef' in metadata and metadata['GPS GPSLongitudeRef'] == 'W':
            lon = -lon

        return lat, lon
    return None


def convertir_gps_a_decimal(grado_str):
    """
    Convierte string GPS EXIF a decimal
    """
    # Implementación de conversión...
    pass