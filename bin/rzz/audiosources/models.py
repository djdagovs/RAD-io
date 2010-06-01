from os import path

from django.db import models
from django.core.urlresolvers import reverse

from rzz.utils.str import sanitize_filename, sanitize_filestring
from rzz.utils.file import move_field_file, set_mp3_metadata
from rzz.artists.models import Artist

def audio_file_name(instance, filename):
	ext = filename.split('.')[-1]
	if instance.title or instance.artist:
		artist = sanitize_filestring(instance.artist if instance.artist else 'unknown_artist')
		title = sanitize_filestring(instance.title if instance.title else 'unknown_title')
		return 'audiofiles/{0}-{1}.{2}'.format(artist, title,ext)
	else:
		return 'audiofiles/{0}'.format(sanitize_filename(filename))

class TagCategory(models.Model):
    name = models.CharField('Categorie', max_length=50, unique=True)

    def __unicode__(self):
        return self.name
    

class Tag(models.Model):
    category = models.ForeignKey(TagCategory)
    name = models.CharField('Tag', max_length=50)

    def __unicode__(self):
        return self.name
    class Meta:
        unique_together = ("category", "name")

class AudioModel(models.Model):
    length = models.IntegerField()
    tags = models.ManyToManyField(Tag)

    def formatted_length(self):
        hours = self.length / 3600
        minutes = (self.length % 3600) / 60
        seconds = (self.length % 60)
        output = '{0}:{1}'.format(minutes, seconds)
        output = '{0}:'.format(hours) + (output if hours else '')
        return output

    class Meta:
        abstract = True

class AudioFile(AudioModel):
    title = models.CharField('Audiofile title', max_length=400)
    artist = models.CharField('Audiofile artist', max_length=200)
    rzz_artist = models.ForeignKey(Artist, null=True)
    file = models.FileField(upload_to=audio_file_name)
    
    def __unicode__(self):
        return self.artist + u' - ' + self.title 
    def form_url(self):
        return reverse('audio-file-edit',args=[self.id])
    def update_file(self):
        print 'INTO UPDATE FILE'
        set_mp3_metadata(self.file.path, self.artist, self.title)
        move_field_file(self.file, 
                          audio_file_name(self, 
                                          path.split(self.file.name)[1]))


class AudioSource(AudioModel):
    title = models.CharField('AudioSource title', max_length=400)
    rzz_artist = models.ForeignKey(Artist, null=True)
    audio_files = models.ManyToManyField(AudioFile, through='SourceElement')
    
    def __unicode__(self):
        return self.title 

class SourceElement(models.Model):
	position = models.IntegerField()
	audiofile = models.ForeignKey(AudioFile)
	audiosource = models.ForeignKey(AudioSource)
