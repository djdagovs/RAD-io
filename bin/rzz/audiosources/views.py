import logging as log
import json

from django.contrib.admin.views.decorators import staff_member_required
from django.views.generic.simple import direct_to_template
from django.http import HttpResponse
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404

from rzz.audiosources.models import AudioFile, AudioSource, SourceElement,Tag, TagCategory
from rzz.audiosources.forms import AudioFileForm, EditAudioFileForm
from rzz.utils.models import instance_to_json
from rzz.utils.views import generic_form
from rzz.audiosources.utils import process_tags

@staff_member_required
def create_audio_source(request):
    """
    View for dynamic creation of an audio source
    """
    if request.method == 'POST':
        audio_source = AudioSource(title=request.POST['title'], length=0)
        for key, val in request.POST.items():
            try:
                pos = int(key)
                id = int(val)
                audiofile = AudioFile.objects.get(pk=int(val))
                source_element = SourceElement(position=pos,
                                               audiosource=audio_source,
                                               audiofile=audiofile)
                source_element.save()
                audio_source.length += audiofile.length 
            except ValueError:
                pass
        audio_source.save()
    return direct_to_template(request, 
                              'audiosources/create_audiosource.html', 
                              extra_context={'form':AudioFileForm()})

@staff_member_required
def create_audio_file(request):
    """
    AJAX
    View for creation of audio files 
    Returns a simple form to be integrated by ajax on GET
    on POST, returns a json representation of the audiofile
    """
    # TODO: Do two/three views : 
    # 1. Music control center view
    # 2. Form view
    # 3. Ajax response ?
    if request.method == 'POST':
        form = AudioFileForm(request.POST, request.FILES)
        if form.is_valid():
            audiofile = form.save()
            return HttpResponse(instance_to_json(audiofile, 
                                                 status='ok',
                                                 form_url=audiofile.form_url()))
        else:
            return HttpResponse(json.dumps(dict(form.errors.items() 
                                                + [('status', 'error')])))
    return direct_to_template(request,
                              'audiosources/audiofile_form.html',
                              extra_context={'form':AudioFileForm()})

def audio_files_list(request):
    """
    AJAX
    Displays a list of audio files depending on filter clauses
    """
    num_page = request.GET['p']
    nb_items = 50
    bottom = nb_items * num_page
    top = bottom + nb_items
    if opts:
        audiofiles = AudioFile.objects.filter(**opts)[bottom:top]
    else:
        audiofiles = AudioFile.objects.all()[bottom:top]
    return direct_to_template(request,
                              'audiosources/audiofile_list.html',
                              extra_context={'audiofiles': audiofiles})

def edit_audio_file(request, audiofile_id):
    """
    AJAX
    Returns a form to edit audiofile
    """
    audio_file = get_object_or_404(AudioFile, pk=audiofile_id)
    form = EditAudioFileForm(initial= {'title':audio_file.title,
                                       'artist':audio_file.artist})
    if request.method =='POST':
        form = EditAudioFileForm(request.POST)
        if form.is_valid():
            audio_file.title = form.cleaned_data['title']
            audio_file.artist = form.cleaned_data['artist']
            for category, tags in process_tags(form.cleaned_data['tags']).items():
                print "{0}, {1}".format(category, tags)
                c = TagCategory(name=category)
                c.save()
                for tag in tags:
                    print "Tag :" + tag
                    t = Tag(category=c,name=tag).save()
                    audio_file.tags.add(t)
            audio_file.save()
            return HttpResponse(instance_to_json(audio_file,
                                                 status='ok'))
        else:
            return HttpResponse(json.dumps(dict(form.errors.items() 
                                                + [('status','errors')])))
    return generic_form(request, form, 
                        reverse(edit_audio_file, args=[audiofile_id]))
