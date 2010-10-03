
Application =
    # Main application singleton, regroups global mechanics

    views: {}
    current_view: 'main'

    show_view: (name) ->
        for view_name, view in @views
            if view_name == name
                view.show()
            else
                view.hide()

        @view(name)

    load: (name, view_params) ->
        @views[name].load(view_params)
        @show_view name

    view: (view_name) ->
        if view_name?
            @current_view = view_name
        else
            @current_view

    component_action: (component_name) ->
        @views[@current_view]?.components_actions[component_name]


class TemplateComponent
    # Abstract class for elements represented by an EJS template

    dom: null

    constructor: (opts) ->
        @dom = render_template opts.template, opts.context
        @ui = $(@dom)


class Audiomodel extends TemplateComponent
    # Represents an audiomodel in the audiomodel list

    constructor: (type, json_model) ->

        @type = type
        $.extend this, json_model

        super
            template: "#{@type}_list_element"
            context: {audiomodel:json_model}

    set_title: (title) ->
        @title = title
        @ui.find(".#{@type}_title").text(@title)

    set_artist: (artist) ->
        if @type == "audiofile"
            @artist = artist
            @ui.find(".#{@type}_artist").text(@artist)

    handle_delete: ->
        audiomodel = @
        msg = "L'élément #{if @artist? then "#{@artist} -"} #{@title} a bien été supprimé"
        delete_menu = make_xps_menu {
            name: "delete_audiomodel_#{@id}"
            text: "Etes vous sur de vouloir supprimer ce#{if @type=="audiofile" then " morceau" else "tte playlist"} ?"
            title: "Suppression d'un#{if @type=="audiofile" then " morceau" else "e playlist"}"
            show_validate:no
            actions:
                "Oui": ->
                    $.getJSON e.target.href, (json) =>
                        post_message msg
                        audiomodel.ui.remove()
                        $(@).dialog('close').remove()
                "Non": ->
                    $(@).dialog('close').remove()

        }
        return (e) ->
            e.preventDefault()
            show_menu delete_menu

    make_audiofile_edit_menu : (data, to_delete_tags) ->
        audiomodel = @
        make_xps_menu {

            name: "edit_audiomodel_#{audiomodel.id}"
            text: data.html
            title: "Edition d'un morceau"

            on_show: ->
                $(@).find('.audiofile_tag_delete').click handle_tag_delete
                $(@).find('#id_tags').autocomplete multicomplete_params(data.tag_list)
                $(@).find('#id_artist').autocomplete source: data.artist_list

            validate_action: ->
                $(@).find('form').ajaxSubmit
                    dataType:'json'
                    data: to_delete_tags
                    success: (json) ->
                        console.log "LOL IM IN TEH SUCCESS"
                        af = json.audiofile
                        audiomodel.set_title af.title
                        audiomodel.set_artist af.artist
                        post_message "Le morceau #{af.artist} - #{af.title} a été modifié avec succès"
        }


    handle_audiofile_edit: ->

        to_delete_tags = {}
        audiomodel = @

        handle_tag_delete = (e) ->
            ###
                Does the necessary action when a tag is marked for deletion :
                1. Hides it, and the category if necessary
                2. Adds an hidden input for when the form is submitted
            ###

            e.preventDefault()
            $audiofile_tag = $(@).parents('.audiofile_tag').first()

            if $audiofile_tag.siblings().length == 0
                $audiofile_tag.parents('tr').first().hide()
            else
                $audiofile_tag.hide()

            tag_id = $audiofile_tag[0].id.split(/_/)[1]
            to_delete_tags["to_delete_tag_#{tag_id}"]= tag_id

            show_menu menu

        return (e) ->
            e.preventDefault()
            $.getJSON @href, (data) ->
                menu = audiomodel.make_audiofile_edit_menu(data, to_delete_tags)
                show_menu menu

    bind_events: ->

        @ui.find('.audiomodel_delete').click @handle_delete()

        if @type == "audiofile"
            @ui.find('.audiofile_edit').click @handle_audiofile_edit()
            @ui.find('.audiofile_play').click handle_audiofile_play

        else if @type == "audiosource"
            @ui.find('.audiosource_edit').click (e) ->
                e.stopPropagation(); e.preventDefault()
                $.get @href, (json) ->
                    console.log json
                    Application.load 'playlist', json


class TagsTable extends TemplateComponent

    constructor: (audiomodel) ->
        super template: 'tags_table', context:{audiomodel:audiomodel}


class AudioFileForm extends TemplateComponent


class PlaylistElement extends TemplateComponent

    constructor: (audiofile, fresh) ->
        @fresh = fresh?
        @audiofile = audiofile
        super template:'playlist_element', context: {fresh:@fresh, audiofile:audiofile}


class Playlist

    length:0
    elements: new Set()

    element_update: (el) ->
        el.ui.find('.source_element_delete').click (e) =>
            e.preventDefault()
            @remove(el)

        el.ui.find('.audiofile_edit').click audiofile_edit_handler
        Playlist.container.find('li').disableTextSelect()
        @update_length()

    update_length: ->
        Playlist.length_container.text format_length(@length)

    append: (audiofile, fresh) ->
        pl_element = new PlaylistElement(audiofile, fresh)
        @elements.add(pl_element)
        @length += audiofile.length
        Playlist.container.append pl_element.dom

    replace: (audiofile, old_element, fresh) ->
        if @elements.has old_element
            new_el = new PlaylistElement(audiofile, fresh)
            @length += audiofile.length - old_element.audiofile.length
            @elements.remove old_element
            @elements.add new_el
            old_element.ui.replaceWith new_el.dom

    remove: (el) ->
        if el.fresh then el.ui.remove()
        else el.ui.addClass 'to_delete_source_element'
        @elements.remove(el)
        @length -= el.audiofile.length
        @update_length()

Playlist.container = $ '#uploaded_audiofiles'
Playlist.length_container = $ '#playlist_length'

Widgets =

    tags:
        view_url: -> "/audiosources/#{Widgets.audiomodels.current_model}/tag/list"
        selected_tags: {}
        clear: -> @selected_tags = {}
        load: ->
            select_handler =  (event, ui) =>
                @selected_tags = (i.value for i in $ '#tag_selector li.ui-selected input')
                Widgets.audiomodels.load()

            $.get @view_url(), (html_data) ->
                $('#tag_selector').html html_data
                $('#tag_selector ul').make_selectable handler:select_handler


    audiomodel_selector:
        container: d$ '#source_type'
        button_class: "audiomodel_selector"
        selected_class: "audiomodel_selected"

        load: ->
            for model_name, button_name of Widgets.audiomodels.models
                dom = tag 'span', button_name, class:@button_class
                @container.append(dom)
                $(dom).button()
                dom.click (e) ->
                    Widgets.audiomodels.current_model = model_name
                    Widgets.tags.clear()
                    Widgets.audiomodels.clear_filter()
                    Widgets.audiomodels.load()
                    Widgets.tags.load()

            @container.make_selectable
                unique_select: yes
                select_class: @selected_class


    audiomodels:
        container: d$ '#track_selector'
        models:
            audiofile: "Tracks"
            audiosource: "Playlists"
        current_model: 'audiofile'

        view_url: -> "/audiosources/#{@current_model}/list/"

        all: []
        by_id: {}

        text_filter: ""
        clear_filter: -> @text_filter = ""

        filter_to_params: ->
            map = {}
            for idx, tag of Widgets.tags.selected_tags
                map["tag_#{idx}"] = tag
            if @text_filter then map["text"] = @text_filter
            return map

        load: ->
            $.getJSON @view_url(), @filter_to_params() , (audiomodels_list) =>

                @all = []
                @by_id = {}

                ul = tag 'ul'
                @container.html ''
                @container.append ul

                for json_audiomodel in audiomodels_list
                    audiomodel = new Audiomodel(@current_model, json_audiomodel)
                    @all.push audiomodel
                    @by_id[audiomodel.id] = audiomodel
                    ul.append audiomodel.ui
                    audiomodel.bind_events()

                $('[id$="select_footer"]').hide()
                $("##{@current_model}_select_footer").show()

                # View specific actions
                @component_action = Application.component_action('audiomodels')
                @component_action?.call()
                delete @component_action


app_view = (map) ->
    @show = -> @container.show()
    @hide = -> @container.hide()
    $.extend this, map
    return this


Application.views.playlist = app_view

    container: $ '#playlist_edit'
    inputs:
        title: $ '#playlist_title'
        tags: $ '#audiosource_tags'
    fields:
        title: $ '#playlist_edit_title'
        audiofiles: Playlist.container
        tags: '#tags_table_container'
        file_forms: $ '#audiofile_forms'
    form: $ '#audiosource_form'

    components_actions:
        audiomodels: ->
            Playlist.container.sortable('refresh')
            if @current_model == "audiofile"
                $('#track_selector ul li').draggable
                    connectToSortable: Playlist.container
                    helper:'clone'
                    appendTo:'body'
                    scroll:no
                    zIndex:'257'

    load: (json) ->
        # Resets playlist
        @playlist = new Playlist()

        # Add a form for audio file upload, and add the upload handler
        @fields.file_forms.html(render_template  'audiofile_form', json)
        $('.audiofileform').each ->
            $(@).ajaxForm(audiofile_form_options $(@), $(@).clone())

        # Reset all fields
        f.html '' for f in @fields
        i.val '' for i in @inputs

        @fields.title.html json.title
        @form[0].action = json.form_url
        @inputs.tags.autocomplete(multicomplete_params json.tag_list).unbind 'blur.autocomplete'

        # Add Necessary information for playlist, if in edition mode
        if json.mode == "edition"
            @inputs.title.val(if json.mode  == "edition" then json.audiosource.title)
            for audiofile in json.audiosource.sorted_audiofiles
                append_to_playlist(audiofile, no)
            @fields.tags.html(new TagsTable(json.audiosource).dom)

populate_form_errors = (errors, form) ->

    for error in errors
        if error != 'status'
            $ul = $("input[name=#{error}]", form).parent().before '<ul> </ul>'
            for msg in error
                $ul.before "<li>#{msg}</li>"

audiofile_edit_handler = (e) ->

    # On click on the edit button on any audiofile
    # handles showing the modal form and setting up appropriate actions for it
    # TODO : Use another class than ui-state-default for $pl_element selection

    handle_tag_delete = (e) ->

        # Does the necessary action when a tag is marked for deletion :
        # 1. Hides it, and the category if necessary
        # 2. Adds an hidden input for when the form is submitted

        e.preventDefault()
        $audiofile_tag = $(@).parents('.audiofile_tag').first()

        if $audiofile_tag.siblings().length == 0
            $audiofile_tag.parents('tr').first().hide()
        else
            $audiofile_tag.hide()

        tag_id = $audiofile_tag[0].id.split(/_/)[1]
        $audiofile_tag.append "<input type=\"hidden\" name=\"to_delete_tag_#{tag_id}\" value=\"#{tag_id}\">"

    e.stopPropagation(); e.preventDefault()
    $pl_element = $(@).parents('.ui-state-default').first()

    $.getJSON @href, (data) ->
        modal_action "Editer un morceau", data.html, (close_func) ->

            on_edit_success = (data) ->
                close_func()
                if $pl_element
                    $('#audiofile_title', $pl_element).text data.audiofile.title
                    $('#audiofile_artist', $pl_element).text data.audiofile.artist
                $('#audiofiles_actions_container').html ''
                if current_audiomodel == "audiofile_select" then update_sources_list()
                post_message "Le morceau #{data.audiofile.artist} - #{data.audiofile.title} a été modifié avec succès"

            $('.audiofile_tag_delete').click handle_tag_delete
            $('#id_tags').autocomplete multicomplete_params(data.tag_list)
            $('#id_artist').autocomplete source: data.artist_list
            $('#audiofile_edit_form').ajaxForm dataType:'json', success:on_edit_success

update_tags_list = ->

    # Update the tags list, by requesting the server
    # Depending on the model type, show the appropriate tags

    $.get audiomodel_route().tags_url, (html_data) ->
        $('#tag_selector').html html_data
        $('#tag_selector ul').make_selectable
            handler: (event, ui) ->
                # Resets the filter_data object, keeping only the text filter
                sel_data = text_filter: sel_data['text_filter']

                # Adds every selected tag
                for input, i in $('#tag_selector ul li.ui-selected input')
                    sel_data["tag_#{i}"] = input.value

                # Updates the source with the new filters
                update_sources_list()

handle_audiofile_play = (e) ->
    # Plays an audiofile on the flash player 

    e.preventDefault(); e.stopPropagation()
    player = document.getElementById 'audiofile_player'
    if player then player.dewset e.target.href

playlist_edit_handler = ->

    # This function is called ONLY ONCE, at document ready, because the playlist edit div is just hidden
    # Does all setting up for playlist editing
    # TODO : Name should be source_edit_handler ;)

    $('.audiofile_edit').click audiofile_edit_handler

    # Sets up sortability of files in the playlist
    $('#uploaded_audiofiles').sortable
        axis: 'y'
        containment: $('.playlist_box')
        connectWith: '#track_selector ul li'
        cursor:"crosshair"
        stop: (e, ui) ->
            # Used when an element is dragged from the audiofile selector
            if ui.item.hasClass 'ui-draggable'
                append_to_playlist audiomodels_by_id[ui.item.children('input').val()], true, ui.item

    # When the edit form is submitted
    $('#audiosource_form', document).submit (e) ->
        e.preventDefault()
        data = {}

        # Adds the playlist tracks to the data to be submitted, if they're not marked for deletion
        for li, i in $('#uploaded_audiofiles li') when not $(li).hasClass "to_delete_source_element"
            data["source_element_#{i}"] = $(li).children('input').val()

        $(@).ajaxSubmit
            data: data
            success: (r) ->
                # On success, hides  the playlist, and show the message and main content

                if current_audiomodel == "audiosource_select" then update_sources_list()
                $('#playlist_edit').hide()
                $('#main_content').show()
                action: if r.action=="edition" then "modifiée" else "ajoutée"

                post_message "La playlist #{r.audiosource.title} à été #{action} avec succès"
                current_mode = "main"

audiofile_form_options = (target_form, new_form) ->

    # Options for dynamic file upload
    # Displays a progress bar for the upload
    # TODO : Use a better form duplication mechanism
    #        First just get rid of this shitty second param
    #        Maybe store the form as an EJS template ?

    # Progress bar update function
    # TODO : Use setInterval instead of setTimeout, and dump the recursive tail call

    update_progress_info = ->
        $.getJSON '/upload-progress/', {'X-Progress-ID': uuid}, (data, status) ->
            if data
                progress = parseInt(data.received) / parseInt(data.size)
                prg_bar.progressbar "option", "value", progress * 100
                setTimeout update_progress_info, UPDATE_FREQ

    UPDATE_FREQ = 1000
    uuid = gen_uuid()
    prg_bar = $ '.progress_bar', target_form

    # Add the unique id to the form action
    target_form[0].action += "?X-Progress-ID=#{uuid}"

    # Option map
    dataType:'json'
    target: target_form
    success: (response, statusText, form) ->
        if response.status
          prg_bar.hide()
          if response.status == "error" then populate_form_errors(response, form)
          else
              post_message "Le morceau #{response.audiofile.artist} - #{response.audiofile.title} a été ajouté avec succès"
              form.hide()
              append_to_playlist response.audiofile, true
        else
          form.html(response)
    beforeSubmit: (arr, $form, options) ->
        # Appends a new form after the first one, for multiuploads
        $newform = $(new_form)
        $form.after($newform)

        # Recursive call to handle the new form upload
        $newform.ajaxForm(audiofile_form_options $newform, $newform.clone())
        prg_bar.progressbar {progress: 0}
        setTimeout update_progress_info UPDATE_FREQ

playlist_view = (json) ->

    # This function is called everytime a playlist is edited OR created
    # It sets the necessary CHANGING data and handlers for the playlist edition
    # For the global settings see playlist_edit_handler

    current_mode = "playlist_edit"
    $pl_div = $('#playlist_edit')

    # Resets playlist length
    total_playlist_length = 0
    # Switch the main divs
    $pl_div.show()
    $('#main_content').hide()

    # Add a form for audio file upload, and add the upload handler
    $('#audiofile_forms').html(render_template  'audiofile_form', json)
    $('.audiofileform').each ->
        $(@).ajaxForm(audiofile_form_options $(@), $(@).clone())

    # Reset all fields
    $('#uploaded_audiofiles').html ''
    $('#playlist_title').val('')
    $('#tags_table_container', $pl_div).html ''
    $('#audiosource_tags').val('')

    $('#playlist_edit_title', $pl_div).html json.title
    $('#audiosource_form')[0].action = json.form_url
    $('#audiosource_tags').autocomplete(multicomplete_params json.tag_list).unbind 'blur.autocomplete'

    # Add Necessary information for playlist, if in edition mode
    if json.mode == "edition"
        $('#playlist_title').val(if json.mode  == "edition" then json.audiosource.title)
        for audiofile in json.audiosource.sorted_audiofiles
            append_to_playlist(audiofile, no)
        $('#tags_table_container').html(render_template 'tags_table', audiomodel:json.audiosource)



# ========================================= PLANNINGS PART ======================================== #

show_edit_planning = () ->
    board = $('#main_planning_board')
    ct = $('#main_planning_board_container')

    for _ in [0...24]
        for i in [1..6]
            div_class = {3:'half',6:'hour'}[i] or 'tenth'
            board.append(div class:"grid_time grid_#{div_class}")

    $('#main_content').hide()
    $('#planning_edit').show()
    ct.height $(document).height() - ct.offset().top - 20

    $('#main_planning_board').droppable
        over: (e, ui) ->
            dropped_el = ui.helper

        drop: (e, ui) ->
        tolerance:'fit'

    current_mode = "planning_edit"

pos_on_pboard = (el_pos) ->

    # Takes a coordinates object as input -> {left:int, top:int}
    # Returns a coordinate object relative to the planning board

    pboard_off = $('#planning_board').offset()
    el_pos.top -= pboard_off.top
    el_pos.left -= pboard_off.left
    return el_pos

el_pos_on_pboard = (el, pos) ->

    # If only el is given, returns the position of el on the planning board
    # If pos is given as pos = {top:int, left:int},
    # then place el at the given pos relative to the board

    pboard_off = $('#planning_board').offset()
    el_off = el.offset()
    if pos
        el.css
            top: pboard_off.top + pos.top
            left: pboard_off.left + pos.left
    else
        el_off.top -= pboard_off.top
        el_off.left -= pboard_off.left
        return el_off

closest = (num, steps) ->

    # num: int, steps: [int]
    # Returns the step that is the closest to num

    ret = null
    $.each steps, (i) ->
        if steps[i] < num < steps[i +1]
            if num - steps[i] < steps[i + 1] - num
                ret = steps[i]
            else
                ret = steps[i + 1]
    return ret

step = (num, step) -> num - (num % step)

# ========================================= DOCUMENT READY PART ======================================== #

$ ->
    # Handler for adding selected sources to the playlist 
    # TODO : This sucks 
    add_tracks_to_playlist = ->
        for el, i in $('#track_selector li') when $(el).hasClass 'ui-selected'
            append_to_playlist audiomodels[i], true

    # Configure the playlist handling once and for all
    playlist_edit_handler()

    for cname, component of Widgets
        console.log "Loading component #{cname}"
        component.load()

    # Configure all sources filters, except for the Tag filter which is handled in update_tags_list
    # Text selector filter
    $('#text_selector').keyup (e) -> sel_data['text_filter'] = $(@).val(); update_sources_list()

    # Global click event handlers

    $('#create_playlist_button').click (e) -> $.get '/audiosources/json/create-audio-source', playlist_view
    $('#uploaded_audiofiles .audiofile_play').live 'click', handle_audiofile_play
    $('#add_to_playlist_button').click add_tracks_to_playlist

    show_edit_planning()
