import gi
import os
import time
import random
from gi.repository import Gtk, Gdk, GdkPixbuf, GObject
from urllib.parse import quote
import eyed3

gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')
gi.require_version('GdkPixbuf', '2.0')

import gi.repository.GdkPixbuf as GdkPixbuf
import gi.repository.Gst as Gst
import gi.repository.Gtk as Gtk

class MusicPlayer:
    def __init__(self):
        Gst.init(None)

        self.window = Gtk.Window()
        self.window.connect("destroy", Gtk.main_quit)
        self.window.set_default_size(800, 600)
        self.window.set_title("Music Player")

        self.playlist_store = Gtk.ListStore(str, str, str, str, str)
        self.original_playlist = []  # Store the original playlist data for filtering

        self.playlist_view = Gtk.TreeView(self.playlist_store)
        self.playlist_view.set_rules_hint(True)
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Playlist", renderer, text=0)
        self.playlist_view.append_column(column)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Artist", renderer, text=1)
        self.playlist_view.append_column(column)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Genre", renderer, text=2)
        self.playlist_view.append_column(column)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Album", renderer, text=3)
        self.playlist_view.append_column(column)

        column.set_sort_column_id(0)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.add(self.playlist_view)

        self.play_button = Gtk.Button("Play")
        self.play_button.connect("clicked", self.play)
        self.pause_button = Gtk.Button("Pause")
        self.pause_button.connect("clicked", self.toggle_pause)
        self.stop_button = Gtk.Button("Stop")
        self.stop_button.connect("clicked", self.stop)

        self.load_from_dir_button = Gtk.Button("Load Dir")
        self.load_from_dir_button.connect("clicked", self.load_from_dir)
        self.append_from_file_button = Gtk.Button("Append File")
        self.append_from_file_button.connect("clicked", self.append_from_file)
        self.clear_playlist_button = Gtk.Button("Clear Playlist")
        self.clear_playlist_button.connect("clicked", self.clear_playlist)
        self.shuffle_playlist_button = Gtk.Button("Shuffle Playlist")
        self.shuffle_playlist_button.connect("clicked", self.shuffle_playlist)
        self.save_playlist_button = Gtk.Button("Save Playlist")
        self.save_playlist_button.connect("clicked", self.save_playlist)
        self.load_playlist_button = Gtk.Button("Load Playlist")
        self.load_playlist_button.connect("clicked", self.load_playlist)
        self.repeat_all_button = Gtk.ToggleButton("Repeat Playlist")
        self.repeat_all_button.connect("toggled", self.toggle_repeat_playlist)
        self.repeat_one_button = Gtk.ToggleButton("Repeat Current")
        self.repeat_one_button.connect("toggled", self.toggle_repeat_current)
        self.mute_button = Gtk.ToggleButton("Mute")
        self.mute_button.connect("toggled", self.toggle_mute)
        self.search_button = Gtk.Button("Search")
        self.search_button.connect("clicked", self.search)
        self.search_entry = Gtk.Entry()
        self.search_entry.set_placeholder_text("Enter search criteria...")
        self.search_entry.connect("activate", self.search)


        hbox_buttons = Gtk.HBox(False, 0)
        hbox_buttons.pack_start(self.play_button, True, True, 2)
        hbox_buttons.pack_start(self.pause_button, True, True, 2)
        hbox_buttons.pack_start(self.stop_button, True, True, 2)
        hbox_buttons.pack_start(self.load_from_dir_button, True, True, 2)
        hbox_buttons.pack_start(self.append_from_file_button, True, True, 2)
        hbox_buttons.pack_start(self.clear_playlist_button, True, True, 2)
        hbox_buttons.pack_start(self.shuffle_playlist_button, True, True, 2)
        hbox_buttons.pack_start(self.save_playlist_button, True, True, 2)
        hbox_buttons.pack_start(self.load_playlist_button, True, True, 2)
        hbox_buttons.pack_start(self.repeat_all_button, True, True, 2)
        hbox_buttons.pack_start(self.repeat_one_button, True, True, 2)
        hbox_buttons.pack_start(self.mute_button, True, True, 2)
        hbox_search = Gtk.HBox(False, 0)
        hbox_search.pack_start(self.search_button, False, False, 2)
        hbox_search.pack_start(self.search_entry, True, True, 2)


        self.time_label = Gtk.Label("00:00:00 / 00:00:00")
        self.time_label.set_name("time-label")
        self.time_label.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0, 0, 0, 1))
        self.time_label.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
        hbox_buttons.pack_start(self.time_label, False, False, 2)

        self.now_playing_label = Gtk.Label()
        self.now_playing_label.set_name("now-playing-label")
        self.now_playing_label.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0, 0, 0, 1))
        self.now_playing_label.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
        self.now_playing_label.set_markup('<span background="black" foreground="white" font_desc="12">Now Playing:</span>')

        vbox = Gtk.VBox(False, 0)
        vbox.pack_start(self.now_playing_label, False, False, 2)
        vbox.pack_start(scrolled_window, True, True, 2)
        vbox.pack_start(hbox_buttons, False, False, 2)
        vbox.pack_start(hbox_search, False, False, 2) 

        # Add volume slider
        self.gain_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.gain_scale.set_digits(0)
        self.gain_scale.set_value_pos(Gtk.PositionType.BOTTOM)
        self.gain_scale.add_mark(0, Gtk.PositionType.BOTTOM, "0%")
        self.gain_scale.add_mark(50, Gtk.PositionType.BOTTOM, "50%")
        self.gain_scale.add_mark(100, Gtk.PositionType.BOTTOM, "100%")
        self.gain_scale.connect("value-changed", self.on_gain_scale_change)
        vbox.pack_start(self.gain_scale, False, False, 2)

        # Add position slider
        self.position_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 5)
        self.position_scale.set_digits(0)
        self.position_scale.set_value_pos(Gtk.PositionType.BOTTOM)
        self.position_scale.add_mark(10, Gtk.PositionType.BOTTOM, "10%")
        self.position_scale.add_mark(20, Gtk.PositionType.BOTTOM, "20%")
        self.position_scale.add_mark(30, Gtk.PositionType.BOTTOM, "30%")
        self.position_scale.add_mark(40, Gtk.PositionType.BOTTOM, "40%")
        self.position_scale.add_mark(50, Gtk.PositionType.BOTTOM, "50%")
        self.position_scale.add_mark(60, Gtk.PositionType.BOTTOM, "60%")
        self.position_scale.add_mark(70, Gtk.PositionType.BOTTOM, "70%")
        self.position_scale.add_mark(80, Gtk.PositionType.BOTTOM, "80%")
        self.position_scale.add_mark(90, Gtk.PositionType.BOTTOM, "90%")
        self.position_scale.add_mark(100, Gtk.PositionType.BOTTOM, "100%")
        self.position_scale.connect("value-changed", self.on_position_scale_change)
        vbox.pack_start(self.position_scale, False, False, 2)

        # Set the initial position of the slider to 0
        self.position_scale.set_value(0)

        self.window.add(vbox)
        self.window.show_all()

        self.pipeline = Gst.ElementFactory.make("playbin", "player")
        self.pipeline.set_property("volume", 0.25)  # Set default volume to 25%
        self.playback_paused = False
        self.repeat_playlist = False
        self.repeat_one_enabled = False  # Initialize "Repeat Current" to False
        self.muted = False
        self.muted_volume = 0.25  # Set initial muted volume to 25%

        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_message)
        # Update the "Now Playing" label in real-time
        self.update_now_playing_label()
        self.update_time_timer = GObject.timeout_add(1000, self.update_time_label)
        self.original_playlist = []  # Store the original playlist data

    def create_search_dialog(self):
        dialog = Gtk.Dialog("Search Playlist", self.window, 0, (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK))
        dialog.set_default_response(Gtk.ResponseType.OK)

        # Add input fields for search criteria
        grid = Gtk.Grid()
        grid.set_column_spacing(10)
        grid.set_row_spacing(10)

        artist_label = Gtk.Label("Artist:")
        self.artist_entry = Gtk.Entry()
        title_label = Gtk.Label("Title:")
        self.title_entry = Gtk.Entry()
        genre_label = Gtk.Label("Genre:")
        self.genre_entry = Gtk.Entry()
        album_label = Gtk.Label("Album:")
        self.album_entry = Gtk.Entry()
        file_name_label = Gtk.Label("File Name:")
        self.file_name_entry = Gtk.Entry()

        grid.attach(artist_label, 0, 0, 1, 1)
        grid.attach(self.artist_entry, 1, 0, 1, 1)
        grid.attach(title_label, 0, 1, 1, 1)
        grid.attach(self.title_entry, 1, 1, 1, 1)
        grid.attach(genre_label, 0, 2, 1, 1)
        grid.attach(self.genre_entry, 1, 2, 1, 1)
        grid.attach(album_label, 0, 3, 1, 1)
        grid.attach(self.album_entry, 1, 3, 1, 1)
        grid.attach(file_name_label, 0, 4, 1, 1)
        grid.attach(self.file_name_entry, 1, 4, 1, 1)

        dialog.get_content_area().add(grid)
        dialog.show_all()

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.filter_playlist()
        dialog.destroy()

    def filter_playlist(self):
        artist = self.artist_entry.get_text()
        title = self.title_entry.get_text()
        genre = self.genre_entry.get_text()
        album = self.album_entry.get_text()
        file_name = self.file_name_entry.get_text()

        # Clear the current playlist
        self.playlist_store.clear()

        # Iterate through the original playlist and add matching items
        for song_path, song_artist, song_genre, song_album, song_title in self.original_playlist:
            if (
                (artist.lower() in song_artist.lower()) and
                (title.lower() in song_title.lower()) and
                (genre.lower() in song_genre.lower()) and
                (album.lower() in song_album.lower()) and
                (file_name.lower() in os.path.basename(song_path).lower())
            ):
                self.playlist_store.append([song_path, song_artist, song_genre, song_album, song_title])

    def play(self, widget):
        selection = self.playlist_view.get_selection()
        model, selected_song_iter = selection.get_selected()

        if selected_song_iter:
            song_path = model.get_value(selected_song_iter, 0)
            self.play_audio_file(song_path)

    def play_audio_file(self, file_path):
        try:
            encoded_file_path = quote(file_path)
            self.pipeline.set_state(Gst.State.NULL)
            self.pipeline.set_property("uri", f"file://{encoded_file_path}")
            self.pipeline.set_state(Gst.State.PLAYING)
            self.playback_paused = False
        except Exception as e:
            print(f"Error while playing audio: {e}")

    def toggle_pause(self, widget):
        if self.playback_paused:
            self.pipeline.set_state(Gst.State.PLAYING)
            self.playback_paused = False
        else:
            self.pipeline.set_state(Gst.State.PAUSED)
            self.playback_paused = True

    def stop(self, widget):
        self.pipeline.set_state(Gst.State.NULL)

    def on_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.ERROR:
            self.pipeline.set_state(Gst.State.NULL)
            err, debug = message.parse_error()
            print("Error: %s" % err, debug)
        elif t == Gst.MessageType.EOS:
            if self.repeat_one_enabled:
                # Repeat the current song by seeking to the start
                self.pipeline.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH, 0)
                self.pipeline.set_state(Gst.State.PLAYING)
            elif self.repeat_playlist:
                selection = self.playlist_view.get_selection()
                model, selected_song_iter = selection.get_selected()
                if selected_song_iter:
                    next_song_iter = model.iter_next(selected_song_iter)
                    if not next_song_iter:
                        next_song_iter = model.get_iter_first()
                    if next_song_iter:
                        next_song_path = model.get_value(next_song_iter, 0)
                        self.play_audio_file(next_song_path)
            else:
                self.pipeline.set_state(Gst.State.NULL)
                print("End-Of-Stream reached")

        # Handle track change event
        elif t == Gst.MessageType.ELEMENT:
            if message.get_structure().get_name() == "GstElementMessageEos":
                # Track has finished, update the label with the next track if available
                selection = self.playlist_view.get_selection()
                model, selected_song_iter = selection.get_selected()
                if selected_song_iter:
                    next_song_iter = model.iter_next(selected_song_iter)
                    if next_song_iter:
                        artist = model.get_value(next_song_iter, 1)
                        title = model.get_value(next_song_iter, 4)
                        album = model.get_value(next_song_iter, 3)
                        now_playing_text = f"Now Playing: {artist} - {title} from {album}"
                        self.now_playing_label.set_text(now_playing_text)

    def create_search_dialog(self):
        dialog = Gtk.Dialog("Search Playlist", self.window, 0, (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK))
        dialog.set_default_response(Gtk.ResponseType.OK)

        # Add input fields for search criteria
        grid = Gtk.Grid()
        grid.set_column_spacing(10)
        grid.set_row_spacing(10)

        artist_label = Gtk.Label("Artist:")
        self.artist_entry = Gtk.Entry()
        title_label = Gtk.Label("Title:")
        self.title_entry = Gtk.Entry()
        genre_label = Gtk.Label("Genre:")
        self.genre_entry = Gtk.Entry()
        album_label = Gtk.Label("Album:")
        self.album_entry = Gtk.Entry()
        file_name_label = Gtk.Label("File Name:")
        self.file_name_entry = Gtk.Entry()

        grid.attach(artist_label, 0, 0, 1, 1)
        grid.attach(self.artist_entry, 1, 0, 1, 1)
        grid.attach(title_label, 0, 1, 1, 1)
        grid.attach(self.title_entry, 1, 1, 1, 1)
        grid.attach(genre_label, 0, 2, 1, 1)
        grid.attach(self.genre_entry, 1, 2, 1, 1)
        grid.attach(album_label, 0, 3, 1, 1)
        grid.attach(self.album_entry, 1, 3, 1, 1)
        grid.attach(file_name_label, 0, 4, 1, 1)
        grid.attach(self.file_name_entry, 1, 4, 1, 1)

        dialog.get_content_area().add(grid)
        dialog.show_all()

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.filter_playlist()
        dialog.destroy()

    def search(self, widget):
        # Pobierz kryteria wyszukiwania z pola tekstowego
        search_criteria = self.search_entry.get_text().lower()

        # Filtruj playlistę na podstawie kryteriów wyszukiwania
        filtered_playlist = []
        for song_data in self.original_playlist:
            song_title = song_data[4].lower()
            if search_criteria in song_title:
                filtered_playlist.append(song_data)

        # Aktualizuj widok playlisty
        self.playlist_store.clear()
        for song_data in filtered_playlist:
            self.playlist_store.append(song_data)

    def filter_playlist(self):
        artist = self.artist_entry.get_text()
        title = self.title_entry.get_text()
        genre = self.genre_entry.get_text()
        album = self.album_entry.get_text()
        file_name = self.file_name_entry.get_text()

        # Clear the current playlist
        self.playlist_store.clear()

        # Iterate through the original playlist and add matching items
        for song_path, song_artist, song_genre, song_album, song_title in self.original_playlist:
            if (
                (artist.lower() in song_artist.lower()) and
                (title.lower() in song_title.lower()) and
                (genre.lower() in song_genre.lower()) and
                (album.lower() in song_album.lower()) and
                (file_name.lower() in os.path.basename(song_path).lower())
            ):
                self.playlist_store.append([song_path, song_artist, song_genre, song_album, song_title])

    def load_from_dir(self, widget):
        dialog = Gtk.FileChooserDialog(
            "Please choose a directory", None, Gtk.FileChooserAction.SELECT_FOLDER,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, "Select", Gtk.ResponseType.OK)
        )
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            folder_path = dialog.get_filename()
            self.original_playlist = self.scan_folder_for_audio_files(folder_path)
            self.update_playlist_view()
        dialog.destroy()

    def append_from_file(self, widget):
        dialog = Gtk.FileChooserDialog(
            "Please choose a file", None, Gtk.FileChooserAction.OPEN,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        )
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            song_path = dialog.get_filename()
            title, artist, genre, album = self.get_metadata_from_id3(song_path)
            self.playlist_store.append([song_path, artist, genre, album, title])
            self.original_playlist.append([song_path, artist, genre, album, title])
        dialog.destroy()

    def scan_folder_for_audio_files(self, folder_path):
        audio_files = []
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.endswith((".mp3", ".wav", ".ogg", ".flac")):
                    song_path = os.path.join(root, file)
                    title, artist, genre, album = self.get_metadata_from_id3(song_path)
                    audio_files.append([song_path, artist, genre, album, title])
        return audio_files

    def update_playlist_view(self):
        self.playlist_store.clear()
        for song_data in self.original_playlist:
            self.playlist_store.append(song_data)

    def clear_playlist(self, widget):
        self.playlist_store.clear()
        self.original_playlist.clear()

    def shuffle_playlist(self, widget):
        # Get the data from the ListStore and shuffle it
        playlist_data = [row[:] for row in self.playlist_store]
        random.shuffle(playlist_data)

        # Clear the ListStore and re-add the shuffled data
        self.playlist_store.clear()
        for row in playlist_data:
            self.playlist_store.append(row)

    def save_playlist(self, widget):
        dialog = Gtk.FileChooserDialog(
            "Save Playlist", None, Gtk.FileChooserAction.SAVE,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
        )
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            playlist_file = dialog.get_filename()
            with open(playlist_file, "w") as f:
                for row in self.original_playlist:
                    f.write(f"{row[0]}\n")
        dialog.destroy()

    def load_playlist(self, widget):
        dialog = Gtk.FileChooserDialog(
            "Load Playlist", None, Gtk.FileChooserAction.OPEN,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        )
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            playlist_file = dialog.get_filename()
            with open(playlist_file, "r") as f:
                lines = f.read().splitlines()
                for line in lines:
                    title, artist, genre, album = self.get_metadata_from_id3(line)
                    self.original_playlist.append([line, artist, genre, album, title])
                    self.playlist_store.append([line, artist, genre, album, title])
        dialog.destroy()

    def toggle_repeat_playlist(self, widget):
        self.repeat_playlist = widget.get_active()

    def toggle_repeat_current(self, widget):
        self.repeat_one_enabled = widget.get_active()

    def toggle_mute(self, widget):
        self.muted = widget.get_active()
        if self.muted:
            # Store the current volume before muting
            self.muted_volume = self.pipeline.get_property("volume")
            self.pipeline.set_property("volume", 0.0)  # Mute
        else:
            # Restore the volume to the stored value
            self.pipeline.set_property("volume", self.muted_volume)  # Unmute

    def on_gain_scale_change(self, widget):
        value = self.gain_scale.get_value()
        volume = value / 100  # Convert the value from the range 0-100 to 0-1
        self.pipeline.set_property("volume", volume)

    def on_position_scale_change(self, widget):
        if self.pipeline.get_state(0)[1] == Gst.State.PLAYING:
            value = self.position_scale.get_value()
            position = (value / 100) * self.pipeline.query_duration(Gst.Format.TIME)[1]
            self.pipeline.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH, position)

    def update_time_label(self):
        if self.pipeline.get_state(0)[1] == Gst.State.PLAYING:
            position, duration = self.pipeline.query_position(Gst.Format.TIME)[1], self.pipeline.query_duration(Gst.Format.TIME)[1]
            position_secs, duration_secs = position // Gst.SECOND, duration // Gst.SECOND
            position_str = time.strftime("%H:%M:%S", time.gmtime(position_secs))
            duration_str = time.strftime("%H:%M:%S", time.gmtime(duration_secs))

            if self.playlist_view.get_selection():
                model, selected_song_iter = self.playlist_view.get_selection().get_selected()
                if selected_song_iter:
                    artist = model.get_value(selected_song_iter, 1)
                    title = model.get_value(selected_song_iter, 4)
                    album = model.get_value(selected_song_iter, 3)
                    now_playing_text = f"Now Playing: {artist} - {title} from {album}"
                    self.now_playing_label.set_text(now_playing_text)

            self.time_label.set_text(f"{position_str} / {duration_str}")

        return True

    def update_now_playing_label(self):
        if self.playlist_view.get_selection():
            model, selected_song_iter = self.playlist_view.get_selection().get_selected()
            if selected_song_iter:
                artist = model.get_value(selected_song_iter, 1)
                title = model.get_value(selected_song_iter, 4)
                album = model.get_value(selected_song_iter, 3)
                now_playing_text = f"Now Playing: {artist} - {title} from {album}"
                self.now_playing_label.set_text(now_playing_text)


    def get_metadata_from_id3(self, file_path):
        try:
            audiofile = eyed3.load(file_path)
            if audiofile is not None and audiofile.tag:
                artist = str(audiofile.tag.artist)
                genre = str(audiofile.tag.genre)
                album = str(audiofile.tag.album)
                title = str(audiofile.tag.title)
                return title, artist, genre, album
        except Exception as e:
            print(f"Error reading ID3 tag: {e}")
        return os.path.basename(file_path), "", "", ""


    def run(self):
        Gtk.main()

if __name__ == "__main__":
    player = MusicPlayer()
    Gtk.main()

