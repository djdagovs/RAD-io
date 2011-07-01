"""
This module contains every view that is related to
the handling of audio content on the radio. A lot
of theses views are simple json wrappers for the
radio admin interface to communicate with the database.
Some of theses views **should** be simple wrappers
but aren't.
"""
import json
from datetime import date
import locale
from calendar import day_name

from django.contrib.admin.views.decorators import staff_member_required
from django.views.generic.simple import direct_to_template
from django.views.generic.list_detail import object_list, object_detail
from django.http import HttpResponse
from django.core.urlresolvers import reverse
from django.template import Context, loader
from django.shortcuts import get_object_or_404
from django.http import Http404

from rzz.artists.models import Artist

from rzz.audiosources.models import AudioFile, AudioSource, Planning, Tag, tag_list, PlanningStartEvent
from rzz.audiosources.forms import EditAudioFileForm
from rzz.audiosources.utils import add_tags_to_model, add_audiofiles_to_audiosource, remove_tags_from_model

from rzz.utils.jsonutils import JSONResponse
from rzz.utils.queries import Q_or
from rzz.utils.file import get_mp3_metadata
from rzz.utils.collections import dict_transform


def listen(request):
    """
    Simple view, not really necessary (could use direct linking in the url file)
    """
    # TODO: Use direct_to_template in the url file
    return direct_to_template(request, "listen.html")

@staff_member_required
def main(request):
    """
    This view is the backbone of the radio admin interface
    """
    return direct_to_template(request, 'audiosources/main.html')


@staff_member_required
def set_planning_active(_, planning_id):
    """
    Set the corresponding planning as active
    """
    planning = get_object_or_404(Planning, id=planning_id)
    planning.set_active()
    return HttpResponse()


@staff_member_required
def create_planning(request):
    """
    View for dynamic creation of a planning
    """
    planning_data = json.loads(request.POST['planning_data'])
    planning = Planning(name=planning_data['title'])
    planning.save()
    planning.add_elements(planning_data['planning_elements'])
    add_tags_to_model(planning_data['tags'], planning)

    return HttpResponse()


@staff_member_required
def edit_planning(request, planning_id):
    """
    View for edition of a planning
    """
    planning = Planning.objects.get(id=planning_id)

    if request.method == 'POST':
        planning_data = json.loads(request.POST['planning_data'])
        print planning_data
        planning.planningelement_set.all().delete()
        planning.add_elements(planning_data['planning_elements'])
        planning.name = planning_data["title"]
        remove_tags_from_model(planning, planning_data["to_delete_tags"])
        add_tags_to_model(planning_data['tags'], planning)
        planning.save()
        return HttpResponse()
    else:
        planning_dict = planning.to_dict(with_tags=True)
        pe_dicts = [pe.to_dict() for pe in planning.planningelement_set.all()]
        planning_dict["planning_elements"] = pe_dicts
        return JSONResponse(planning_dict)


@staff_member_required
def create_audio_source(request):
    """
    View for dynamic creation of an audio source
    """
    if request.method == 'POST':
        audio_source = AudioSource(title=request.POST['title'], length=0)
        audio_source.save()

        add_tags_to_model(request.POST['tags'], audio_source)

        playlist_tuples = [(int(key.split('_')[-1]), int(val))
                           for key, val in request.POST.items()
                           if key.startswith('source_element_')]

        add_audiofiles_to_audiosource(playlist_tuples, audio_source)
        return JSONResponse({
            'status':'success',
            'action':'creation',
            'audiosource':audio_source.to_dict()
        })

    return JSONResponse({
        'action': 'creation',
        'tag_list': tag_list(),
        'title': 'Creation d''une nouvelle playlist',
        'form_url': reverse('create-audio-source')
    })


@staff_member_required
def edit_audio_source(request, audiosource_id):
    """
    JSON View for edition of an audio source (playlist)
    This view deletes every source element of the audio source
    every time it is edited
    """
    # TODO: Send 
    audio_source = get_object_or_404(AudioSource, id=audiosource_id)
    if request.method == 'POST':
        print request.POST
        audio_source.title = request.POST['title']
        audio_source.description = request.POST['description']
        share = request.POST['share']
        audio_source.share = True if share == "yes" else False
        audio_source.sourceelement_set.all().delete()
        audio_source.length = 0
        add_tags_to_model(request.POST['tags'], audio_source)
        # Save to be able to add audiofiles to source
        audio_source.save()

        playlist_tuples = [(int(key.split('_')[-1]), int(val))
                           for key, val in request.POST.items()
                           if key.startswith('source_element_')]

        to_delete_tags = [val for key, val in request.POST.items()
                          if key.startswith('to_delete_tag')]

        remove_tags_from_model(audio_source, to_delete_tags)
        add_audiofiles_to_audiosource(playlist_tuples, audio_source)
        return JSONResponse({
            'status':'success',
            'action':'edition',
            'audiosource':audio_source.to_dict()
        })

    return JSONResponse({
        'action':'edition',
        'tag_list':tag_list(),
        'title': "Edition de la playlist %s" % audio_source.title,
        'audiosource':audio_source.to_dict(with_audiofiles=True,
                                           with_tags=True),
        'form_url': reverse('edit-audio-source', args=[audiosource_id])
    })


@staff_member_required
def create_audio_file(request):
    """
    AJAX
    POST View for creation of audio files
    Returns a json representation of the audiofile
    """
    #TODO: Add error handling
    if request.method == 'POST':
        files = request.FILES.getlist('file')
        af_list = []

        for afile in files:
            instance = AudioFile()
            path = afile.temporary_file_path()
            instance.artist, instance.title, instance.length = get_mp3_metadata(path)
            instance.original_filename = afile.name
            instance.file = afile
            instance.save()
            af_list.append(instance.to_dict())

        return JSONResponse({
            'audiofiles':af_list,
            'status':'ok'
            }, mimetype=False)


def audio_models_list(request, audiomodel_klass, page):
    """
    AJAX
    Displays a list of audio files depending on filter clauses
    """
    nb_items = 50
    bottom = nb_items * page
    top = bottom + nb_items
    text_filter = request.GET.get('text_filter', None)
    tags = Tag.objects.filter(
        id__in=[int(el) for key, el in request.GET.items() if "tag_" in key]
    )

    if text_filter:
        search_clauses = ['title']
        if audiomodel_klass == AudioFile:
            search_clauses += ['artist']
        search_dict = dict(
            [(sc + '__icontains', text_filter) for sc in search_clauses]
        )
        audiomodels = audiomodel_klass.objects.filter(Q_or(**search_dict))
    else:
        audiomodels = audiomodel_klass.objects.all()

    if tags:
        for tag in tags:
            audiomodels = audiomodels.filter(tags=tag)

    cnt = audiomodels.count()

    if bottom > cnt:
        raise Http404

    audiomodels = audiomodels[bottom:top if top <= cnt else cnt]

    return JSONResponse([af.to_dict() for af in audiomodels])


def edit_audio_files(request):
    """
    Edit several audio files at once
    """

    audiofiles_ids_list = request.POST.getlist("audiofiles")
    audiofiles = AudioFile.objects.filter(id__in=audiofiles_ids_list)
    tags_updated = artist_updated = False

    if request.POST["tags"]:
        tags_updated = True
        for audiofile in audiofiles:
            add_tags_to_model(request.POST["tags"], audiofile)

    if request.POST["artist"]:
        artist_updated = True
        audiofiles.update(artist=request.POST["artist"])

    return JSONResponse({
        'tags_updated':tags_updated,
        'artist_updated':artist_updated
    })


def edit_audio_file(request, audiofile_id):
    """
    AJAX
    Returns a form to edit audiofile
    """
    # TODO : Use js templating instead of django templating
    audiofile = get_object_or_404(AudioFile, pk=audiofile_id)
    form = EditAudioFileForm(initial= {'title':audiofile.title,
                                       'artist':audiofile.artist})
    if request.method =='POST':
        to_delete_tags = [val for key, val in request.POST.items()
                          if key.startswith('to_delete_tag')]

        remaining_dict = dict([(k, v) for k, v in request.POST.items()
                               if not key.startswith('to_delete_tag')])

        form = EditAudioFileForm(remaining_dict)

        if form.is_valid():
            artist = form.cleaned_data['artist']
            title = form.cleaned_data['title']

            if artist != audiofile.artist or title != audiofile.title:
                audiofile.title = title
                audiofile.artist = artist
                audiofile.save_and_update_file()

            add_tags_to_model(form.cleaned_data['tags'], audiofile)

            audiofile.save()
            remove_tags_from_model(audiofile, to_delete_tags)
            return JSONResponse({
                'audiofile':audiofile.to_dict(),
                'status':'ok'
            })
        else:
            return JSONResponse(dict(form.errors.items()
                                     + [('status','errors')]))

    template = loader.get_template('audiosources/audiofile_edit_form.html')
    ctx = Context({'form':form, 'audiofile':audiofile})
    return JSONResponse({
        'html':template.render(ctx),
        'tag_list':tag_list(),
        'audiofile': audiofile.to_dict(with_tags=True),
        'artist_list':[a.name for a in Artist.objects.all()]
    })


def tags_list(request, audiomodel_klass):
    tags = Tag.objects.extra(where=[
        """
        id IN (SELECT tag_id
               FROM audiosources_taggedmodel_tags
               WHERE taggedmodel_id IN (SELECT %s_ptr_id
                                        FROM audiosources_%s))
        """ % (
            "taggedmodel" if audiomodel_klass == Planning else "audiomodel", {
                AudioFile:'audiofile',
                AudioSource:'audiosource',
                Planning:"planning"
            }[audiomodel_klass]
        )
    ])
    categories = {}
    for tag in tags:
        try:
            categories[tag.category.name].append(tag)
        except KeyError:
            categories[tag.category.name] = [tag]

    return direct_to_template(request,
                              'audiosources/tags_list.html',
                              extra_context={'categories':categories})


def show_active_planning(request):

    locale.setlocale(locale.LC_ALL, '')
    planning = Planning.objects.active_planning()
    p_elements = list(planning.planningelement_set.all())
    elements = [
        (
            day_name[i],
            sorted([p for p in p_elements if p.day == i and p.type == 'single'],
                   key=lambda p: p.time_start)
        )
         for i in range(7)
    ]

    return direct_to_template(request,
                              'audiosources/show_active_planning.html',
                              extra_context={
                                  'days':elements,
                                  'today':day_name[date.today().weekday()]
                              })

def duplicate_planning(request):
    planning = Planning.objects.get(id=request.GET["planning_id"])
    new_planning = Planning(name=request.GET["name"], active = False)
    new_planning.save()
    for planning_element in planning.planningelement_set.all():
        # Set id to none to create a new element
        planning_element.id = None
        planning_element.planning = new_planning
        planning_element.save()

    return HttpResponse()

def edit_calendar(request):

    if request.method == "POST":
        transform_map = {
            "start": ("when", lambda x:date(*x)),
            "planning_id": None
        }
        raw_events = json.loads(request.POST["events"])
        events = [dict_transform(e, transform_map) for e in raw_events]
        PlanningStartEvent.objects.all().delete()
        for event in events:
            PlanningStartEvent(**event).save()
        return HttpResponse()


    events = PlanningStartEvent.objects.values(
        "when", "planning__id", "planning__name"
    )
    for event in events:
        w = event["when"]
        event["when"] = {"day":w.day,"month":w.month,"year":w.year}

    return JSONResponse(list(events))

def shared_contents_list(request, page):
    return object_list(request,
        queryset = AudioSource.objects.filter(share=True),
        paginate_by = 20,
        page = page,
        template_name="audiosources/shared_contents_list.html",
        template_object_name="shared_contents"
    )

def shared_content_detail(request, audiosource_id):
    return object_detail(request,
        queryset = AudioSource.objects.all(),
        object_id = audiosource_id,
        template_name = "audiosources/shared_content_detail.html",
        template_object_name = "shared_content"
    )

def audiosource_playlist(request, audiosource_id):
    a = AudioSource.objects.get(id=audiosource_id)
    elements = a.sourceelement_set.order_by("position")
    return direct_to_template(
        request,
        'audiosources/playlist.xml',
        extra_context={
            "audiosource": a,
            "source_elements": elements}
    )

def get_playing_element(request):
    playing_element = Planning.objects.active_planning().get_playing_element()
    return JSONResponse({"playing_element": playing_element.to_dict() if playing_element else None})
