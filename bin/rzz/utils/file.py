import shutil
from os import path, makedirs

from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3

from django.conf import settings

def move_field_file(field_file, new_path):
    split = new_path.split('/')
    name = split[-1]
    dir = '/'.join(split[:-1])
    abs_dir = path.join(settings.MEDIA_ROOT, dir)
    if not path.exists(abs_dir):
        makedirs(abs_dir)
    shutil.move(field_file.path, path.join(settings.MEDIA_ROOT, new_path))
    field_file.name = new_path

def set_mp3_metadata(mp3_path, artist='unknown_artist', title='unknown_title'):
    mp3 = MP3(mp3_path, ID3=EasyID3)
    mp3['title'] = title
    mp3['artist'] = artist
    mp3.save()

def get_mp3_metadata(mp3_path):
    mp3 = MP3(mp3_path, ID3=EasyID3)
    title = u' '.join(mp3['title']) if 'title' in mp3 else u'unknown_title'
    artist = u' '.join(mp3['artist']) if 'artist' in mp3 else u'unknown_artist'
    return artist, title, mp3.info.length

def first_available_filename(filename):

    if path.isfile(path.join(settings.MEDIA_ROOT, filename)):
        file_ext = filename.split(".")[-1]
        base_filename = ".".join(filename.split(".")[:-1])
        i = 1
        while path.isfile(path.join(settings.MEDIA_ROOT, filename)):
            filename = "{0}_{1}.{2}".format(base_filename, i, file_ext)
            i = i + 1

    return filename


