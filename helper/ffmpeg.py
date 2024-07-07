import asyncio
import json
import math
import os
import re
import subprocess
import time

from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

import ffmpeg

from .. import LOGGER, download_dir, encode_dir
from .database.access_db import db
from .display_progress import TimeFormatter


def get_codec(filepath, channel='v:0'):
    output = subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', channel,
                                      '-show_entries', 'stream=codec_name,codec_tag_string', '-of',
                                      'default=nokey=1:noprint_wrappers=1', filepath])
    return output.decode('utf-8').split()


async def fix_thumb(thumb):
    width = 0
    height = 0
    try:
        if thumb != None:
            parser = createParser(thumb)
            metadata = extractMetadata(parser)
            if metadata.has("width"):
                width = metadata.get("width")
            if metadata.has("height"):
                height = metadata.get("height")
                
            # Open the image file
            with Image.open(thumb) as img:
                # Convert the image to RGB format and save it back to the same file
                img.convert("RGB").save(thumb)
            
                # Resize the image
                resized_img = img.resize((width, height))
                
                # Save the resized image in JPEG format
                resized_img.save(thumb, "JPEG")
            parser.close()
    except Exception as e:
        print(e)
        thumb = None 
       
    return width, height, thumb
    
async def extract_subs(filepath, msg, user_id):

    path, extension = os.path.splitext(filepath)
    name = path.split('/')
    check = get_codec(filepath, channel='s:0')
    if check == []:
        return None
    elif check == 'pgs':
        return None
    else:
        output = encode_dir + str(msg.id) + '.ass'
    subprocess.call(['ffmpeg', '-y', '-i', filepath, '-map', 's:0', output])
    subprocess.call(['mkvextract', 'attachments', filepath, '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16',
                    '17', '18', '19', '20', '21', '22', '23', '24', '25', '26', '27', '28', '29', '30', '31', '32', '33', '34', '35', '36', '37', '38', '39', '40'])
    subprocess.run([f"mv -f *.JFPROJ *.FNT *.PFA *.ETX *.WOFF *.FOT *.TTF *.SFD *.VLW *.VFB *.PFB *.OTF *.GXF *.WOFF2 *.ODTTF *.BF *.CHR *.TTC *.BDF *.FON *.GF *.PMT *.AMFM  *.MF *.PFM *.COMPOSITEFONT *.PF2 *.GDR *.ABF *.VNF *.PCF *.SFP *.MXF *.DFONT *.UFO *.PFR *.TFM *.GLIF *.XFN *.AFM *.TTE *.XFT *.ACFM *.EOT *.FFIL *.PK *.SUIT *.NFTR *.EUF *.TXF *.CHA *.LWFN *.T65 *.MCF *.YTF *.F3F *.FEA *.SFT *.PFT /usr/share/fonts/"], shell=True)
    subprocess.run([f"mv -f *.jfproj *.fnt *.pfa *.etx *.woff *.fot *.ttf *.sfd *.vlw *.vfb *.pfb *.otf *.gxf *.woff2 *.odttf *.bf *.chr *.ttc *.bdf *.fon *.gf *.pmt *.amfm  *.mf *.pfm *.compositefont *.pf2 *.gdr *.abf *.vnf *.pcf *.sfp *.mxf *.dfont *.ufo *.pfr *.tfm *.glif *.xfn *.afm *.tte *.xft *.acfm *.eot *.ffil *.pk *.suit *.nftr *.euf *.txf *.cha *.lwfn *.t65 *.mcf *.ytf *.f3f *.fea *.sft *.pft /usr/share/fonts/ && fc-cache -f"], shell=True)
    return output


async def encode(filepath, message, msg):

    ex = await db.get_extensions(message.from_user.id)
    path, extension = os.path.splitext(filepath)
    name = path.split('/')

    if ex == 'MP4':
        output_filepathh = encode_dir + name[len(name)-1] + '.mp4'
    elif ex == 'AVI':
        output_filepathh = encode_dir + name[len(name)-1] + '.avi'
    else:
        output_filepathh = encode_dir + name[len(name)-1] + '.mkv'

    output_filepath = output_filepathh
    subtitles_path = encode_dir + str(msg.id) + '.ass'

    progress = download_dir + "process.txt"
    with open(progress, 'w') as f:
        pass

    assert(output_filepath != filepath)

    # Check Path
    if os.path.isfile(output_filepath):
        LOGGER.warning(f'"{output_filepath}": file already exists')
    else:
        LOGGER.info(filepath)

    # HEVC Encode
    x265 = await db.get_hevc(message.from_user.id)
    video_i = get_codec(filepath, channel='v:0')
    if video_i == []:
        codec = ''
    else:
        if x265:
            codec = '-c:v libx265'
        else:
            codec = '-c:v libx264'

    # Tune Encode
    tune = await db.get_tune(message.from_user.id)
    if tune:
        tunevideo = '-tune animation'
    else:
        tunevideo = '-tune film'

    # CABAC
    cbb = await db.get_cabac(message.from_user.id)
    if cbb:
        cabac = '-coder 1'
    else:
        cabac = '-coder 0'

    # Reframe
    rf = await db.get_reframe(message.from_user.id)
    if rf == '4':
        reframe = '-refs 4'
    elif rf == '8':
        reframe = '-refs 8'
    elif rf == '16':
        reframe = '-refs 16'
    else:
        reframe = ''

    # Bits
    b = await db.get_bits(message.from_user.id)
    if not b:
        codec += ' -pix_fmt yuv420p'
    else:
        codec += ' -pix_fmt yuv420p10le'

    # CRF
    crf = await db.get_crf(message.from_user.id)
    if crf:
        Crf = f'-crf {crf}'
    else:
        await db.set_crf(message.from_user.id, crf=26)
        Crf = '-crf 26'

    # Frame
    fr = await db.get_frame(message.from_user.id)
    if fr == 'ntsc':
        frame = '-r ntsc'
    elif fr == 'pal':
        frame = '-r pal'
    elif fr == 'film':
        frame = '-r film'
    elif fr == '23.976':
        frame = '-r 24000/1001'
    elif fr == '30':
        frame = '-r 30'
    elif fr == '60':
        frame = '-r 60'
    else:
        frame = ''

    # Aspect ratio
    ap = await db.get_aspect(message.from_user.id)
    if ap:
        aspect = '-aspect 16:9'
    else:
        aspect = ''

    # Preset
    p = await db.get_preset(message.from_user.id)
    if p == 'uf':
        preset = '-preset ultrafast'
    elif p == 'sf':
        preset = '-preset superfast'
    elif p == 'vf':
        preset = '-preset veryfast'
    elif p == 'f':
        preset = '-preset fast'
    elif p == 'm':
        preset = '-preset medium'
    else:
        preset = '-preset slow'

    # Some Optional Things
    x265 = await db.get_hevc(message.from_user.id)
    if x265:
        video_opts = f'-profile:v main  -map 0:v? -map_chapters 0 -map_metadata 0'
    else:
        video_opts = f'{cabac} {reframe} -profile:v main  -map 0:v? -map_chapters 0 -map_metadata 0'

    # Metadata Watermark
    m = await db.get_metadata_w(message.from_user.id)
    if m:
        metadata = '-metadata title=Weeb-Zone.Blogspot.com -metadata:s:v title=Weeb-Zone.Blogspot.com -metadata:s:a title=Weeb-Zone.Blogspot.com'
    else:
        metadata = ''

    # Copy Subtitles
    h = await db.get_hardsub(message.from_user.id)
    s = await db.get_subtitles(message.from_user.id)
    subs_i = get_codec(filepath, channel='s:0')
    if subs_i == []:
        subtitles = ''
    else:
        if s:
            if h:
                subtitles = ''
            else:
                subtitles = '-c:s copy -c:t copy -map 0:t? -map 0:s?'
        else:
            subtitles = ''


#    ffmpeg_filter = ':'.join([
#        'drawtext=fontfile=/app/bot/utils/watermark/font.ttf',
#        f"text='Weeb-Zone.Blogspot.com'",
#        f'fontcolor=white',
#        'fontsize=main_h/20',
#        f'x=40:y=40'
#    ])

    # Watermark and Resolution
    r = await db.get_resolution(message.from_user.id)
    w = await db.get_watermark(message.from_user.id)
    if r == 'OG':
        watermark = ''
    elif r == '1080':
        watermark = '-vf scale=1920:1080'
    elif r == '720':
        watermark = '-vf scale=1280:720'
    elif r == '576':
        watermark = '-vf scale=768:576'
    else:
        watermark = '-vf scale=852:480'
    if w:
        if r == 'OG':
            watermark += '-vf '
        else:
            watermark += ','
        watermark += 'subtitles=VideoEncoder/utils/extras/watermark.ass
    # Hard Subs
    if h:
        if r == 'OG':
            if w:
                watermark += ','
            else:
                watermark += '-vf '
        else:
            watermark += ','
        watermark += f'subtitles={subtitles_path}'

    # Sample rate
    sr = await db.get_samplerate(message.from_user.id)
    if sr == '44.1K':
        sample = '-ar 44100'
    elif sr == '48K':
        sample = '-ar 48000'
    else:
        sample = ''

    # bit rate
    bit = await db.get_bitrate(message.from_user.id)
    if bit == '400':
        bitrate = '-b:a 400k'
    elif bit == '320':
        bitrate = '-b:a 320k'
    elif bit == '256':
        bitrate = '-b:a 256k'
    elif bit == '224':
        bitrate = '-b:a 224k'
    elif bit == '192':
        bitrate = '-b:a 192k'
    elif bit == '160':
        bitrate = '-b:a 160k'
    elif bit == '128':
        bitrate = '-b:a 128k'
    else:
        bitrate = ''

    # Audio
    a = await db.get_audio(message.from_user.id)
    a_i = get_codec(filepath, channel='a:0')
    if a_i == []:
        audio_opts = ''
    else:
        if a == 'dd':
            audio_opts = f'-c:a ac3 {sample} {bitrate} -map 0:a?'
        elif a == 'aac':
            audio_opts = f'-c:a aac {sample} {bitrate} -map 0:a?'
        elif a == 'vorbis':
            audio_opts = f'-c:a libvorbis {sample} {bitrate} -map 0:a?'
        elif a == 'alac':
            audio_opts = f'-c:a alac {sample} {bitrate} -map 0:a?'
        elif a == 'opus':
            audio_opts = f'-c:a libopus -vbr on {sample} {bitrate} -map 0:a?'
        else:
            audio_opts = '-c:a copy -map 0:a?'

    # Audio Channel
    c = await db.get_channels(message.from_user.id)
    if c == '1.0':
        channels = '-rematrix_maxval 1.0 -ac 1'
    elif c == '2.0':
        channels = '-rematrix_maxval 1.0 -ac 2'
    elif c == '2.1':
        channels = '-rematrix_maxval 1.0 -ac 3'
    elif c == '5.1':
        channels = '-rematrix_maxval 1.0 -ac 6'
    elif c == '7.1':
        channels = '-rematrix_maxval 1.0 -ac 8'
    else:
        channels = ''

    finish = '-threads 8'

    # Finally
    command = ['ffmpeg', '-hide_banner', '-loglevel', 'quiet',
               '-progress', progress, '-hwaccel', 'auto', '-y', '-i', filepath]
    command.extend((codec.split() + preset.split() + frame.split() + tunevideo.split() + aspect.split() + video_opts.split() + Crf.split() +
                   watermark.split() + metadata.split() + subtitles.split() + audio_opts.split() + channels.split() + finish.split()))
    proc = await asyncio.create_subprocess_exec(*command, output_filepath, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    # Progress Bar
    await handle_progress(proc, msg, message, filepath)
    # Wait for the subprocess to finish
    stdout, stderr = await proc.communicate()
    e_response = stderr.decode().strip()
    t_response = stdout.decode().strip()
    LOGGER.info(e_response)
    LOGGER.info(t_response)
    await proc.communicate()
    return output_filepath
